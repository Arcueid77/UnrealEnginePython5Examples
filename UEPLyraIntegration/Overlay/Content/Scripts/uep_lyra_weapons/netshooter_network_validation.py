"""Real predicted NetShooter input; native free flight and wire-matched replicas."""
import atexit
import copy
import math
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from . import weapon_ability_fire_network_validation as base
from . import netshooter_ability_mixin as policy,weapon_ability_fire_mixin as parent,netshooter_actor_mixin as actor_policy
from .netshooter_network_contract import PEERS,PLAN,require,accept_command
from .weapon_fire_fx_validation import dead


class Witness(base.Witness):
    def init_witness(self,result,peer,run):
        base.Witness.init_witness(self,result,peer,run);self.weapon="netshooter";self.report["weapon"]="netshooter";self.actor=None;self.samples=[];self.actor_identity=None
        self.report.update(projectile_spawn_requested_by_fixture=False,impact_or_strand_replication_accepted=False,projectile_physics_written=False)
    def actors(self):return [value for value in self.world.all_actors() if base.valid(value) and value.is_a(ue.load_class(policy.PROJECTILE)) and not dead(value)]
    def install(self):
        owner=self
        for cls_path in (policy.CLASS,"/Game/Weapons/B_Weapon.B_Weapon_C"):
            cls=ue.load_class(cls_path);ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==cls]
            originals={name:value["python_class"] for name,value in row["profiles"].items()};self.observers[cls]=originals
            for profile,source in originals.items():
                methods={name:fn for name,fn in vars(source).items() if not name.startswith("__") and callable(fn)}
                if cls_path==policy.CLASS:
                    def around_activation(handler,selected):
                        def invoke(ability):
                            watched=owner.armed and base.wire.same(base.wire.read(ability.call_function("GetAvatarActorFromActorInfo")),owner.command["source_identity"])
                            before=set(owner.actors())
                            if watched:event=dict(profile=selected,authority=bool(ability.call_function("K2_HasAuthority")),locally_controlled=bool(ability.call_function("IsLocallyControlled")),mode=int(ability.get_property("CurrentActivationInfo").ActivationMode),prediction_key=base.prediction(ability,owner))
                            result=handler(ability)
                            if watched:
                                born=[value for value in owner.actors() if value not in before];event["native_spawn_delta"]=len(born);owner.activations.append(event)
                                if event["authority"]:
                                    require(len(born)==1,"authority NetShooter did not spawn one native projectile");owner.actor=born[0]
                            return result
                        invoke.override="K2_ActivateAbility";return invoke
                    def around_data(handler):
                        def invoke(ability,TargetData):
                            watched=owner.armed and base.wire.same(base.wire.read(ability.call_function("GetAvatarActorFromActorInfo")),owner.command["source_identity"])
                            if watched:owner.target_data.append(dict(authority=bool(ability.call_function("K2_HasAuthority")),prediction_key=base.prediction(ability,owner),count=int(policy.lib("AbilitySystemBlueprintLibrary").call_function("GetDataCountFromTargetData",TargetData))))
                            return handler(ability,TargetData)
                        invoke.override="OnRangedWeaponTargetDataReady";return invoke
                    methods["Activate"]=around_activation(source.Activate,profile);methods["TargetData"]=around_data(source.TargetData)
                else:
                    def around_fire(handler):
                        def invoke(actor,*args):
                            if owner.armed and base.wire.same(base.wire.read(actor.call_function("GetOwner")),owner.command["source_identity"]):owner.weapon_events.append(dict(actor=base.path(actor)))
                            return handler(actor,*args)
                        invoke.override="Fire";return invoke
                    methods["Fire"]=around_fire(source.Fire)
                ue.register_mixin_profile(cls,profile,type("ObservedNetShooter"+self.peer+str(len(self.observers))+profile,(),methods))
    def arm(self):
        base.Witness.arm(self);self.actor=None;self.samples=[];self.actor_identity=None;self.destroyed=False;self.actor_profile_selected=False
        ability=base.ability_for(self.source,ue.load_class(policy.CLASS)) if self.peer in ("server",self.command["owner"]) else None
        self.parent_before=copy.deepcopy(parent.evidence(ability)) if ability is not None else None
    def sample(self):
        if not self.armed:return
        if self.actor is None:
            found=[value for value in self.actors() if base.wire.same(base.wire.read(value.call_function("GetInstigator")),self.command["source_identity"])]
            require(len(found)<=1,"duplicate native NetShooter replicas")
            if not found:return
            self.actor=found[0]
        if dead(self.actor):self.destroyed=True;return
        if not self.actor_profile_selected:
            ue.set_mixin_profile(self.actor,self.command["profile"]);self.actor_profile_selected=True
        identity=base.wire.read(self.actor)
        if base.wire.key(identity) is not None:self.actor_identity=identity
        point=base.vector(self.actor.get_actor_location());now=self.game_time()
        if not self.samples or self.samples[-1]["time"]!=now:
            require(len(self.samples)<512,"native NetShooter trajectory exceeded bound")
            self.samples.append(dict(time=now,location=point,velocity=base.vector(self.actor.get_property("ProjectileMovement").get_property("Velocity"))))
        self.rep_flags=(bool(self.actor.get_property("bReplicates")),bool(self.actor.get_property("bReplicateMovement")))
        self.natural_hits=sum(actor_policy.evidence(self.actor)[name] for name in ("hit_bodies","fallback_hit_bodies"))
    def snapshot(self):
        ability=base.ability_for(self.source,ue.load_class(policy.CLASS)) if self.peer in ("server",self.command["owner"]) else None
        count=0
        if ability is not None:
            after=parent.evidence(ability);count=sum(after[name]-self.parent_before[name] for name in ("target_data_calls","fallback_target_data_calls"))
        distance=math.dist(self.samples[0]["location"],self.samples[-1]["location"]) if self.samples else 0.
        return dict(position=self.position,owner=self.command["owner"],profile=self.command["profile"],source_identity=base.wire.read(self.source),projectile_identity=self.actor_identity,
            activations=copy.deepcopy(self.activations),target_data=copy.deepcopy(self.target_data),parent_target_data_calls=count,ability_ended=ability is None or not ability.get_property("bIsActive"),
            weapon_fire_entries=len(self.weapon_events),native_moving_samples=len({tuple(value["location"]) for value in self.samples}),distance_moved=distance,trajectory=copy.deepcopy(self.samples),
            projectile_replicates=self.rep_flags[0],projectile_replicates_movement=self.rep_flags[1],natural_hit_entries=self.natural_hits,projectile_destruction_observed=self.destroyed,
            human_health_unchanged=all(base.health_value(value)==self.human_before[peer] for peer,value in self.humans.items()))


class Client(Witness,base.Client):
    def prepare(self):
        humans=self.humans_for(self.command);model=base.capture(self.controller)
        if humans is None or model is None or "ID_NetShooter" not in model["definition"]:return False
        if any(value.get_actor_location().z<8000. for value in humans.values()):return False
        self.humans=humans;self.item=base.services(self.controller)[1].call_function("GetActiveSlotItem")
        if base.ammo_policy.ammo(self.item)[0]!=self.command["ammo_before"][self.peer]:return False
        self.own_ability=base.ability_for(self.pawn,ue.load_class(policy.CLASS))
        if self.own_ability is None:return False
        self.select_profile(self.own_ability,self.command["profile"]);self.arm();self.input_gestures=0;self.released=True;self.pending_row=None
        self.ammo_before=base.ammo_policy.ammo(self.item)[0];self.prepare_started=time.monotonic();self.enter("aim");return True
    def aim(self):
        if self.peer==self.command["owner"]:self.controller.call_function("SetControlRotation",ue.FRotator(0.,50.,45.))
        if time.monotonic()-self.prepare_started<.7:return
        camera=self.controller.get_property("PlayerCameraManager")
        if camera.call_function("GetCameraLocation").z<8000.:return
        self.acknowledge("ready",dict(control=base.rot(self.controller.call_function("GetControlRotation")),native_line_of_sight=True));self.enter("command")
    def collect(self):
        self.sample()
        if self.pending_row is not None:
            if not self.destroyed:return
            self.pending_row["projectile_destruction_observed"]=True;self.report["cases"].append(self.pending_row);self.acknowledge("cleanup",dict(destroyed=True))
            self.completed=self.position;self.armed=False;self.enter("command");return
        owner=self.peer==self.command["owner"];expected=self.ammo_before-1 if owner else self.ammo_before
        if self.actor_identity is None or len(self.samples)<3 or base.ammo_policy.ammo(self.item)[0]!=expected or len(self.weapon_events)!=1:return
        row=self.snapshot()
        if row["distance_moved"]<100. or (owner and (len(self.activations)!=1 or len(self.target_data)!=1 or not row["ability_ended"])):return
        row.update(input_gestures=self.input_gestures,input_released=self.released,ammo_before=self.ammo_before,ammo_after=base.ammo_policy.ammo(self.item)[0])
        self.pending_row=row;self.acknowledge("done",row)
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":self.report["status"]="passed"
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_NETSHOOTER_NETWORK_SHUTDOWN_"+self.report["status"].upper())


class Server(Witness,base.Server):
    def __init__(self,result,run):
        base.Server.__init__(self,result,run);self.original_modes={};self.clearing=False
    def setup(self):
        base.Server.setup(self)
        if not self.setup_done:return
        for index,(peer,value) in enumerate(self.owners.items()):
            pawn=value["pawn"];movement=pawn.get_property("CharacterMovement");self.original_modes[peer]=(int(movement.get_property("MovementMode")),int(movement.get_property("CustomMovementMode")))
            movement.call_function("SetMovementMode",5,0);movement.call_function("StopMovementImmediately")
            require(pawn.call_function("K2_TeleportTo",ue.FVector(50000.,50000.+index*1500.,10000.),ue.FRotator()),"native open-air source pose refused")
    def equipped(self):
        for peer,value in self.owners.items():
            model=base.capture(value["controller"]);ability=base.ability_for(value["pawn"],ue.load_class(policy.CLASS))
            if model is None or "ID_NetShooter" not in model["definition"] or ability is None:return
            value["ability"]=ability;value["item"]=base.services(value["controller"])[1].call_function("GetActiveSlotItem");self.originals[peer]=base.ammo_policy.ammo(value["item"])
        self.stage="start";self.stage_started=time.monotonic()
    def start(self):
        owner,profile=PLAN[self.position];selected=self.owners[owner]
        if selected["ability"].get_property("bIsActive"):return
        self.select_profile(selected["ability"],profile);base.set_stat(selected["item"],base.ammo_policy.MAGAZINE,8)
        other=next(peer for peer in PEERS if peer!=owner)
        self.command=dict(owner=owner,profile=profile,source_identity=base.wire.read(selected["pawn"]),target_identity=base.wire.read(self.owners[other]["pawn"]),
            ammo_before={peer:base.ammo_policy.ammo(value["item"])[0] for peer,value in self.owners.items()},
            players={peer:dict(player_id=value["player_id"],identity=base.wire.read(value["pawn"])) for peer,value in self.owners.items()})
        self.arm();self.ammo_before=base.ammo_policy.ammo(selected["item"])[0];self.clearing=False;self.publish("prepare")
    def step(self):
        require(time.monotonic()-self.stage_started<65.,"native NetShooter network stage timeout: "+str(self.stage))
        if self.stage=="equipping":self.equipped()
        elif self.stage=="start":self.start()
        elif self.stage=="prepare":
            acks=self.acks("ready")
            if acks is None:return
            selected=self.owners[self.command["owner"]];actual=base.rot(selected["controller"].call_function("GetControlRotation"));desired=acks[self.command["owner"]]["row"]["control"]
            if any(abs((a-b+180.)%360.-180.)>3. for a,b in zip(actual,desired)):return
            if selected["controller"].get_property("PlayerCameraManager").call_function("GetCameraLocation").z<8000.:return
            self.native_aim_sync=True;self.publish("fire")
        elif self.stage=="fire":
            self.sample();selected=self.owners[self.command["owner"]]
            if not self.clearing:
                if self.acks("done") is None or self.actor_identity is None or selected["ability"].get_property("bIsActive") or len(self.activations)!=1 or len(self.target_data)!=1:return
                row=self.snapshot();row.update(ammo_before=self.ammo_before,ammo_after=base.ammo_policy.ammo(selected["item"])[0],native_aim_sync=self.native_aim_sync,authority_fixture_cleanup=True)
                require(row["native_moving_samples"]>=3 and row["distance_moved"]>=100. and row["natural_hit_entries"]==0,"authority natural free-flight window missing")
                self.actor.call_function("K2_DestroyActor");self.sample();row["projectile_destruction_observed"]=self.destroyed;self.report["cases"].append(row);self.clearing=True
            elif self.acks("cleanup") is not None:
                self.armed=False;self.position+=1
                for tag,value in zip((base.ammo_policy.MAGAZINE,base.ammo_policy.CAPACITY,base.ammo_policy.SPARE),self.originals[self.command["owner"]]):base.set_stat(selected["item"],tag,value)
                if self.position==len(PLAN):self.restore();self.command={};self.publish("complete")
                else:self.stage="start";self.stage_started=time.monotonic()
        elif self.stage=="complete":
            if self.acks("complete") is None:return
            if not self.released:atomic_write(self.root/"release.json",dict(run_id=self.run));self.released=True
            exits=[base.token(self.root,peer+"-exited.json",self.run) for peer in PEERS]
            if all(row is not None and row["exit_code"]==0 for row in exits):self.report["server_waited_for_client_process_exit"]=True;self.finish()
    def restore(self):
        if self.actor is not None and not dead(self.actor):self.actor.call_function("K2_DestroyActor")
        for peer,(mode,custom) in self.original_modes.items():self.owners[peer]["pawn"].get_property("CharacterMovement").call_function("SetMovementMode",mode,custom)
        base.Server.restore(self)
        self.report["original_native_pose_movement_restored"]=all(math.dist(base.vector(value["pawn"].get_actor_location()),base.vector(self.original_poses[peer][0]))<.1 and int(value["pawn"].get_property("CharacterMovement").get_property("MovementMode"))==self.original_modes[peer][0] for peer,value in self.owners.items())
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":self.report["status"]="passed"
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_NETSHOOTER_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPNetShooterNetworkResult=") for value in sys.argv):
    result,peer,run=base.arg("-UEPNetShooterNetworkResult="),base.arg("-UEPJumpPeer="),base.arg("-UEPJumpRun=")
    validation=Server(result,run) if peer=="server" else Client(result,peer,run)
    atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
