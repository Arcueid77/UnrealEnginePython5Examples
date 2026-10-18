"""Native swept blocking contact produces Hit; never invoke ReceiveHit."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Activation
from . import grenade_hit_mixin as policy
from .grenade_hit_contract import CLASS,PLAN,require,validate


def path(obj): return obj.get_path_name() if valid(obj) else None
def vector(obj): return [float(obj.x),float(obj.y),float(obj.z)]


class Validation(Ready):
    healths=Activation.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.target=None;self.actors=[];self.events=[];self.installed=False;self.cleaned=False
        self.report=dict(schema_version=1,status="running",error=None,cases=[],observation_errors=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,
            physical_input_tested=False,hit_callback_replayed=False,health_properties_written=False,raw_velocity_written=False,enemy_hit_detonation_tested=False,
            native_rpc_detonate_body_migrated=False,audio_playback_tested=False,quantitative_flight_physics_tested=False,native_blocking_sweep_used=True)
    def box(self,label,location,extent):
        actor=self.world.actor_spawn(ue.find_class("Actor"),location);self.actors.append(actor)
        box=actor.add_actor_root_component(ue.find_class("BoxComponent"),label);box.call_function("SetBoxExtent",extent,False)
        box.call_function("SetCollisionObjectType",0);box.call_function("SetCollisionResponseToAllChannels",2);box.call_function("SetCollisionEnabled",1)
        require(actor.call_function("K2_TeleportTo",location,ue.FRotator()),"native collision fixture pose refused");return actor,box
    def begin(self):
        bridge=ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world)
        self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode);require(self.report["native_mode"]=="Standalone","native swept Hit standalone world required")
        self.cls=ue.load_class(CLASS);ue.register_declared_mixin(self.cls);self.teams=ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem",self.world,ue.find_class("LyraTeamSubsystem"))
        self.floor,_=self.box("UEPHitFloor",ue.FVector(200000.,200000.,1980.),ue.FVector(5000.,5000.,20.))
        self.wall,self.wall_box=self.box("UEPHitWall",ue.FVector(200400.,200000.,2100.),ue.FVector(10.,200.,200.));self.wall_box.call_function("SetCollisionEnabled",0)
        binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==self.cls];self.original_classes={name:value["python_class"] for name,value in binding["profiles"].items()};owner=self
        for name,base in self.original_classes.items():
            def around(handler,profile):
                def invoke(actor,MyComp,Other,OtherComp,bSelfMoved,HitLocation,HitNormal,NormalImpulse,Hit):
                    watched=actor==owner.target;row=None
                    if watched:
                        try:
                            comparison=owner.teams.call_function("CompareTeams",Other,actor.get_property("Instigator"))
                            row=dict(profile=profile,native_generated_callback=True,my_component=path(MyComp),other=path(Other),other_component=path(OtherComp),location=vector(HitLocation),
                                comparison=int(comparison[0]),fuse_exists_before=owner.fuse(actor))
                        except Exception: owner.report["observation_errors"].append(traceback.format_exc())
                    handler(actor,MyComp,Other,OtherComp,bSelfMoved,HitLocation,HitNormal,NormalImpulse,Hit)
                    if row is not None:
                        try: row.update(fuse_exists_after=owner.fuse(actor),stats=copy.deepcopy(policy.evidence(actor)));owner.events.append(row)
                        except Exception: owner.report["observation_errors"].append(traceback.format_exc())
                return invoke
            methods={key:value for key,value in vars(base).items() if not key.startswith("__") and callable(value)};methods["ReceiveHit"]=around(base.ReceiveHit,name)
            ue.register_mixin_profile(self.cls,name,type("ObservedGrenadeHit"+name,(),methods))
        self.installed=True;self.enter("source")
    def fuse(self,actor): return bool(ue.find_class("KismetSystemLibrary").get_cdo().call_function("K2_TimerExistsHandle",self.world,actor.get_property("Timer")))
    def source(self):
        require(time.monotonic()-self.phase_started<30.,"actual living same-team bot source missing")
        bots,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.find_class("LyraPlayerBotController"))
        for controller in bots:
            pawn=controller.get_controlled_pawn()
            if not valid(pawn): continue
            health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            if not valid(health) or health.call_function("GetHealth")!=100.: continue
            if int(self.teams.call_function("CompareTeams",pawn,self.pawn)[0])!=0: continue
            self.friend=pawn;self.friend_pose=(pawn.get_actor_location(),pawn.get_actor_rotation());self.health_before=self.healths();self.enter("sweep");return
    def sweep(self):
        name,profile=PLAN[self.index];self.wall_box.call_function("SetCollisionEnabled",1 if name=="invalid-wall" else 0)
        destination=ue.FVector(200400. if name=="same-team" else 202000.,200000.,2100.)
        require(self.friend.call_function("K2_TeleportTo",destination,ue.FRotator()),"native friendly fixture pose refused");self.friend.call_function("GetMovementComponent").call_function("StopMovementImmediately")
        transform=ue.FTransform(ue.FVector(200000.,200000.,2100.),ue.FRotator(),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.OverrideRootScale
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,self.cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,None,scale)
        require(valid(actor),"native swept Grenade missing");self.actors.append(actor);actor.set_property("Instigator",self.pawn);ue.set_mixin_profile(actor,profile)
        self.target=actor;self.events=[];self.statics.call_function("FinishSpawningActor",actor,transform,scale)
        mesh=actor.get_property("Mesh");mesh.call_function("SetNotifyRigidBodyCollision",True)
        actor.call_function("K2_SetActorLocation",NewLocation=ue.FVector(200800.,200000.,2100.),bSweep=True,bTeleport=False)
        require(len(self.events)==1 and not self.report["observation_errors"],"actual native swept Hit missing/duplicated: "+str(self.report["observation_errors"]))
        row=dict(name=name,profile=profile,**{"class":path(actor.get_class())},mesh=path(mesh),expected_other=path(self.wall if name=="invalid-wall" else self.friend),native_hits=len(self.events),event=copy.deepcopy(self.events[0]))
        actor.call_function("K2_DestroyActor");row["actor_destroyed"]=not valid(actor) or bool(actor.call_function("IsActorBeingDestroyed"));self.target=None
        require(self.healths()==self.health_before,"non-detonating Hit fixture changed actual Pawn Health")
        self.report["cases"].append(row);self.index+=1;ue.log("UEP_GRENADE_HIT_CASE_PASSED "+name+" "+profile)
        if self.index==len(PLAN): self.quiet_ticks=0;self.enter("quiet")
    def quiet(self):
        require(self.healths()==self.health_before,"Hit quiet interval changed actual Pawn Health")
        self.quiet_ticks+=1
        if self.quiet_ticks>=20: self.report["quiet_ticks"]=self.quiet_ticks;self.finish()
    def cleanup(self):
        if self.cleaned: return
        self.target=None
        for actor in self.actors:
            if valid(actor) and not actor.call_function("IsActorBeingDestroyed"): actor.call_function("K2_DestroyActor")
        if hasattr(self,"friend_pose"): self.report["bot_pose_restored"]=bool(self.friend.call_function("K2_TeleportTo",*self.friend_pose))
        if self.installed:
            for name,base in self.original_classes.items(): ue.register_mixin_profile(self.cls,name,base)
            binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==self.cls]
            self.report["production_classes_restored"]=all(binding["profiles"][name]["python_class"] is base for name,base in self.original_classes.items())
        self.report.update(test_actors_destroyed=all(not valid(actor) or actor.call_function("IsActorBeingDestroyed") for actor in self.actors),all_pawn_health_unchanged=self.healths()==self.health_before if hasattr(self,"health_before") else False);self.cleaned=True
    def tick(self,seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<180.,"native Hit total timeout")
            if self.phase=="ready": self.ready()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                if self.phase=="source": self.source()
                elif self.phase=="sweep": self.sweep()
                elif self.phase=="quiet": self.quiet()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        if error: self.report["pending_hits"]=copy.deepcopy(self.events)
        try: self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_GRENADE_HIT_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try: self.report["status"]="passed";validate(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_HIT_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeHitResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
