"""Two real native clients predict; GAS RPC activates authority once.

Coordination files schedule/ack only. Projectiles are observed and destroyed by
the authority witness before a world tick: their replication/explosion is NOT
this bounded activation test. No far-field teleports or raw gameplay writes.
"""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from .auto_respawn_helpers_validation import Validation as Ready,instances,specs
from .auto_respawn_helpers_network_validation import token
from .auto_respawn_events_mixin import ADAPTER
from .jump_network_validation import Server as Playing,arg
from .grenade_widget_validation import Validation as Widget,roots
from .auto_respawn_lifecycle_validation import ui_probe
from .grenade_widget_network_validation import Client as Viewer
from .grenade_activation_validation import Validation as Single,config,counts,path
from .grenade_activation_contract import CLASS,require
from .grenade_activation_network_contract import PLAN,PEERS,client,validate,accept_command
from . import grenade_activation_mixin as policy,network_identity as wire,melee_replica_readiness as readiness


def handles(asc): return [int(item.Handle.Handle) for item in roots(asc)]
def native_mode(world):
    bridge=ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",world)
    return str(bridge.call_function("CaptureSnapshot").NetMode)
def report(mode,peer,run):
    return dict(schema_version=1,status="running",error=None,native_mode=mode,peer=peer,run_id=run,cases=[],observation_errors=[],
        network_acceptance=True,full_acceptance=False,packaged_runtime=False,physical_input_tested=False,packet_loss_tested=False,travel_rejoin_tested=False,
        health_properties_written=False,inventory_properties_written=False,ability_spec_properties_written=False,activation_event_replayed=False,task_callbacks_replayed=False,
        ability_granted_by_fixture=False,native_rpc_bypassed=False,gameplay_state_delivered_by_files=False,projectile_replication_tested=False,
        projectile_actor_business_migrated=False,explosion_damage_tested=False,denied_body_native_tested=False,far_field_teleports=False)


class Witness:
    install=Single.install
    projectiles=Single.projectiles
    healths=Single.healths
    widgets=Widget.widgets
    source_pawn=Viewer.source_pawn
    def view(self):
        row=Single.view(self);row["activation_mode"]=int(self.grenade.get_property("CurrentActivationInfo").ActivationMode)
        return row
    def init_witness(self):
        self.grenade=None;self.target=None;self.scope=SubscriptionScope();self.test_projectiles=[];self.native_events=[];self.messages=[]
        self.observation_errors=self.report["observation_errors"];self.installed=False;self.wire_required=True;self.closed=False
        self.rep_notifies=[]
    def observe_native(self):
        self.math=ue.find_class("KismetMathLibrary").get_cdo();self.system=ue.find_class("KismetSystemLibrary").get_cdo()
        self.install();reader=ue.load_class(ADAPTER).get_cdo()
        owner=self
        # Test-only native RepNotify witness. Always execute the original BP
        # once; the fourth function is NOT a migrated production handler.
        for name in ("Python","BlueprintFallback"):
            binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==ue.load_class(CLASS)]
            base=binding["profiles"][name]["python_class"]
            def notify(ability):
                watched=ability==owner.grenade and owner.target is not None
                before=len(owner.messages)
                if watched:
                    row=dict(cooldown=float(ability.get_property("Cooldown Time")),active=bool(ability.get_property("bIsActive")),game_time=float(owner.statics.call_function("GetTimeSeconds",owner.world)))
                ability.call_mixin_original("OnRep_Cooldown Time")
                if watched:
                    row["messages"]=copy.deepcopy(owner.messages[before:]);owner.rep_notifies.append(row)
                    require(len(owner.rep_notifies)<=64,"bounded native Grenade RepNotify history exhausted")
            notify.override="OnRep_Cooldown Time"
            ue.register_mixin_profile(ue.load_class(CLASS),name,type("ObservedGrenadeNotify"+name,(),dict(K2_ActivateAbility=base.K2_ActivateAbility,
                K2_OnPawnAvatarSet=base.K2_OnPawnAvatarSet,K2_OnAbilityRemoved=base.K2_OnAbilityRemoved,ObservedCooldownNotify=notify)))
        def read(proxy):
            payload,success=reader.call_function("ReadDuration",proxy);require(success is True,"native network Grenade duration extraction failed");return payload
        def received(channel,payload):
            try:
                if path(payload.Instigator)==self.target:
                    self.messages.append(dict(channel=str(channel.TagName),instigator=path(payload.Instigator),duration=float(payload.Duration),
                        native_active=bool(self.grenade.get_property("bIsActive")),native_montage_task_count=len([task for task in self.grenade.get_property("ActiveTasks") if valid(task) and task.is_a(ue.find_class("AbilityTask_PlayMontageAndWait"))])))
            except Exception: self.observation_errors.append(traceback.format_exc())
        self.scope.listen_gameplay_message(self.world,policy.CHANNEL,ue.find_struct("LyraInteractionDurationMessage"),read,received)
    def arm(self,profile):
        self.original=dict(config=self.original_config)
        self.target=path(self.pawn);self.native_events=[];self.messages=[];self.rep_notifies=[];self.pre_projectiles=[path(actor) for actor in self.projectiles()]
        self.before_counts=counts(self.grenade);self.health_before=self.healths();self.cooldown_before=float(self.grenade.get_property("Cooldown Time"))
        ue.set_mixin_profile(self.grenade,profile)
        self.native_cost_ready=bool(self.grenade.call_function("K2_CheckAbilityCost"));self.native_cooldown_ready=bool(self.grenade.call_function("K2_CheckAbilityCooldown"))
        require(self.native_cost_ready and self.native_cooldown_ready,"native Grenade cost/cooldown not ready")
    def native_row(self):
        require(len(self.native_events)==1 and not self.observation_errors,"actual native network Grenade callback failed: "+str(self.observation_errors))
        result=copy.deepcopy(self.native_events[0]);after=counts(self.grenade)
        result.update(pawn=path(self.pawn),native_callback_count=1,native_role=int(self.pawn.call_function("GetLocalRole")),
            native_authority=bool(self.grenade.call_function("K2_HasAuthority")),native_cost_ready=self.native_cost_ready,native_cooldown_ready=self.native_cooldown_ready,
            messages=copy.deepcopy(self.messages),cooldown_before=self.cooldown_before,stats={key:value-self.before_counts[key] for key,value in after.items()},
            source_identity=wire.read(self.pawn),montage_continues_after_end=result["montage"]==self.original_config["montage"] and result["active_after"] is False)
        return result
    def close_witness(self):
        if self.closed: return
        self.target=None
        try: self.scope.close()
        finally: self.report["listener_closed"]=self.scope.closed
        if self.installed:
            for name,base in (("Python",policy.LyraGrenadeActivationPythonProfile),("BlueprintFallback",policy.LyraGrenadeActivationBlueprintFallbackProfile)):
                ue.register_mixin_profile(ue.load_class(CLASS),name,base)
            binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==ue.load_class(CLASS)]
            self.report["observers_restored"]=all(binding["profiles"][name]["python_class"] is base for name,base in (("Python",policy.LyraGrenadeActivationPythonProfile),("BlueprintFallback",policy.LyraGrenadeActivationBlueprintFallbackProfile)))
        self.report["remaining_test_projectiles"]=len([actor for actor in self.test_projectiles if valid(actor) and not actor.call_function("IsActorBeingDestroyed")])
        self.closed=True
    def diagnostic(self):
        row=dict(native_events=copy.deepcopy(self.native_events),messages=copy.deepcopy(self.messages),rep_notifies=copy.deepcopy(self.rep_notifies))
        if valid(self.grenade): row.update(counts=counts(self.grenade),cooldown=float(self.grenade.get_property("Cooldown Time")),native_cooldown=float(self.grenade.call_function("GetCooldownTimeRemaining")))
        if hasattr(self,"frozen_counts"): row["frozen_counts"]=self.frozen_counts
        if hasattr(self,"frozen_messages"): row["frozen_messages"]=self.frozen_messages
        if hasattr(self,"own_state") and self.own_state is not None:
            before=self.own_state["health"];after=self.healths()
            row.update(health_before=before,health_after=after,health_removed=sorted(set(before)-set(after)),health_added=sorted(set(after)-set(before)),
                health_changed={key:dict(before=before[key],after=after[key]) for key in set(before)&set(after) if before[key]!=after[key]})
        self.report["failure_diagnostic"]=row


class Client(Witness,Ready):
    def __init__(self,result,peer,run):
        Ready.__init__(self,result);self.peer,self.run,self.root=peer,run,self.path.parent;self.require_auto_active=False;self.require_local_playing_phase=False
        self.report=report("Client",peer,run);self.init_witness();self.processed=None;self.position=-1;self.completed_position=-1;self.command=None;self.own_state=None
    def ready(self):
        if token(self.root,"playing-ready.json",self.run) is not None: Ready.ready(self)
    def begin(self):
        self.report["native_mode"]=native_mode(self.world);require(self.report["native_mode"]=="Client","actual native client world required")
        values=instances(self.asc,ue.load_class(CLASS));require(len(values)==1,"one actual replicated owner Grenade instance required")
        self.grenade=values[0];self.original_config=config(self.grenade);self.original_grenade_profile=str(ue.get_mixin_profile(self.grenade))
        self.original_handles=handles(self.asc);self.original_specs=specs(self.asc);self.original_widgets=self.widgets()
        require(len(self.original_handles)==len(self.original_widgets)==1,"one persistent Grenade and actual attached native widget required")
        self.report.update(player_id=int(self.controller.PlayerState.PlayerId),native_role=int(self.pawn.call_function("GetLocalRole")),native_class=path(self.grenade.get_class()),original_handles=self.original_handles)
        self.observe_native();atomic_write(self.root/(self.peer+"-ready.json"),dict(run_id=self.run,player_id=self.report["player_id"]))
        self.enter("network")
    def ack(self,stage,row):
        atomic_write(self.root/(self.peer+"-"+str(self.position)+"-"+stage+".json"),dict(run_id=self.run,position=self.position,row=row));self.processed=(self.position,stage)
    def prepare(self):
        source=self.source_pawn()
        if not valid(source) or not Ready.attach(self,self.world,self.controller): return
        require(instances(self.asc,ue.load_class(CLASS))==[self.grenade] and handles(self.asc)==self.original_handles,"original replicated Grenade instance/handle changed")
        require(self.widgets()==self.original_widgets and specs(self.asc)==self.original_specs,"native Reset changed persistent UI/spec classes")
        self.own=self.command["owner"]==self.peer;self.target=None;self.native_events=[];self.messages=[]
        self.own_state=dict(specs=specs(self.asc),handles=handles(self.asc),widgets=self.widgets(),counts=counts(self.grenade),health=self.healths())
        health=source.get_component_by_type(ue.find_class("LyraHealthComponent"))
        self.source_before=dict(network_identity=wire.read(source),source_role=int(source.call_function("GetLocalRole")),healthy_bound=True,binding=readiness.snapshot(source,health))
        if self.own:
            if self.grenade.call_function("GetCooldownTimeRemaining")>0: return
            self.arm(self.command["profile"])
        self.quiet_ticks=0
        self.ack("prepare",dict(own=self.own,**self.source_before))
    def activate(self):
        if self.own:
            accepted=bool(self.asc.call_function("TryActivateAbilityByClass",ue.load_class(CLASS),False))
            require(accepted,"owning client real predicted ASC Grenade request rejected")
            self.event_row=self.native_row();self.event_row["native_request_accepted"]=accepted
            # Original native baseline has no local predicted cooldown yet.
            # A second request now really reactivates it; wait for replicated
            # cooldown before the separate native rejection/guard check.
            self.event_row["native_repeat_rejected"]=False;self.repeat_checked=False
            self.frozen_counts=counts(self.grenade);self.frozen_messages=copy.deepcopy(self.messages)
        self.game_started=time.monotonic();self.enter("quiet");self.processed=(self.position,"activate")
    def quiet(self):
        require(time.monotonic()-self.game_started<15.,"native predicted Grenade montage/quiet timeout")
        require(self.widgets()==self.original_widgets and specs(self.asc)==self.original_specs and handles(self.asc)==self.original_handles,"Grenade activation altered native UI/specs/handles")
        require(self.healths()==self.own_state["health"],"native Grenade fixture changed Health; no raw restoration allowed")
        if self.own:
            require(len(self.native_events)==1 and counts(self.grenade)==self.frozen_counts and self.messages==self.frozen_messages,"late predicted Grenade handler/message")
            if not self.repeat_checked:
                remaining=float(self.grenade.call_function("GetCooldownTimeRemaining"))
                if remaining>0:
                    self.event_row["native_confirmed_cooldown_before_repeat"]=remaining
                    self.event_row["native_repeat_rejected"]=self.asc.call_function("TryActivateAbilityByClass",ue.load_class(CLASS),False) is False
                    require(self.event_row["native_repeat_rejected"] and len(self.native_events)==1,"native cooldown-confirmed repeat request was not rejected")
                    self.repeat_checked=True
        else:
            require(not self.native_events and not self.messages and counts(self.grenade)==self.own_state["counts"],"foreign request activated/messaged local owner")
        self.quiet_ticks+=1
        if self.quiet_ticks<20: return
        if self.own and not self.repeat_checked: return
        if self.own and path(self.pawn.call_function("GetCurrentMontage"))==self.original_config["montage"]: return
        require([path(actor) for actor in self.projectiles()]==self.pre_projectiles if self.own else not self.projectiles(),"unaccepted projectile replicated into bounded activation fixture")
        row=dict(position=self.position,owner=self.command["owner"],profile=self.command["profile"],own=self.own,quiet_ticks=self.quiet_ticks,
            source=self.source_before,ui_preserved=True,specs_preserved=True,handles_preserved=True,all_pawn_health_unchanged=True,
            foreign_owner_untouched=not self.own,activation=copy.deepcopy(self.event_row) if self.own else None,native_montage_completed=True)
        self.report["cases"].append(row);self.completed_position=self.position;self.target=None;self.ack("done",row);self.enter("network")
    def cleanup(self):
        self.close_witness()
        if hasattr(self,"original_grenade_profile"):
            ue.set_mixin_profile(self.grenade,self.original_grenade_profile)
            self.report.update(profile_restored=str(ue.get_mixin_profile(self.grenade))==self.original_grenade_profile,
                specs_preserved=specs(self.asc)==self.original_specs,handles_preserved=handles(self.asc)==self.original_handles,
                config_preserved=config(self.grenade)==self.original_config,ui_preserved=self.widgets()==self.original_widgets)
    def tick(self,delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<500.,"native Grenade predicted client total timeout")
            if self.phase=="ready": self.ready()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                if self.phase=="quiet": self.quiet()
                elif self.phase=="release":
                    if token(self.root,"release.json",self.run) is not None: self.finish()
                else:
                    command=token(self.root,"activation-command.json",self.run)
                    if command is not None and accept_command(command,self.processed,self.completed_position):
                        self.command=command;self.position=command["position"];stage=command["stage"]
                        if stage=="prepare": self.prepare()
                        elif stage=="activate": self.activate()
                        elif stage=="complete": self.cleanup();self.ack("complete",dict(cleanup=True));self.enter("release")
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        try:
            if error: self.diagnostic()
            self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write();ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try: self.report["status"]="passed";client(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_ACTIVATION_NETWORK_SHUTDOWN_"+self.report["status"].upper())


class Server(Witness,Playing):
    def __init__(self,result,run):
        Playing.__init__(self,result,run);self.report=report("DedicatedServer","server",run);self.report["server_waited_for_client_process_exit"]=False
        self.ability_class=CLASS;self.init_witness();self.stage=None;self.command={};self.released=False
    def prepare_owners(self):
        self.report["native_mode"]=native_mode(self.world);require(self.report["native_mode"]=="DedicatedServer","actual native dedicated-server world required")
        for owner in self.owners.values():
            require(path(owner["ability"].get_class())==CLASS,"actual authority Grenade class changed")
            owner["asc"]=ability_system(owner["pawn"]);owner["profile"]=str(ue.get_mixin_profile(owner["ability"]))
            owner["specs"]=specs(owner["asc"]);owner["handles"]=handles(owner["asc"]);owner["config"]=config(owner["ability"])
        self.report["native_class"]=CLASS;self.observe_native()
    def publish(self,stage):
        self.stage,self.stage_started=stage,time.monotonic()
        atomic_write(self.root/"activation-command.json",dict(run_id=self.run,position=self.position,stage=stage,**self.command))
    def acks(self,stage):
        rows={peer:token(self.root,peer+"-"+str(self.position)+"-"+stage+".json",self.run,self.position) for peer in PEERS}
        return rows if all(rows.values()) else None
    def start(self):
        peer,profile=PLAN[self.position];owner=self.owners[peer]
        if owner["ability"].call_function("GetCooldownTimeRemaining")>0: return
        self.owner=owner;self.controller=owner["controller"];self.pawn=self.controller.get_controlled_pawn();self.asc=owner["asc"];self.grenade=owner["ability"];self.original_config=owner["config"]
        self.old_pawn=path(self.pawn);self.old_identity=wire.read(self.pawn);require(wire.key(self.old_identity) is not None,"authority old Pawn has no wire identity")
        self.target=None;tag=GameplayTag(TagName="GameplayEvent.RequestReset");state=self.controller.PlayerState
        ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("SendGameplayEventToActor",state,tag,GameplayEventData(EventTag=tag,Instigator=state,Target=state))
        self.stage="respawn";self.stage_started=time.monotonic();self.command=dict(owner=peer,profile=profile,player_id=owner["player_id"])
    def respawn(self):
        pawn=self.controller.get_controlled_pawn()
        if not valid(pawn) or path(pawn)==self.old_pawn: return
        health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        if not valid(health) or health.call_function("GetHealth")!=100. or not valid(ability_system(pawn)): return
        if self.asc.call_function("GetGameplayTagCount",GameplayTag(TagName="Gameplay.DamageImmunity")): return
        identity=wire.read(pawn)
        if wire.key(identity) is None: return
        self.pawn=pawn;self.owner["pawn"]=pawn;self.command["source_identity"]=identity
        require(instances(self.asc,ue.load_class(CLASS))==[self.grenade] and handles(self.asc)==self.owner["handles"],"native Reset replaced persistent authority Grenade")
        self.arm(self.command["profile"]);self.publish("prepare")
    def capture_cleanup(self):
        rows={}
        for peer,owner in self.owners.items():
            ability=owner["ability"];asc=owner["asc"];ue.set_mixin_profile(ability,owner["profile"])
            rows[peer]=dict(native_asc_alive=valid(asc),profile_restored=str(ue.get_mixin_profile(ability))==owner["profile"],
                specs_preserved=specs(asc)==owner["specs"],handles_preserved=handles(asc)==owner["handles"],config_preserved=config(ability)==owner["config"],
                original_handles=owner["handles"],current_handles=handles(asc))
        self.report["native_pre_release_cleanup"]=rows
    def step(self):
        require(time.monotonic()-self.stage_started<45.,"native Grenade authority stage timeout: "+str(self.stage))
        if self.stage=="respawn": self.respawn()
        elif self.stage=="prepare":
            self.prepare_acks=self.acks("prepare")
            if self.prepare_acks:
                self.health_before=self.healths();self.publish("activate");self.quiet_ticks=0;self.event_row=None
        elif self.stage=="activate":
            if self.native_events and self.event_row is None:
                self.event_row=self.native_row();self.frozen_counts=counts(self.grenade);self.frozen_messages=copy.deepcopy(self.messages)
                self.report["pending_activation"]=copy.deepcopy(self.event_row)
            if self.event_row is None: return
            require(len(self.native_events)==1 and counts(self.grenade)==self.frozen_counts and self.messages==self.frozen_messages,"late authoritative Grenade callback/message")
            require(self.healths()==self.health_before,"network Grenade fixture changed Health")
            self.quiet_ticks+=1;done=self.acks("done")
            if not done or self.quiet_ticks<20: return
            require([path(actor) for actor in self.projectiles()]==self.pre_projectiles,"observed authority projectile still alive")
            row=dict(position=self.position,owner=self.command["owner"],profile=self.command["profile"],old_identity=self.old_identity,source_identity=wire.read(self.pawn),
                native_reset_requests=1,activation=copy.deepcopy(self.event_row),prepared={peer:value["row"] for peer,value in self.prepare_acks.items()},
                viewers={peer:value["row"] for peer,value in done.items()},quiet_ticks=self.quiet_ticks,all_pawn_health_unchanged=True,
                native_nonlocal_owner=not self.grenade.call_function("IsLocallyControlled"),native_ui_invalid=not ui_probe(self.grenade)["valid"])
            self.report["cases"].append(row);ue.log("UEP_GRENADE_ACTIVATION_NETWORK_CASE_PASSED "+row["owner"]+" "+row["profile"])
            self.position+=1;self.target=None
            if self.position==len(PLAN): self.publish("complete")
            else: self.stage="start";self.stage_started=time.monotonic()
        elif self.stage=="complete":
            if not self.acks("complete"): return
            if not self.released:
                self.capture_cleanup();self.close_witness();atomic_write(self.root/"release.json",dict(run_id=self.run));self.released=True
            exits=[token(self.root,peer+"-exited.json",self.run) for peer in PEERS]
            if all(row is not None and row["exit_code"]==0 for row in exits): self.report["server_waited_for_client_process_exit"]=True;self.finish()
    def tick(self,seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<500.,"native Grenade predicted authority total timeout")
            if not self.playing_gate: self.wait_playing()
            elif not self.owners: self.setup()
            elif not self.installed: self.prepare_owners();self.stage="start";self.stage_started=time.monotonic()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                if self.stage=="start": self.start()
                else: self.step()
            self.report.update(pending_stage=self.stage,pending_callbacks=copy.deepcopy(self.native_events));atomic_write(self.path,self.report);return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        try:
            if self.owners and not self.released: self.capture_cleanup()
            self.close_witness()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);atomic_write(self.path,self.report);ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown": self.report["status"]="passed"
        atomic_write(self.path,self.report);(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_ACTIVATION_NETWORK_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeActivationNetworkResult=")),None)
if result:
    peer,run=arg("-UEPJumpPeer="),arg("-UEPJumpRun=")
    validation=Server(result,run) if peer=="server" else Client(result,peer,run)
    atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
