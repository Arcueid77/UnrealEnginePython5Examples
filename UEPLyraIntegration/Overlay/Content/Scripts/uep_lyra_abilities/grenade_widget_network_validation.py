"""Real replicated Give/Reset/Reset/Clear for two owners; files only coordinate."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from .auto_respawn_helpers_network_validation import token
from .auto_respawn_helpers_validation import specs
from .auto_respawn_lifecycle_validation import ui_probe
from .jump_network_validation import Server as Playing,arg
from .grenade_widget_validation import Validation as Single,roots
from . import grenade_widget_mixin as policy,grenade_widget_observation as observation
from . import melee_replica_readiness as readiness
from .grenade_widget_network_contract import PEERS,PLAN,require,client,validate


def handles(asc): return [int(item.Handle.Handle) for item in roots(asc)]
def object_path(value): return value.get_path_name() if valid(value) else None


def poll_diagnostics(validation):
    diagnostic=getattr(validation,"lifecycle_diagnostic",None)
    if diagnostic is not None:
        control,watch=diagnostic;control.observe_registration();watch.poll()
        validation.report["lifecycle_event_files"]=list(watch.files)


def close_diagnostics(validation):
    diagnostic=getattr(validation,"lifecycle_diagnostic",None)
    if diagnostic is not None:
        control,watch=diagnostic;control.restore();watch.close()
        validation.report["lifecycle_event_files"]=list(watch.files)


class Client(Single):
    def __init__(self,result,peer,run):
        super().__init__(result);self.peer,self.run,self.root=peer,run,self.path.parent
        self.require_local_playing_phase=False;self.require_auto_active=False
        self.position=0;self.processed=None;self.command=None
        self.report.update(peer=peer,run_id=run,client_native_give_clear_called=False,native_give_clear_called_by_fixture=False,
            packet_loss_tested=False,travel_rejoin_tested=False)
    def ready(self):
        if token(self.root,"playing-ready.json",self.run) is not None: super().ready()
    def begin(self):
        super().begin();require(self.report["native_mode"]=="Client","actual native client mode required")
        self.report.update(player_id=int(self.controller.PlayerState.PlayerId),native_role=int(self.pawn.call_function("GetLocalRole")))
        atomic_write(self.root/(self.peer+"-ready.json"),dict(run_id=self.run,player_id=self.report["player_id"]))
        self.enter("network")
    def source_pawn(self):
        values,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.find_class("LyraCharacter"))
        found=[]
        for pawn in values:
            state=pawn.get_property("PlayerState")
            if valid(state) and int(state.PlayerId)==self.command["player_id"] and state.call_function("GetPawn")==pawn: found.append(pawn)
        if len(found)!=1: return None
        pawn=found[0];health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        if not valid(health): return None
        row=readiness.snapshot(pawn,health);self.report["pending_target_binding"]=row
        if row["health"]!=100. or row["destroying"] or row["actor_asc"] is None or row["actor_asc"]["avatar"]!=row["actor"]: return None
        return pawn
    def ack(self,stage,row):
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-"+stage+".json"),dict(run_id=self.run,position=self.position,row=row))
        self.processed=(self.position,stage)
    def attach_command(self):
        own=self.command["owner"]==self.peer
        if own:
            matches=[item for item in roots(self.asc) if int(item.Handle.Handle)==self.command["handle"]]
            if len(matches)!=1: return
            values=[value for value in list(matches[0].NonReplicatedInstances)+list(matches[0].ReplicatedInstances) if valid(value)]
            if len(values)!=1: return
            self.clone=values[0];self.target_path=self.clone.get_path_name();self.native_events=[]
            ue.set_mixin_profile(self.clone,self.command["profile"])
            require(not ui_probe(self.clone)["valid"],"replicated test grant already owns UI before Avatar change")
        else:
            self.clone=None;self.target_path=None;self.native_events=[]
            require(specs(self.asc)==self.original_specs,"foreign native grant changed own ability specs")
        pawn=self.source_pawn()
        if not valid(pawn): return
        require(self.widgets()==self.original_widgets,"native grant changed UI before Avatar callback")
        self.previous_pawn=pawn.get_path_name();self.waves=[]
        self.ack("attach",dict(own=own,initial_ui_invalid=True,source_role=int(pawn.call_function("GetLocalRole"))))
    def wave(self,number):
        pawn=self.source_pawn()
        if not valid(pawn) or pawn.get_path_name()==self.previous_pawn: return
        own=self.command["owner"]==self.peer;widgets=self.widgets()
        if len(widgets)!=(2 if own else 1): return
        if own and (not ui_probe(self.clone)["valid"] or len(self.native_events)!=number): return
        if number==2: require(widgets==self.waves[0]["widgets"],"network repeated Avatar duplicated/replaced native UI")
        row=dict(number=number,pawn=pawn.get_path_name(),old_pawn=self.previous_pawn,source_role=int(pawn.call_function("GetLocalRole")),
            health=100.,canonical_bound_asc=True,widgets=widgets,own=own)
        self.waves.append(row);self.previous_pawn=row["pawn"];self.ack("respawn"+str(number),row)
    def cleared(self):
        own=self.command["owner"]==self.peer
        if own and any(int(item.Handle.Handle)==self.command["handle"] for item in roots(self.asc)): return
        if self.widgets()!=self.original_widgets: return
        if own and len(self.native_events)!=3: return
        require(specs(self.asc)==self.original_specs and handles(self.asc)==self.original_grenade_handles,"network own original specs/Grenade handle changed")
        self.clone=None;self.quiet_ticks+=1
        if self.quiet_ticks<20: return
        row=dict(position=self.position,owner=self.command["owner"],profile=self.command["profile"],own=own,waves=copy.deepcopy(self.waves),
            native_callbacks=copy.deepcopy(self.native_events),quiet_ticks=self.quiet_ticks,original_widgets_restored=True,original_specs_restored=True)
        self.report["cases"].append(row);self.ack("clear",row)
    def cleanup(self):
        if self.cleaned: return
        close_diagnostics(self)
        self.report["observers_restored"]=observation.restore() if self.installed else True
        self.report["test_owned_specs_removed"]=not hasattr(self,"asc") or (hasattr(self,"original_grenade_handles") and handles(self.asc)==self.original_grenade_handles)
        self.clone=None;self.cleaned=True
    def tick(self,seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<500.,"native Grenade UI client total timeout")
            poll_diagnostics(self)
            if self.phase=="ready": self.ready()
            elif self.phase=="release":
                if token(self.root,"release.json",self.run) is not None: self.finish()
            else:
                command=token(self.root,"ui-command.json",self.run)
                if command is not None:
                    key=(command["position"],command["stage"])
                    if key!=self.processed:
                        if key!=getattr(self,"waiting_key",None): self.waiting_key=key;self.wait_started=time.monotonic()
                        require(time.monotonic()-self.wait_started<40.,"native Grenade UI replicated stage timeout: "+str(key))
                        self.command=command;self.position=command["position"];stage=command["stage"]
                        if stage=="attach": self.attach_command()
                        elif stage.startswith("respawn"): self.wave(int(stage[-1]))
                        elif stage=="clear": self.cleared()
                        elif stage=="complete":
                            self.cleanup();self.ack("complete",{});self.enter("release")
                        self.report["pending_command"]=command
                        if stage!="clear": self.quiet_ticks=0
            self.report.update(phase=self.phase,pending_native_events=copy.deepcopy(self.native_events));self.write();return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        try: self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write();ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try: self.report["status"]="passed";client(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_WIDGET_NETWORK_SHUTDOWN_"+self.report["status"].upper())


class Server(Playing):
    def __init__(self,result,run):
        super().__init__(result,run);self.ability_class=policy.CLASS;self.installed=False;self.clone=None;self.target_path=None
        self.native_events=[];self.observation_errors=[];self.stage=None
        self.report.update(native_mode="DedicatedServer",observation_errors=self.observation_errors,health_properties_written=False,
            callback_replay=False,native_ui_pool_written=False,packet_loss_tested=False,travel_rejoin_tested=False)
    def capture_spec_cleanup(self):
        rows={}
        for peer,value in self.owners.items():
            live="asc" in value and valid(value["asc"])
            current=handles(value["asc"]) if live else []
            rows[peer]=dict(native_asc_alive=live,original_handles=value.get("handles",[]),current_handles=current,
                original_specs_restored=live and specs(value["asc"])==value["specs"])
        self.report["native_pre_release_specs"]=rows
        self.report["test_owned_specs_removed"]=bool(rows) and all(row["native_asc_alive"] and row["current_handles"]==row["original_handles"] and row["original_specs_restored"] for row in rows.values())
    def prepare(self):
        for value in self.owners.values():
            value["asc"]=value["controller"].PlayerState.get_property("AbilitySystemComponent")
            value["specs"]=specs(value["asc"]);value["handles"]=handles(value["asc"])
            require(len(value["handles"])==1,"one original authority Grenade handle required")
        self.report["native_mode"]=str(ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world).call_function("CaptureSnapshot").NetMode)
        observation.install(self);self.installed=True
    def publish(self,stage):
        self.stage=stage;self.stage_started=time.monotonic()
        atomic_write(self.root/"ui-command.json",dict(run_id=self.run,position=self.position,stage=stage,**self.command))
    def acks(self,stage):
        values={peer:token(self.root,peer+"-"+str(self.position)+"-"+stage+".json",self.run,self.position) for peer in PEERS}
        return values if all(values.values()) else None
    def start(self):
        peer,profile=PLAN[self.position];self.owner=self.owners[peer];self.asc=self.owner["asc"]
        self.handle=self.asc.call_function("K2_GiveAbility",ue.load_class(policy.CLASS),1,-1)
        item,=[item for item in roots(self.asc) if int(item.Handle.Handle)==int(self.handle.Handle)]
        values=[value for value in list(item.NonReplicatedInstances)+list(item.ReplicatedInstances) if valid(value)]
        require(len(values)==1,"one real authority test Grenade instance required")
        self.clone=values[0];self.target_path=self.clone.get_path_name();self.native_events=[];ue.set_mixin_profile(self.clone,profile)
        require(not self.clone.call_function("IsLocallyControlled") and not ui_probe(self.clone)["valid"],"dedicated remote owner unexpectedly owns UI")
        self.command=dict(owner=peer,profile=profile,handle=int(self.handle.Handle),player_id=self.owner["player_id"])
        self.row=dict(position=self.position,owner=peer,profile=profile,owning_player_state=self.owner["controller"].PlayerState.get_path_name(),
            reset_requests=0,native_callbacks=[],waves=[],native_locally_controlled=False)
        self.publish("attach")
    def reset(self,number):
        self.old_pawn=self.owner["controller"].get_controlled_pawn().get_path_name()
        tag=GameplayTag(TagName="GameplayEvent.RequestReset");state=self.owner["controller"].PlayerState
        ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("SendGameplayEventToActor",state,tag,GameplayEventData(EventTag=tag,Instigator=state,Target=state))
        self.row["reset_requests"]+=1;self.publish("respawn"+str(number))
    def respawned(self,number):
        pawn=self.owner["controller"].get_controlled_pawn()
        if not valid(pawn) or pawn.get_path_name()==self.old_pawn: return False
        health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        if not valid(health) or health.call_function("GetHealth")!=100. or not valid(ability_system(pawn)): return False
        if self.asc.call_function("GetGameplayTagCount",GameplayTag(TagName="Gameplay.DamageImmunity"))!=0: return False
        if len(self.native_events)!=number: return False
        self.owner["pawn"]=pawn
        return True
    def step(self):
        require(time.monotonic()-self.stage_started<45.,"authority Grenade UI stage timeout: "+str(self.stage))
        if self.stage=="attach":
            if self.acks("attach"): self.reset(1)
        elif self.stage.startswith("respawn"):
            number=int(self.stage[-1]);acks=self.acks(self.stage)
            if not self.respawned(number) or not acks: return
            self.row["waves"].append(dict(number=number,pawn=self.owner["pawn"].get_path_name(),old_pawn=self.old_pawn,health=100.,viewers={peer:value["row"] for peer,value in acks.items()}))
            if number==1: self.reset(2)
            else:
                self.asc.call_function("ClearAbility",self.handle);self.clone=None;self.clear_events=copy.deepcopy(self.native_events);self.publish("clear")
        elif self.stage=="clear":
            require(self.native_events==self.clear_events,"late authority callback after native Grenade Clear")
            acks=self.acks("clear")
            if not acks: return
            require(specs(self.asc)==self.owner["specs"] and handles(self.asc)==self.owner["handles"],"authority original Grenade specs changed")
            self.row.update(native_callbacks=copy.deepcopy(self.native_events),viewers={peer:value["row"] for peer,value in acks.items()},original_specs_restored=True)
            self.report["cases"].append(copy.deepcopy(self.row));self.position+=1
            if self.position==len(PLAN): self.publish("complete")
            else: self.start()
        elif self.stage=="complete":
            if not self.acks("complete"): return
            if not getattr(self,"released",False):
                self.capture_spec_cleanup()
                require(self.report["test_owned_specs_removed"],"authority test-owned specs remain before client release")
                self.report["observers_restored"]=observation.restore();self.installed=False
                atomic_write(self.root/"release.json",dict(run_id=self.run));self.released=True
            exits=[token(self.root,peer+"-exited.json",self.run) for peer in PEERS]
            if all(value is not None and value["exit_code"]==0 for value in exits): self.report["server_waited_for_client_process_exit"]=True;self.finish()
    def tick(self,seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<500.,"native Grenade UI authority total timeout")
            poll_diagnostics(self)
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.installed and self.stage is None: self.prepare();self.start()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"));self.step()
            self.report.update(pending_stage=self.stage,pending_native_events=copy.deepcopy(self.native_events));atomic_write(self.path,self.report);return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        try:
            close_diagnostics(self)
            if self.clone is not None:
                if valid(self.asc) and any(int(item.Handle.Handle)==int(self.handle.Handle) for item in roots(self.asc)): self.asc.call_function("ClearAbility",self.handle)
                self.clone=None
            if self.installed: self.report["observers_restored"]=observation.restore();self.installed=False
            # Disconnection legitimately destroys PlayerStates/ASCs. Preserve
            # the live before-release proof; do not query dead peers after exit.
            if not getattr(self,"released",False): self.capture_spec_cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        super().finish(error)
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown": self.report["status"]="passed"
        atomic_write(self.path,self.report);(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_WIDGET_NETWORK_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeWidgetNetworkResult=")),None)
if result:
    peer,run=arg("-UEPJumpPeer="),arg("-UEPJumpRun=")
    mode=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPReplicaCharacterStartupProfile=")),None)
    if mode:
        from .melee_character_default_control import CharacterDefaultControl
        diagnostic_control=CharacterDefaultControl(mode)
    else: diagnostic_control=None
    validation=Server(result,run) if peer=="server" else Client(result,peer,run)
    validation.lifecycle_diagnostic=None
    if diagnostic_control is not None:
        watch=readiness.EarlyWatch(validation.root,peer,run);diagnostic_control.observe_births(watch,construction=True)
        validation.lifecycle_diagnostic=(diagnostic_control,watch)
        validation.report["character_lifecycle_diagnostic"]=diagnostic_control.report
    atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
