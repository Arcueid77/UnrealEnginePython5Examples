"""Real BP BeginPlay schedules native 0.16s timer; never replay its callback."""
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
from . import grenade_cleanup_mixin as policy
from .grenade_cleanup_contract import CLASS,PLAN,require,validate


def path(obj): return obj.get_path_name() if valid(obj) else None
def ignored(component): return sorted(path(value) for value in component.call_function("CopyArrayOfMoveIgnoreActors") if valid(value))


class Validation(Ready):
    healths=Activation.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.target=None;self.actors=[];self.events=[];self.max_frame=0.;self.installed=False;self.cleaned=False
        self.report=dict(schema_version=1,status="running",error=None,cases=[],observation_errors=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,
            physical_input_tested=False,cleanup_callback_replayed=False,timer_state_written=False,health_properties_written=False,raw_velocity_written=False,
            quantitative_movement_parity_tested=False,fuse_detonate_damage_business_migrated=False,original_native_timer_used=True,test_grenade_collision_disabled=True)
    def state(self,actor):
        instigator=actor.get_property("Instigator");character=valid(instigator) and instigator.is_a(ue.find_class("Character"))
        return dict(mesh_ignores=ignored(actor.get_property("Mesh")),capsule_ignores=ignored(instigator.get_property("CapsuleComponent")) if character else None,
            rotation_follows_velocity=bool(actor.get_property("ProjectileMovement").get_property("bRotationFollowsVelocity")))
    def begin(self):
        bridge=ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world)
        self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode);require(self.report["native_mode"]=="Standalone","native cleanup standalone world required")
        self.cls=ue.load_class(CLASS);ue.register_declared_mixin(self.cls);self.original_capsule_ignores=ignored(self.pawn.get_property("CapsuleComponent"));self.health_before=self.healths()
        self.other=self.world.actor_spawn(ue.find_class("SpectatorPawn"),ue.FVector(200000.,200000.,2000.));self.actors.append(self.other)
        require(valid(self.other) and not self.other.is_a(ue.find_class("Character")),"actual non-Character Pawn source missing")
        self.other.call_function("SetActorEnableCollision",False);owner=self
        for name,base in (("Python",policy.LyraGrenadeCleanupPythonProfile),("BlueprintFallback",policy.LyraGrenadeCleanupBlueprintFallbackProfile)):
            def around(handler,profile):
                def invoke(actor):
                    watched=actor==owner.target;row=None
                    if watched:
                        try: row=dict(profile=profile,native_timer_callback=True,elapsed=owner.game_time()-owner.spawn_game_time,before=owner.state(actor))
                        except Exception: owner.report["observation_errors"].append(traceback.format_exc())
                    handler(actor)
                    if row is not None:
                        try: row.update(after=owner.state(actor),stats=copy.deepcopy(policy.evidence(actor)));owner.events.append(row)
                        except Exception: owner.report["observation_errors"].append(traceback.format_exc())
                return invoke
            ue.register_mixin_profile(self.cls,name,type("ObservedGrenadeCleanup"+name,(),dict(SetupVFX=base.SetupVFX,PostLaunchCleanup=around(base.PostLaunchCleanup,name))))
        self.installed=True;self.enter("spawn")
    def spawn(self):
        name,profile=PLAN[self.index];instigator=self.pawn if name=="character" else self.other if name=="non-character-pawn" else None
        point=self.pawn.get_actor_location();transform=ue.FTransform(ue.FVector(point.x+1000.,point.y,point.z+1000.),ue.FRotator(),ue.FVector(1.,1.,1.))
        scale=ESpawnActorScaleMethod.OverrideRootScale
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,self.cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,None,scale)
        require(valid(actor),"native deferred cleanup Grenade missing");self.actors.append(actor);actor.set_property("Instigator",instigator)
        ue.set_mixin_profile(actor,profile);self.target=actor;self.events=[];self.max_frame=0.;self.spawn_game_time=self.game_time()
        actor.call_function("SetActorEnableCollision",False)
        self.statics.call_function("FinishSpawningActor",actor,transform,scale)
        require(actor.call_function("GetActorEnableCollision") is False,"test Grenade collision was not actually disabled")
        self.row=dict(name=name,profile=profile,actor=path(actor),**{"class":path(actor.get_class())},instigator=path(instigator),
            instigator_is_character=valid(instigator) and instigator.is_a(ue.find_class("Character")),initial=self.state(actor))
        require(not self.events,"original cleanup timer unexpectedly fired synchronously during Spawn")
        self.enter("timer")
    def timer(self):
        require(valid(self.target) and not self.target.call_function("IsActorBeingDestroyed"),"native Grenade did not survive to original cleanup timer")
        require(time.monotonic()-self.phase_started<1.5,"native one-shot cleanup timer did not fire before unmodified2s fuse")
        require(self.healths()==self.health_before,"native cleanup fixture changed Pawn Health")
        if not self.events: return
        require(len(self.events)==1,"native cleanup callback duplicated")
        self.row.update(event=copy.deepcopy(self.events[0]),native_grenade_alive_until_cleanup=True);self.quiet_ticks=0;self.enter("quiet")
    def quiet(self):
        require(valid(self.target) and not self.target.call_function("IsActorBeingDestroyed"),"native Actor died before cleanup quiet interval")
        require(self.events==[self.row["event"]] and self.healths()==self.health_before,"late cleanup callback or damage")
        self.quiet_ticks+=1
        if self.quiet_ticks<20: return
        self.row.update(quiet_ticks=self.quiet_ticks,max_observed_frame=self.max_frame,actual_timer_callback_count=len(self.events))
        actor=self.target;actor.call_function("K2_DestroyActor");self.row["actor_destroyed"]=not valid(actor) or bool(actor.call_function("IsActorBeingDestroyed"))
        self.report["cases"].append(copy.deepcopy(self.row));self.target=None;self.index+=1
        ue.log("UEP_GRENADE_CLEANUP_CASE_PASSED "+self.row["name"]+" "+self.row["profile"])
        if self.index==len(PLAN): self.finish()
        else: self.enter("spawn")
    def cleanup(self):
        if self.cleaned: return
        self.target=None
        for actor in self.actors:
            if valid(actor) and not actor.call_function("IsActorBeingDestroyed"): actor.call_function("K2_DestroyActor")
        if self.installed:
            for name,base in (("Python",policy.LyraGrenadeCleanupPythonProfile),("BlueprintFallback",policy.LyraGrenadeCleanupBlueprintFallbackProfile)): ue.register_mixin_profile(self.cls,name,base)
            binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==self.cls]
            self.report["production_classes_restored"]=all(binding["profiles"][name]["python_class"] is base for name,base in (("Python",policy.LyraGrenadeCleanupPythonProfile),("BlueprintFallback",policy.LyraGrenadeCleanupBlueprintFallbackProfile)))
        self.report.update(remaining_test_actors=len([actor for actor in self.actors if valid(actor) and not actor.call_function("IsActorBeingDestroyed")]),
            all_pawn_health_unchanged=self.healths()==self.health_before if hasattr(self,"health_before") else False,
            source_capsule_ignores_restored=ignored(self.pawn.get_property("CapsuleComponent"))==self.original_capsule_ignores if hasattr(self,"original_capsule_ignores") else False)
        self.cleaned=True
    def tick(self,seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<180.,"native cleanup total timeout");self.max_frame=max(self.max_frame,float(seconds))
            if self.phase=="ready": self.ready()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                if self.phase=="spawn": self.spawn()
                elif self.phase=="timer": self.timer()
                elif self.phase=="quiet": self.quiet()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        if error: self.report["pending_events"]=copy.deepcopy(self.events);self.report["pending_case"]=getattr(self,"row",None)
        try: self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_GRENADE_CLEANUP_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try: self.report["status"]="passed";validate(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_CLEANUP_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeCleanupResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
