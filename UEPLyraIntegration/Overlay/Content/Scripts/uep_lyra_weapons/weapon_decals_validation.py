"""Actual native decal cache/typed-array reads and natural latent cleanup timing."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod,ENCPoolMethod
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from .weapon_fire_fx_validation import dead,vec,parameter
from . import weapon_decals_mixin as policy
from .weapon_decals_contract import PROFILES,CASES,SURFACES,require,validate

SYSTEM="/Game/Effects/Particles/Impacts/NS_ImpactDecals.NS_ImpactDecals"


def array_kind(component,name):
    store=component.get_property("OverrideParameters");matches=[entry for entry in store.SortedParameterOffsets if str(entry.Name)==name]
    require(len(matches)==1,"native decal position interface missing")
    return store.DataInterfaces[int(matches[0].Offset)].get_class().get_name()


class Validation(Ready):
    healths=Health.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.components=[];self.original_classes={};self.target=None;self.cleanup_events=[]
        self.report=dict(schema_version=1,status="running",error=None,cases=[],timer_cases=[],full_acceptance=False,network_acceptance=False,
            packaged_runtime=False,pixels_tested=False,audio_playback_tested=False,timer_properties_written=False,latent_callback_replayed=False,health_properties_written=False)
    def remember(self,component):
        if valid(component) and not any(component==value for value in self.components):self.components.append(component)
        return component
    def remove(self,component):
        if valid(component):component.call_function("K2_DestroyComponent",component)
        require(not valid(component),"fixture native component destruction failed")
    def begin(self):
        bridge=policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld",self.world);self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Standalone","native decal standalone required")
        self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);self.signature=ue.describe_function(self.cls,"fire")
        self.health_before=self.healths();self.original_view=self.controller.call_function("GetViewTarget")
        self.camera=self.world.actor_spawn(ue.find_class("CameraActor"));self.actors.append(self.camera)
        require(self.camera.call_function("K2_TeleportTo",ue.FVector(-250.,0.,100.),ue.FRotator(0.,-20.,0.)),"native decal camera placement failed")
        self.controller.call_function("SetViewTargetWithBlend",self.camera,0.,0,0.,False)
        self.system=ue.load_object(ue.find_class("NiagaraSystem"),SYSTEM)
        self.warm=self.remember(policy.lib("NiagaraFunctionLibrary").call_function("SpawnSystemAtLocation",WorldContextObject=self.world,
            SystemTemplate=self.system,Location=ue.FVector(),Rotation=ue.FRotator(),Scale=ue.FVector(1.,1.,1.),bAutoDestroy=False,bAutoActivate=True,
            PoolingMethod=getattr(ENCPoolMethod,"None"),bPreCullCheck=True))
        require(valid(self.warm),"native decal prewarm spawn failed")
        binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cls]
        self.original_classes={name:row["python_class"] for name,row in binding["profiles"].items()};owner=self
        for name,base in self.original_classes.items():
            def around(handler,profile):
                def invoke(actor):
                    if actor==owner.target:owner.cleanup_events.append(dict(profile=profile,time=owner.game_time()))
                    return handler(actor)
                invoke.override=policy.AFTER;return invoke
            ue.register_mixin_profile(self.cls,name,type("ObservedDecalDelay"+name,(),dict(Fire=base.Fire,AfterDelay=around(base.AfterDelay,name))))
        self.warm_ticks=0;self.enter("warm")
    def spawn(self,profile):
        transform=ue.FTransform(ue.FVector(200.,100.,50.),ue.FRotator(),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.OverrideRootScale
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,self.cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,None,scale)
        actor.set_property("Decal System",self.system);actor.set_property("Surface Types",[3,2,1,0])
        actor.set_property("ImpactPositions",[ue.FVector(1000.,0.,25.)]);actor.set_property("ImpactNormals",[ue.FVector(-1.,0.,0.)]);actor.set_property("Impact Surface Types",[0])
        self.statics.call_function("FinishSpawningActor",actor,transform,scale);ue.set_mixin_profile(actor,profile);self.actors.append(actor);return actor
    def visual_trials(self):
        arrays=policy.lib("NiagaraDataInterfaceArrayFunctionLibrary")
        for profile in PROFILES:
            actor=self.spawn(profile);self.target=actor
            for index,name in enumerate(CASES):
                old=actor.get_property("Decal")
                if name=="replace-inactive":
                    inactive=self.remember(actor.add_actor_component(ue.find_class("NiagaraComponent"),"UEPInactiveDecalCache"))
                    require(not inactive.call_function("IsActive"),"native empty decal fixture unexpectedly active")
                    actor.set_property("Decal",inactive);old=inactive
                points=[ue.FVector((4194500. if name=="grow" else 1000.)+i*10.,100.,25.) for i in range(len(SURFACES[index]))]
                normals=[ue.FVector(-1.,0.,0.) for _ in range(max(0,len(points)-1))]
                actor.set_property("ImpactPositions",points);actor.set_property("ImpactNormals",normals);actor.set_property("Impact Surface Types",list(SURFACES[index]))
                before=dict(policy.evidence(actor));actor.call_function("fire");after=policy.evidence(actor);component=self.remember(actor.get_property("Decal"))
                require(valid(component),"original decal native spawn returned invalid component")
                rotation=component.call_function("K2_GetComponentRotation")
                self.report["cases"].append(dict(name=name,profile=profile,component_valid=True,same_cached=component==old,
                    trigger=bool(actor.get_property("Impact Trigger")),trigger_parameter=bool(parameter(component,"User.Trigger","<i")[0]),
                    input_surfaces=list(SURFACES[index]),surface_types=list(actor.get_property("Surface Types")),
                    native_surfaces=list(arrays.call_function("GetNiagaraArrayInt32",component,"User.ImpactSurfaces")),
                    positions=[vec(v) for v in points],normals=[vec(v) for v in normals],
                    native_positions=[vec(v) for v in arrays.call_function("GetNiagaraArrayPosition",component,"User.ImpactPositions")],
                    native_normals=[vec(v) for v in arrays.call_function("GetNiagaraArrayVector",component,"User.ImpactNormals")],
                    position_array_kind=array_kind(component,"User.ImpactPositions"),native_hit_count=parameter(component,"User.NumberOfHits","<i")[0],
                    world_location=vec(component.call_function("K2_GetComponentLocation")),world_rotation=[float(rotation.roll),float(rotation.pitch),float(rotation.yaw)],
                    world_scale=vec(component.call_function("K2_GetComponentScale")),unattached=not valid(component.call_function("GetAttachParent")),native_auto_destroy=bool(component.get_property("bAutoDestroy")),
                    actual_selected_fire_dispatch=after["python_calls" if profile=="Python" else "fallback_calls"]-before["python_calls" if profile=="Python" else "fallback_calls"]==1))
            actor.call_function("K2_DestroyActor")
        for component in self.components:self.remove(component)
        self.index=0;self.start_timer()
    def fire_and_remove(self):
        self.target.call_function("fire");self.remove(self.remember(self.target.get_property("Decal")))
    def start_timer(self):
        self.profile=PROFILES[self.index];self.target=self.spawn(self.profile);self.cleanup_events=[]
        self.timer_start=self.game_time();self.fire_and_remove();self.retriggered=False;self.survived=False;self.enter("timer")
    def timer(self):
        elapsed=self.game_time()-self.timer_start
        if not self.retriggered and elapsed>=1.:
            require(not dead(self.target),"decal died before original delay");self.fire_and_remove();self.retriggered=True
        if 3.1<=elapsed<3.4:require(not dead(self.target),"decal native delay did not reset");self.survived=True
        if not dead(self.target):require(elapsed<5.5,"native decal retrigger cleanup failed");return
        require(len(self.cleanup_events)==1,"unexpected native decal empty cleanup count")
        self.timer_row=dict(profile=self.profile,native_retrigger_observed=self.retriggered,survived_original_deadline=self.survived,
            destroyed_after_retrigger=True,destroy_elapsed=elapsed,native_callback_elapsed=self.cleanup_events[0]["time"]-self.timer_start)
        self.target=self.spawn(self.profile);self.cleanup_events=[];self.target.call_function("fire");self.remove(self.remember(self.target.get_property("Decal")))
        self.hold_component=self.remember(self.target.add_actor_component(ue.find_class("NiagaraComponent"),"UEPValidInactiveDecalHold"))
        require(not self.hold_component.call_function("IsActive"),"native decal hold is active");self.target.set_property("Decal",self.hold_component)
        self.hold_start=self.game_time();self.hold_removed=False;self.enter("hold")
    def hold(self):
        elapsed=self.game_time()-self.hold_start
        if not self.hold_removed and self.cleanup_events:
            require(not dead(self.target) and valid(self.hold_component) and not self.hold_component.call_function("IsActive"),"valid inactive decal did not keep Actor alive")
            self.timer_row.update(valid_inactive_kept_actor_alive=True,native_repeat_cleanup_observed=True)
            self.remove(self.hold_component);self.hold_removed=True
        if not dead(self.target):require(elapsed<7.5,"native repeated decal cleanup failed");return
        self.timer_row.update(destroyed_after_component_removal=True,hold_callback_elapsed=[entry["time"]-self.hold_start for entry in self.cleanup_events])
        self.report["timer_cases"].append(self.timer_row);self.index+=1
        if self.index==len(PROFILES):self.finish()
        else:self.start_timer()
    def cleanup(self):
        self.target=None
        if hasattr(self,"original_view"):
            self.controller.call_function("SetViewTargetWithBlend",self.original_view,0.,0,0.,False)
            self.report["original_view_restored"]=self.controller.call_function("GetViewTarget")==self.original_view
        for component in self.components:self.remove(component)
        for actor in self.actors:
            if not dead(actor):actor.call_function("K2_DestroyActor")
        if self.original_classes:
            for name,base in self.original_classes.items():ue.register_mixin_profile(self.cls,name,base)
            binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cls]
            self.report["production_classes_restored"]=all(binding["profiles"][name]["python_class"] is base for name,base in self.original_classes.items())
            self.report["original_signature_restored"]=ue.describe_function(self.cls,"fire")==self.signature
        self.report["all_test_actors_destroyed"]=all(dead(actor) for actor in self.actors)
        self.report["all_test_components_destroyed"]=all(not valid(component) for component in self.components)
        self.report["original_pawn_health_unchanged"]=hasattr(self,"health_before") and self.healths()==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,"native decal total timeout")
            if self.phase=="ready":self.ready()
            elif self.phase=="warm":
                require(time.monotonic()-self.phase_started<20.,"native decal readiness timeout")
                self.warm_ticks=self.warm_ticks+1 if valid(self.warm) and self.warm.call_function("IsActive") else 0
                if self.warm_ticks>=3:self.report["native_warmup_ready"]=True;self.remove(self.warm);self.visual_trials()
            elif self.phase=="timer":self.timer()
            elif self.phase=="hold":self.hold()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_DECALS_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_DECALS_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPWeaponDecalsResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
