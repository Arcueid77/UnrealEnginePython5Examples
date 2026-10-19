"""Actual server/two-client weapon prediction and native replicated damage."""
import atexit
import copy
import hashlib
import math
import re
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from unreal_engine.enums import ELyraTeamComparison,ETraceTypeQuery,EDrawDebugTrace
from uep_lyra_network_io import atomic_write,read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world.inventory_pad_network_state import capture,services
from uep_lyra_hud.weapon_validation_helpers import set_stat
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.jump_network_validation import Server as Playing,arg
from uep_lyra_abilities.melee_trace_mixin import break_hit,native_outputs
from uep_lyra_abilities import network_identity as wire,reload_weapon_fixture as fixtures,reload_magazine_mixin as ammo_policy
from . import weapon_ability_fire_mixin as policy
from .weapon_ability_fire_network_contract import PEERS,PLAN,FALSE,WEAPONS,require,accept_command


def path(value):return value.get_path_name() if valid(value) else None
def vector(value):return [float(value.x),float(value.y),float(value.z)]
def rot(value):return [float(value.roll),float(value.pitch),float(value.yaw)]
def identity(value):
    result=wire.read(value);return list(wire.key(result)) if wire.key(result) is not None else None
def hit_identity(value):
    if not valid(value):return dict(wire=None,replicated=False,static_guid=None)
    replicated=bool(value.get_property("bReplicates"));guid=None
    if not replicated and "ActorGuid" in value.properties():
        data=value.get_property("ActorGuid");parts=[int(data.get_field(name))&0xffffffff for name in ("A","B","C","D")]
        if any(parts):guid="".join(format(part,"08X") for part in parts)
    return dict(wire=identity(value),replicated=replicated,static_guid=guid)
def token(root,name,run,position=None):
    value=read_json(root/name)
    if value is None:return None
    require(value["run_id"]==run,"foreign network firing token")
    return value if position is None or value["position"]==position else None
def health_value(pawn):
    state=pawn.get_property("PlayerState") if valid(pawn) else None
    asc=state.get_property("AbilitySystemComponent") if valid(state) else None
    if not valid(asc):return None
    attrs=[value for value in asc.get_property("SpawnedAttributes") if valid(value) and value.is_a(ue.find_class("LyraHealthSet"))]
    return float(attrs[0].get_property("Health").CurrentValue) if len(attrs)==1 else None
def binding_ready(pawn):
    if not valid(pawn):return False
    asc=ability_system(pawn);health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
    return valid(asc) and valid(health) and asc.get_property("AvatarActor")==pawn and health.get_property("AbilitySystemComponent")==asc and health.call_function("GetHealth")==health_value(pawn)>0 and not health.call_function("IsDeadOrDying") and not asc.call_function("GetGameplayTagCount",GameplayTag(TagName="Gameplay.DamageImmunity"))
def ability_for(pawn,cls):
    asc=ability_system(pawn)
    if not valid(asc):return None
    values=[value for spec in asc.get_property("ActivatableAbilities").Items if valid(spec.Ability) and spec.Ability.get_class()==cls for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
    return values[0] if len(values)==1 else None
def line_of_sight(source,start,end,victim):
    attached,=source.call_function("GetAttachedActors")
    # DefaultEngine.ini maps Interaction to query3 and Weapon to query4.
    result=policy.lib("KismetSystemLibrary").call_function("LineTraceSingle",WorldContextObject=source,Start=start,End=end,TraceChannel=ETraceTypeQuery.TraceTypeQuery4,
        bTraceComplex=True,ActorsToIgnore=[source]+list(attached),DrawDebugType=getattr(EDrawDebugTrace,"None"),bIgnoreSelf=True,
        TraceColor=ue.FLinearColor(1.,0.,0.,1.),TraceHitColor=ue.FLinearColor(0.,1.,0.,1.),DrawTime=0.)
    fields=native_outputs("KismetSystemLibrary","LineTraceSingle",result)
    return bool(fields["ReturnValue"]) and break_hit(fields["OutHit"])["HitActor"]==victim
def prediction(ability,owner):
    # The existing generic UEP property converter has no Int16Property reader.
    # Native T3D export reads the actual reflected value without a CPP change
    # or pointer/layout assumptions. This is a local read, never an import.
    name=owner.peer+"-prediction-native-"+str(len(owner.prediction_exports))+".t3d";file=owner.root/name
    require(ue.new_object(ue.find_class("ObjectExporterT3D")).export_to_file(ability,str(file)),"native ability prediction export failed")
    raw=file.read_bytes();text=raw.decode("utf-16" if raw[:2] in (b"\xff\xfe",b"\xfe\xff") else "utf-8-sig")
    lines=[line for line in text.splitlines() if line.strip().startswith("CurrentActivationInfo=")]
    require(len(lines)==1,"native activation info export missing")
    matches=re.findall(r"PredictionKeyWhenActivated=\([^\r\n]*?Current=(-?\d+)",lines[0])
    require(len(matches)==1,"native prediction key export missing")
    owner.prediction_exports.append(dict(file=name,sha256=hashlib.sha256(raw).hexdigest(),current=int(matches[0])))
    return int(matches[0])


class Witness:
    def init_witness(self,result,peer,run):
        self.path,self.root,self.peer,self.run=Path(result),Path(result).parent,peer,run
        self.started=time.monotonic();self.finished=False;self.armed=False;self.position=-1;self.completed=-1;self.processed=None;self.command={};self.observers={};self.saved_profiles=[]
        self.weapon=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPWeaponFireNetworkWeapon=")),"pistol")
        self.report=dict(status="running",error=None,peer=peer,run_id=run,weapon=self.weapon,network_acceptance=True,cases=[],observation_errors=[])
        self.report.update({name:False for name in FALSE});self.statics=policy.lib("GameplayStatics")
        self.activations=[];self.target_data=[];self.weapon_events=[];self.callbacks=[];self.health_after=None;self.quiet=0;self.prediction_exports=[]
    def game_time(self):return float(self.statics.call_function("GetTimeSeconds",self.world))
    def install(self):
        owner=self
        for cls_path in (policy.CLASS,"/Game/Weapons/B_Weapon.B_Weapon_C"):
            cls=ue.load_class(cls_path);ue.register_declared_mixin(cls)
            row,=[r for r in ue.get_registered_mixins() if r["target_class"]==cls];originals={name:value["python_class"] for name,value in row["profiles"].items()};self.observers[cls]=originals
            for profile,base in originals.items():
                methods={key:value for key,value in vars(base).items() if not key.startswith("__") and callable(value)}
                if cls_path==policy.CLASS:
                    def around_activate(handler,selected):
                        def invoke(ability):
                            watched=owner.armed and wire.same(wire.read(ability.call_function("GetAvatarActorFromActorInfo")),owner.command["source_identity"])
                            if watched:
                                info=ability.get_property("CurrentActivationInfo")
                                event=dict(profile=selected,authority=bool(ability.call_function("K2_HasAuthority")),mode=int(info.ActivationMode),prediction_key=prediction(ability,owner),
                                    locally_controlled=bool(ability.call_function("IsLocallyControlled")),source=wire.read(ability.call_function("GetAvatarActorFromActorInfo")))
                            result=handler(ability)
                            if watched:
                                event["active_after"]=bool(ability.get_property("bIsActive"));owner.activations.append(event)
                            return result
                        invoke.override="K2_ActivateAbility";return invoke
                    def around_data(handler,selected):
                        def invoke(ability,TargetData):
                            watched=owner.armed and wire.same(wire.read(ability.call_function("GetAvatarActorFromActorInfo")),owner.command["source_identity"])
                            if watched:
                                hits=[break_hit(policy.lib("AbilitySystemBlueprintLibrary").call_function("GetHitResultFromTargetData",TargetData,index)) for index in range(int(policy.lib("AbilitySystemBlueprintLibrary").call_function("GetDataCountFromTargetData",TargetData)))]
                                identities=[hit_identity(hit["HitActor"]) for hit in hits];keys=[value["wire"] for value in identities]
                                event=dict(profile=selected,authority=bool(ability.call_function("K2_HasAuthority")),prediction_key=prediction(ability,owner),source=wire.read(ability.call_function("GetAvatarActorFromActorInfo")),
                                    count=len(hits),hit_identities=keys,hit_identity_details=identities,target_hits=sum(value==list(wire.key(owner.command["target_identity"])) for value in keys),points=[vector(hit["ImpactPoint"]) for hit in hits])
                            result=handler(ability,TargetData)
                            if watched:owner.target_data.append(event)
                            return result
                        invoke.override="OnRangedWeaponTargetDataReady";return invoke
                    methods["Activate"]=around_activate(base.Activate,profile);methods["TargetData"]=around_data(base.TargetData,profile)
                    for name in ("FireComplete","MontageCompleted","MontageInterrupted","MontageCancelled"):
                        def around_end(handler,label,override):
                            def invoke(ability):
                                if owner.armed and wire.same(wire.read(ability.call_function("GetAvatarActorFromActorInfo")),owner.command["source_identity"]):owner.callbacks.append(dict(name=label,time=owner.game_time()))
                                return handler(ability)
                            invoke.override=override;return invoke
                        fn=getattr(base,name);methods[name]=around_end(fn,name,getattr(fn,"override",name))
                else:
                    def around_weapon(handler):
                        def invoke(actor,*args):
                            if owner.armed and wire.same(wire.read(actor.call_function("GetOwner")),owner.command["source_identity"]):owner.weapon_events.append(dict(actor=path(actor),owner=wire.read(actor.call_function("GetOwner"))))
                            return handler(actor,*args)
                        invoke.override="Fire";return invoke
                    methods["Fire"]=around_weapon(base.Fire)
                ue.register_mixin_profile(cls,profile,type("ObservedNetworkWeaponFire"+self.peer+str(len(self.observers))+profile,(),methods))
    def find_identity(self,wanted):
        pawns,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.find_class("LyraCharacter"))
        return next((value for value in pawns if valid(value) and wire.same(wire.read(value),wanted)),None)
    def arm(self):
        self.armed=True;self.activations=[];self.target_data=[];self.weapon_events=[];self.callbacks=[];self.health_after=None;self.quiet=0
        self.source=self.find_identity(self.command["source_identity"]);self.victim=self.find_identity(self.command["target_identity"])
        self.native_target_identity=wire.read(self.victim)
        self.human_before={peer:health_value(value) for peer,value in self.humans.items()}
    def sample(self):
        if not self.armed:return
        value=health_value(self.victim)
        if value is not None:
            self.quiet=self.quiet+1 if self.health_after==value else 0;self.health_after=value
    def select_profile(self,ability,profile):
        if not any(value[0]==ability for value in self.saved_profiles):self.saved_profiles.append((ability,str(ue.get_mixin_profile(ability))))
        ue.set_mixin_profile(ability,profile)
    def snapshot(self):
        ability=ability_for(self.source,ue.load_class(WEAPONS[self.weapon])) if self.peer=="server" or self.peer==self.command["owner"] else None
        return dict(position=self.position,owner=self.command["owner"],profile=self.command["profile"],native_class=WEAPONS[self.weapon],
            source_identity=wire.read(self.source),target_identity=self.native_target_identity,activations=copy.deepcopy(self.activations),target_data=copy.deepcopy(self.target_data),
            callbacks=copy.deepcopy(self.callbacks),health_after=self.health_after,quiet_ticks=self.quiet,weapon_fire_entries=len(self.weapon_events),
            human_health_after={peer:health_value(value) for peer,value in self.humans.items()},human_health_unchanged=all(health_value(value)==self.human_before[peer] for peer,value in self.humans.items()),
            ability_ended=ability is None or not ability.get_property("bIsActive"))
    def close_observers(self):
        self.armed=False;restored=True
        for ability,profile in self.saved_profiles:
            if valid(ability):ue.set_mixin_profile(ability,profile)
        for cls,profiles in self.observers.items():
            for name,base in profiles.items():ue.register_mixin_profile(cls,name,base)
            row,=[r for r in ue.get_registered_mixins() if r["target_class"]==cls]
            restored&=all(row["profiles"][name]["python_class"] is base for name,base in profiles.items())
        self.report["observers_restored"]=restored
        self.report["native_prediction_exports"]=copy.deepcopy(self.prediction_exports)
    def write(self):atomic_write(self.path,self.report)
    def acknowledge(self,stage,row):atomic_write(self.root/(self.peer+"-"+str(self.position)+"-"+stage+".json"),dict(run_id=self.run,position=self.position,attempt=self.command.get("attempt",0),row=row))


class Client(Witness,Ready):
    def __init__(self,result,peer,run):
        Ready.__init__(self,result);self.init_witness(result,peer,run);self.require_auto_active=False;self.require_local_playing_phase=False;self.original_model=None;self.original_control=None
    def ready(self):
        if token(self.root,"playing-ready.json",self.run) is not None:Ready.ready(self)
    def begin(self):
        bridge=policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld",self.world);self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Client","network firing owner is not native client")
        self.player_id=int(self.controller.PlayerState.PlayerId);self.report["player_id"]=self.player_id;self.original_model=capture(self.controller);self.original_control=self.controller.call_function("GetControlRotation")
        require(self.original_model is not None and "ID_Pistol" in self.original_model["definition"],"original network pistol inventory required")
        self.install();self.actions=[ue.load_object(ue.find_class("InputAction"),"/Game/Input/Actions/"+name+"."+name) for name in ("IA_Weapon_Fire","IA_Weapon_Fire_Auto")]
        atomic_write(self.root/(self.peer+"-ready.json"),dict(run_id=self.run,player_id=self.player_id,original_model=self.original_model));self.enter("command")
    def humans_for(self,command):
        values={}
        for peer,value in command["players"].items():
            pawn=self.find_identity(value["identity"])
            if pawn is None or not binding_ready(pawn):return None
            values[peer]=pawn
        return values
    def prepare(self):
        humans=self.humans_for(self.command)
        if humans is None:return False
        self.humans=humans;self.source=self.find_identity(self.command["source_identity"]);self.victim=self.find_identity(self.command["target_identity"])
        if self.source is None or not binding_ready(self.victim):return False
        model=capture(self.controller)
        if model is None or fixtures.WEAPONS[self.weapon][2] not in model["definition"]:return False
        self.item=services(self.controller)[1].call_function("GetActiveSlotItem")
        if ammo_policy.ammo(self.item)[0]!=self.command["ammo_before"][self.peer]:return False
        self.own_ability=ability_for(self.pawn,ue.load_class(WEAPONS[self.weapon]))
        if self.own_ability is None:return False
        self.select_profile(self.own_ability,self.command["profile"]);self.arm();self.input_gestures=0;self.released=True
        self.ammo_before=ammo_policy.ammo(self.item)[0];self.prepare_started=time.monotonic();self.enter("aim")
        return True
    def inject(self,value):
        for action in self.actions:self.controller.inject_enhanced_input_for_action(action,value)
    def aim(self):
        if self.peer==self.command["owner"]:
            camera=self.controller.get_property("PlayerCameraManager");point=self.victim.get_property("Mesh").call_function("GetSocketLocation","spine_03")
            self.controller.call_function("SetControlRotation",policy.lib("KismetMathLibrary").call_function("FindLookAtRotation",camera.call_function("GetCameraLocation"),point))
        if time.monotonic()-self.prepare_started<.6:return
        clear=True
        if self.peer==self.command["owner"]:
            camera=self.controller.get_property("PlayerCameraManager");point=self.victim.get_property("Mesh").call_function("GetSocketLocation","spine_03")
            clear=line_of_sight(self.source,camera.call_function("GetCameraLocation"),point,self.victim)
        self.acknowledge("ready",dict(source_identity=wire.read(self.source),target_identity=wire.read(self.victim),health=health_value(self.victim),ammo=self.ammo_before,
            native_line_of_sight=clear,control=rot(self.controller.call_function("GetControlRotation"))))
        self.enter("command")
    def collect(self):
        self.sample();owner=self.peer==self.command["owner"]
        expected_ammo=self.ammo_before-1 if owner else self.ammo_before
        if self.health_after is None or self.health_after>=self.command["health_before"] or self.quiet<6 or ammo_policy.ammo(self.item)[0]!=expected_ammo:return
        row=self.snapshot()
        if owner and (len(self.activations)!=1 or len(self.target_data)!=1 or not row["ability_ended"]):return
        if len(self.weapon_events)!=1:return
        row.update(input_gestures=self.input_gestures,input_released=self.released,ammo_before=self.ammo_before,ammo_after=ammo_policy.ammo(self.item)[0])
        self.report["cases"].append(row);self.acknowledge("done",row);self.completed=self.position;self.armed=False;self.enter("command")
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<500.,"native firing client timeout")
            if self.phase=="ready":self.ready()
            elif self.phase=="release":
                if token(self.root,"release.json",self.run) is not None:self.finish()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"));self.sample()
                if self.phase=="aim":self.aim()
                elif self.phase=="observe":self.inject(False);self.released=True;self.collect()
                else:
                    command=token(self.root,"fire-command.json",self.run)
                    if command is not None and accept_command(command,self.completed,self.processed):
                        self.command=command;self.position=command["position"]
                        if command["stage"]=="prepare":
                            if self.prepare():self.processed=(self.position,"prepare",command.get("attempt",0))
                        elif command["stage"]=="fire":
                            if self.peer==command["owner"]:self.inject(True);self.input_gestures=1;self.released=False
                            self.processed=(self.position,"fire",command.get("attempt",0));self.enter("observe")
                        elif command["stage"]=="collect":self.processed=(self.position,"collect",command.get("attempt",0));self.enter("observe")
                        elif capture(self.controller)==self.original_model:
                            self.processed=(self.position,"complete",command.get("attempt",0));self.acknowledge("complete",dict(cleanup=True));self.enter("release")
            self.report.update(phase=self.phase,position=self.position,pending_activations=self.activations,pending_target_data=self.target_data,pending_health=self.health_after,pending_weapon_entries=len(self.weapon_events));self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:
            if hasattr(self,"actions"):self.inject(False)
            if self.original_control is not None:
                self.controller.call_function("SetControlRotation",self.original_control);current=rot(self.controller.call_function("GetControlRotation"));original=rot(self.original_control)
                self.report["control_rotation_restored"]=all(abs(a-b)<.001 for a,b in zip(current,original))
            self.report["original_inventory_restored"]=self.original_model is not None and capture(self.controller)==self.original_model
            self.close_observers()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write();ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":self.report["status"]="passed"
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_FIRE_NETWORK_SHUTDOWN_"+self.report["status"].upper())


class Server(Witness,Playing):
    def __init__(self,result,run):
        Playing.__init__(self,result,run);self.init_witness(result,"server",run);self.position=0;self.stage=None;self.setup_done=False;self.released=False
        self.originals={};self.fixtures={};self.original_models={};self.original_poses={};self.bot_poses=[];self.created_bots=[];self.last_spawn=0.;self.report["server_waited_for_client_process_exit"]=False
    def publish(self,stage):
        self.stage=stage;self.stage_started=time.monotonic()
        atomic_write(self.root/"fire-command.json",dict(run_id=self.run,position=self.position,stage=stage,**self.command))
    def acks(self,stage):
        rows={peer:token(self.root,peer+"-"+str(self.position)+"-"+stage+".json",self.run,self.position) for peer in PEERS}
        return rows if all(value is not None and value.get("attempt",0)==self.command.get("attempt",0) for value in rows.values()) else None
    def setup(self):
        ready={peer:token(self.root,peer+"-ready.json",self.run) for peer in PEERS}
        if not all(ready.values()):return
        require(len({row["player_id"] for row in ready.values()})==2,"network fire owners not distinct")
        self.world=ue.find_object(self.report["native_playing_gate"]["stable_authority_pawns"][0][1]).get_world()
        controllers,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.find_class("LyraPlayerController"))
        owners={}
        for peer,row in ready.items():
            matches=[value for value in controllers if valid(value.PlayerState) and int(value.PlayerState.PlayerId)==row["player_id"]]
            if len(matches)!=1 or not binding_ready(matches[0].get_controlled_pawn()):return
            owners[peer]=dict(controller=matches[0],pawn=matches[0].get_controlled_pawn(),player_id=row["player_id"])
        self.owners=owners;self.humans={peer:value["pawn"] for peer,value in owners.items()};self.report["player_ids"]={peer:value["player_id"] for peer,value in owners.items()}
        bridge=policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld",self.world)
        self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="DedicatedServer","network firing authority is not a native dedicated server")
        self.install()
        state=self.statics.call_function("GetGameState",self.world);self.bot_component=state.get_component_by_type(ue.find_class("LyraBotCreationComponent"))
        self.teams=policy.lib("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem",self.world,ue.find_class("LyraTeamSubsystem"))
        for peer,value in owners.items():
            self.original_models[peer]=capture(value["controller"]);self.original_poses[peer]=(value["pawn"].get_actor_location(),value["pawn"].get_actor_rotation())
            if self.weapon!="pistol":self.fixtures[peer]=fixtures.install(value["controller"],self.weapon)
        anchor=owners["A"]["pawn"].get_actor_location()
        require(owners["B0"]["pawn"].call_function("K2_TeleportTo",ue.FVector(anchor.x+600.,anchor.y+600.,anchor.z),owners["B0"]["pawn"].get_actor_rotation()),"native observer player proximity arrangement failed")
        self.setup_done=True;self.stage="equipping";self.stage_started=time.monotonic()
    def bots(self):
        values,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.find_class("LyraPlayerBotController"));return list(values)
    def find_target(self,source):
        for controller in self.bots():
            pawn=controller.get_controlled_pawn()
            if binding_ready(pawn) and self.teams.call_function("CompareTeams",source,pawn)[0]==ELyraTeamComparison.DifferentTeams:return pawn
        if time.monotonic()-self.last_spawn>3.:
            require(valid(self.bot_component) and len(self.created_bots)<6,"bounded native enemy bot preparation exhausted")
            before={path(value) for value in self.bots()};self.bot_component.call_function("SpawnOneBot")
            self.created_bots.extend(value for value in self.bots() if path(value) not in before);self.last_spawn=time.monotonic()
        return None
    def equipped(self):
        cls=ue.load_class(WEAPONS[self.weapon])
        for peer,value in self.owners.items():
            model=capture(value["controller"]);ability=ability_for(value["pawn"],cls)
            if model is None or fixtures.WEAPONS[self.weapon][2] not in model["definition"] or ability is None:return
            value["ability"]=ability;value["item"]=services(value["controller"])[1].call_function("GetActiveSlotItem")
            self.originals[peer]=ammo_policy.ammo(value["item"])
        self.stage="start";self.stage_started=time.monotonic()
    def start(self):
        owner,profile=PLAN[self.position];selected=self.owners[owner];ability=selected["ability"]
        if ability.get_property("bIsActive"):return
        victim=self.find_target(selected["pawn"])
        if victim is None:return
        if not any(value[0]==victim for value in self.bot_poses):self.bot_poses.append((victim,victim.get_actor_location(),victim.get_actor_rotation()))
        self.pose_attempt=0;self.pose_target(victim,selected["pawn"])
        source_id,target_id=wire.read(selected["pawn"]),wire.read(victim)
        if wire.key(source_id) is None or wire.key(target_id) is None:return
        self.select_profile(ability,profile);set_stat(selected["item"],ammo_policy.MAGAZINE,max(3,self.originals[owner][1]//2))
        self.command=dict(owner=owner,profile=profile,attempt=self.pose_attempt,source_identity=source_id,target_identity=target_id,health_before=health_value(victim),
            ammo_before={peer:ammo_policy.ammo(value["item"])[0] for peer,value in self.owners.items()},
            players={peer:dict(player_id=value["player_id"],identity=wire.read(value["pawn"])) for peer,value in self.owners.items()})
        self.arm();self.ammo_before=ammo_policy.ammo(selected["item"])[0];self.publish("prepare")
    def pose_target(self,victim,source):
        point=source.get_actor_location();forward=source.call_function("GetActorForwardVector")
        while self.pose_attempt<24:
            angle=math.radians(45.*(self.pose_attempt%8));distance=(350.,450.,550.)[self.pose_attempt//8]
            x=forward.x*math.cos(angle)-forward.y*math.sin(angle);y=forward.x*math.sin(angle)+forward.y*math.cos(angle)
            if victim.call_function("K2_TeleportTo",ue.FVector(point.x+x*distance,point.y+y*distance,point.z),victim.get_actor_rotation()):
                victim.get_property("CharacterMovement").call_function("StopMovementImmediately");return
            self.pose_attempt+=1
        raise RuntimeError("bounded native clear-line target poses exhausted")
    def step(self):
        require(time.monotonic()-self.stage_started<60.,"native network fire stage timeout: "+str(self.stage))
        if self.stage=="equipping":self.equipped()
        elif self.stage=="start":self.start()
        elif self.stage=="prepare":
            acks=self.acks("ready")
            if acks is None:return
            if not acks[self.command["owner"]]["row"]["native_line_of_sight"]:
                self.pose_attempt+=1;self.pose_target(self.victim,self.source);self.command["attempt"]=self.pose_attempt
                self.publish("prepare");return
            desired=acks[self.command["owner"]]["row"]["control"];actual=rot(self.owners[self.command["owner"]]["controller"].call_function("GetControlRotation"))
            if any(abs((a-b+180.)%360.-180.)>3. for a,b in zip(actual,desired)):return
            self.native_aim_sync=True;self.publish("fire")
        elif self.stage=="fire":
            self.sample();acks=self.acks("done")
            if acks is None:return
            selected=self.owners[self.command["owner"]];ability=selected["ability"]
            if ability.get_property("bIsActive") or len(self.activations)!=1 or len(self.target_data)!=1 or self.quiet<6:return
            row=self.snapshot();row.update(ammo_before=self.ammo_before,ammo_after=ammo_policy.ammo(selected["item"])[0],health_before=self.command["health_before"],native_aim_sync=self.native_aim_sync)
            if any(value["row"]["health_after"]!=self.health_after for value in acks.values()):return
            self.report["cases"].append(row);self.armed=False;self.position+=1
            for tag,value in zip((ammo_policy.MAGAZINE,ammo_policy.CAPACITY,ammo_policy.SPARE),self.originals[self.command["owner"]]):set_stat(selected["item"],tag,value)
            if self.position==len(PLAN):
                self.restore();self.command={};self.publish("complete")
            else:self.stage="start";self.stage_started=time.monotonic()
        elif self.stage=="complete":
            if self.acks("complete") is None:return
            if not self.released:atomic_write(self.root/"release.json",dict(run_id=self.run));self.released=True
            exits=[token(self.root,peer+"-exited.json",self.run) for peer in PEERS]
            if all(value is not None and value["exit_code"]==0 for value in exits):self.report["server_waited_for_client_process_exit"]=True;self.finish()
    def restore(self):
        self.armed=False
        for peer,value in self.owners.items():
            if peer in self.originals:
                for tag,count in zip((ammo_policy.MAGAZINE,ammo_policy.CAPACITY,ammo_policy.SPARE),self.originals[peer]):set_stat(value["item"],tag,count)
            if peer in self.fixtures:fixtures.restore(value["controller"],self.fixtures[peer])
            point,rotation=self.original_poses[peer];value["pawn"].call_function("K2_TeleportTo",point,rotation)
        self.report["original_inventory_restored"]=all(capture(value["controller"])==self.original_models[peer] for peer,value in self.owners.items())
        for pawn,point,rotation in self.bot_poses:
            if valid(pawn) and not pawn.call_function("IsActorBeingDestroyed"):pawn.call_function("K2_TeleportTo",point,rotation)
        for controller in reversed(self.created_bots):
            if valid(controller):
                values=list(self.bot_component.get_property("SpawnedBotList"));require(values and values[-1]==controller,"do not remove a foreign native bot")
                self.bot_component.call_function("RemoveOneBot")
        self.close_observers()
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<500.,"native firing authority total timeout")
            if not self.playing_gate:self.wait_playing()
            elif not self.setup_done:self.setup()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"));self.step()
            self.report.update(stage=self.stage,position=self.position,pending_activations=self.activations,pending_target_data=self.target_data,pending_health=self.health_after);self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:
            if error and self.setup_done:self.restore()
            elif not self.setup_done:self.close_observers()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write();ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":self.report["status"]="passed"
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_FIRE_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPWeaponAbilityFireNetworkResult=") for value in sys.argv):
    result,peer,run=arg("-UEPWeaponAbilityFireNetworkResult="),arg("-UEPJumpPeer="),arg("-UEPJumpRun=")
    validation=Server(result,run) if peer=="server" else Client(result,peer,run)
    atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
