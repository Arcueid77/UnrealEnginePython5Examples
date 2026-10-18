"""Real retained Actor ordinary business entries; no fuse/completion replay."""
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
from . import grenade_actions_mixin as policy,grenade_vfx_mixin as vfx
from .grenade_actions_contract import CLASS,PLAN,require,validate
from .grenade_vfx_validation import Validation as VFXWarmup


def path(obj): return obj.get_path_name() if valid(obj) else None
def vector(obj): return [float(obj.x),float(obj.y),float(obj.z)]
def rotation(obj): return [float(obj.roll),float(obj.pitch),float(obj.yaw)]


class Validation(Ready):
    healths=Activation.healths
    warmup=VFXWarmup.warmup
    warm=VFXWarmup.warm
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.cleaned=False
        self.report=dict(schema_version=1,status="running",error=None,cases=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,
            physical_input_tested=False,begin_play_replayed=False,native_completion_delegate_replayed=False,health_properties_written=False,raw_velocity_written=False,
            quantitative_flight_physics_tested=False,native_trail_completion_tested=False,fuse_detonate_damage_migrated=False,ordinary_action_entries_called_by_fixture=True,test_grenade_collision_disabled=True,
            native_zero_velocity_entry="ProjectileMovement.SetVelocityInLocalSpace")
    def begin(self):
        bridge=ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world)
        self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode);require(self.report["native_mode"]=="Standalone","native actions standalone world required")
        self.cls=ue.load_class(CLASS);ue.register_declared_mixin(self.cls)
        binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==self.cls]
        self.original_profile_classes={name:value["python_class"] for name,value in binding["profiles"].items()}
        self.health_before=self.healths();self.warmup()
    def state(self,actor):
        movement=actor.get_property("ProjectileMovement");trail=actor.get_property("NS_Trail")
        components=actor.call_function("K2_GetComponentsByClass",ue.find_class("NiagaraComponent"))
        return dict(location=vector(actor.get_actor_location()),rotation=rotation(actor.get_actor_rotation()),velocity=vector(movement.get_property("Velocity")),
            conserved=float(actor.get_property("ConservedVelocity")),movement_active=bool(movement.call_function("IsActive")),trail=path(trail),trail_valid=valid(trail),trail_active=bool(trail.call_function("IsActive")) if valid(trail) else False,
            matching_components=len([value for value in components if valid(value) and path(value.call_function("GetAsset"))==vfx.TRAIL]))
    def spawn(self):
        name,profile=PLAN[self.index];point=self.pawn.get_actor_location();position=ue.FVector(point.x+500.,point.y,point.z+400.)
        transform=ue.FTransform(position,ue.FRotator(0.,10.,25.),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.OverrideRootScale
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,self.cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,None,scale)
        require(valid(actor),"actual native Actor action source missing");self.actors.append(actor);actor.set_property("Instigator",self.pawn);ue.set_mixin_profile(actor,profile)
        actor.call_function("SetActorEnableCollision",False);self.statics.call_function("FinishSpawningActor",actor,transform,scale)
        require(actor.call_function("GetActorEnableCollision") is False,"native test Actor collision not disabled")
        movement=actor.get_property("ProjectileMovement");old_trail=actor.get_property("NS_Trail");require(valid(old_trail),"native original/Python VFX source trail missing")
        if name=="zero-speed": movement.call_function("SetVelocityInLocalSpace",ue.FVector())
        if name=="invalid-trail": old_trail.call_function("K2_DestroyComponent",actor);require(not valid(actor.get_property("NS_Trail")),"native source trail component did not destroy")
        before=self.state(actor);destination=ue.FVector(position.x+1000.,position.y-700.,position.z+100.)
        forward=ue.FVector(0.,2. if name=="nonunit-forward" else 1.,0.)
        actor.call_function(policy.TELEPORT,destination,forward)
        after=self.state(actor);stats=policy.evidence(actor) # Hold POD dict before native destruction invalidates wrapper.
        row=dict(name=name,profile=profile,**{"class":path(actor.get_class())},before=before,after=after,destination=vector(destination),forward=vector(forward),
            old_trail_active_after=bool(old_trail.call_function("IsActive")) if valid(old_trail) else False)
        values=vfx.evidence(actor);row["vfx_helper_calls"]=values["python_calls"]+values["fallback_calls"]
        actor.call_function(policy.DESTROY,actor.get_property("NS_Trail") if valid(actor.get_property("NS_Trail")) else None)
        row.update(stats=copy.deepcopy(stats),native_destroyed=not valid(actor) or bool(actor.call_function("IsActorBeingDestroyed")))
        require(self.healths()==self.health_before,"native action fixture changed actual Pawn Health")
        self.report["cases"].append(row);self.index+=1;ue.log("UEP_GRENADE_ACTIONS_CASE_PASSED "+name+" "+profile)
        if self.index==len(PLAN): self.quiet_ticks=0;self.enter("quiet")
    def quiet(self):
        require(self.healths()==self.health_before,"native action quiet interval changed actual Pawn Health")
        self.quiet_ticks+=1
        if self.quiet_ticks>=20: self.report["quiet_ticks"]=self.quiet_ticks;self.finish()
    def cleanup(self):
        if self.cleaned: return
        for actor in self.actors:
            if valid(actor) and not actor.call_function("IsActorBeingDestroyed"): actor.call_function("K2_DestroyActor")
        if hasattr(self,"cls"):
            binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==self.cls]
            self.report["production_classes_unchanged"]=all(binding["profiles"][name]["python_class"] is base for name,base in self.original_profile_classes.items())
        self.report.update(remaining_test_actors=len([actor for actor in self.actors if valid(actor) and not actor.call_function("IsActorBeingDestroyed")]),all_pawn_health_unchanged=self.healths()==self.health_before if hasattr(self,"health_before") else False);self.cleaned=True
    def tick(self,seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<180.,"native Actor actions total timeout")
            if self.phase=="ready": self.ready()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                if self.phase=="warm": self.warm()
                elif self.phase=="spawn": self.spawn()
                elif self.phase=="quiet": self.quiet()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        try: self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_GRENADE_ACTIONS_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try: self.report["status"]="passed";validate(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_ACTIONS_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeActionsResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
