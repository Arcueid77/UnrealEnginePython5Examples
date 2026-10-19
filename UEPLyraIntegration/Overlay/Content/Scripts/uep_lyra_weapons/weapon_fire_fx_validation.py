"""Actual Niagara parameter stores/array reads and original native latent node."""
import atexit
import copy
import struct
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod,EAttachLocation,ENCPoolMethod
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from . import weapon_fire_fx_mixin as policy
from .weapon_fire_fx_contract import PROFILES,CASES,require,validate

SYSTEMS=("/Game/Effects/Particles/Weapons/NS_WeaponFire_ShellEject.NS_WeaponFire_ShellEject",
         "/Game/Effects/Particles/Weapons/NS_WeaponFire.NS_WeaponFire",
         "/Game/Effects/Particles/Weapons/NS_WeaponFire_Tracer.NS_WeaponFire_Tracer")


def dead(value):return not valid(value) or value.call_function("IsActorBeingDestroyed")
def vec(value):return [float(value.x),float(value.y),float(value.z)]
def parameter(component,name,fmt):
    store=component.get_property("OverrideParameters");matches=[entry for entry in store.SortedParameterOffsets if str(entry.Name)==name]
    require(len(matches)==1,"native Niagara parameter absent: "+name)
    data=bytes(store.ParameterData);offset=int(matches[0].Offset);require(0<=offset and offset+struct.calcsize(fmt)<=len(data),"native Niagara override offset invalid")
    return list(struct.unpack_from(fmt,data,offset))


class Validation(Ready):
    healths=Health.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.original_classes={};self.cleanup_events=[];self.target=None
        self.report=dict(schema_version=1,status="running",error=None,cases=[],timer_cases=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,
            pixels_tested=False,audio_playback_tested=False,timer_properties_written=False,latent_callback_replayed=False,health_properties_written=False)
    def begin(self):
        bridge=policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld",self.world);self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Standalone","native fire FX standalone required")
        self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls)
        self.health_before=self.healths();self.original_view=self.controller.call_function("GetViewTarget")
        self.mesh=self.pawn.get_property("Mesh")
        point=self.pawn.get_actor_location();self.location=ue.FVector(point.x+200.,point.y,point.z+50.)
        self.camera=self.world.actor_spawn(ue.find_class("CameraActor"));self.actors.append(self.camera)
        require(self.camera.call_function("K2_TeleportTo",ue.FVector(self.location.x-250.,self.location.y,self.location.z+100.),ue.FRotator(0.,-20.,0.)),"native FX camera placement failed")
        self.controller.call_function("SetViewTargetWithBlend",self.camera,0.,0,0.,False)
        self.warm=self.world.actor_spawn(ue.find_class("Actor"),self.location);self.actors.append(self.warm)
        root=self.warm.add_actor_root_component(ue.find_class("SceneComponent"),"UEPWeaponFXWarm")
        self.systems=[ue.load_object(ue.find_class("NiagaraSystem"),path) for path in SYSTEMS]
        self.warm_components=[policy.lib("NiagaraFunctionLibrary").call_function("SpawnSystemAttached",SystemTemplate=system,AttachToComponent=root,
            AttachPointName="None",Location=ue.FVector(),Rotation=ue.FRotator(),LocationType=EAttachLocation.KeepRelativeOffset,
            bAutoDestroy=False,bAutoActivate=True,PoolingMethod=getattr(ENCPoolMethod,"None"),bPreCullCheck=True) for system in self.systems]
        require(all(valid(c) for c in self.warm_components),"native Niagara prewarm spawn failed")
        binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cls];self.original_classes={name:row["python_class"] for name,row in binding["profiles"].items()};owner=self
        for name,base in self.original_classes.items():
            def around(handler,profile):
                def invoke(actor):
                    if actor==owner.target:owner.cleanup_events.append(dict(profile=profile,time=owner.game_time()))
                    return handler(actor)
                invoke.override=policy.AFTER;return invoke
            ue.register_mixin_profile(self.cls,name,type("ObservedWeaponFXDelay"+name,(),dict(Fire=base.Fire,AfterDelay=around(base.AfterDelay,name))))
        self.warm_ticks=0;self.enter("warm")
    def spawn(self,profile,enabled=True):
        transform=ue.FTransform(self.location,ue.FRotator(),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.OverrideRootScale
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,self.cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,None,scale)
        actor.set_property("Skeletal Mesh Component",self.mesh)
        for (flag,_,system,_,_),asset in zip(policy.STAGES,self.systems):actor.set_property(flag,enabled);actor.set_property(system,asset)
        actor.set_property("Shell Eject Mesh",ue.load_object(ue.find_class("StaticMesh"),"/Game/Effects/Meshes/BulletShells/SM_rifleshell.SM_rifleshell"))
        point=self.mesh.call_function("GetSocketLocation","Muzzle");actor.set_property("ImpactPositions",[ue.FVector(point.x+1000.,point.y,point.z)])
        self.statics.call_function("FinishSpawningActor",actor,transform,scale);ue.set_mixin_profile(actor,profile);self.actors.append(actor);return actor
    def visual_trials(self):
        for profile in PROFILES:
            actor=self.spawn(profile);self.target=actor
            for name in CASES:
                old=[actor.get_property(field) for _,field,_,_,_ in policy.STAGES]
                if name=="disabled":
                    for flag,_,_,_,_ in policy.STAGES:actor.set_property(flag,False)
                elif name=="replace-inactive":
                    for flag,_,_,_,_ in policy.STAGES:actor.set_property(flag,True)
                    inactive=actor.add_actor_component(ue.find_class("NiagaraComponent"),"UEPInactiveCache")
                    require(not inactive.call_function("IsActive"),"native empty Niagara fixture unexpectedly active")
                    actor.set_property("NS_MuzzleFlash",inactive);old[1]=inactive
                before=dict(policy.evidence(actor));actor.call_function("Fire");after=policy.evidence(actor)
                components=[actor.get_property(field) for _,field,_,_,_ in policy.STAGES]
                rows=[]
                for component in components:
                    require(valid(component),"original native system returned invalid component")
                    rotation=component.call_function("K2_GetComponentRotation")
                    rows.append(dict(valid=True,trigger_parameter=bool(parameter(component,"User.Trigger","<i")[0]),
                        relative_rotation=[float(component.get_property("RelativeRotation").roll),float(component.get_property("RelativeRotation").pitch),float(component.get_property("RelativeRotation").yaw)],
                        attached_to_root=component.call_function("GetAttachParent")==actor.get_property("DefaultSceneRoot")))
                impacts=[vec(v) for v in actor.get_property("ImpactPositions")]
                muzzle=self.mesh.call_function("GetSocketLocation","Muzzle");destination=actor.get_property("ImpactPositions")[0]
                expected=policy.lib("KismetMathLibrary").call_function("Normal",policy.lib("KismetMathLibrary").call_function("Subtract_VectorVector",destination,muzzle),.0001)
                array=policy.lib("NiagaraDataInterfaceArrayFunctionLibrary").call_function("GetNiagaraArrayVector",components[2],"User.ImpactPositions")
                self.report["cases"].append(dict(name=name,profile=profile,components=rows,triggers=[bool(actor.get_property(trigger)) for _,_,_,trigger,_ in policy.STAGES],
                    same_cached=[a==b for a,b in zip(old,components)],direction_parameter=parameter(components[1],"User.Direction","<3f"),expected_direction=vec(expected),tracer_array=[vec(v) for v in array],impacts=impacts,
                    actual_selected_fire_dispatch=after["python_calls" if profile=="Python" else "fallback_calls"]-before["python_calls" if profile=="Python" else "fallback_calls"]==1))
            actor.call_function("K2_DestroyActor")
        self.index=0;self.start_timer()
    def start_timer(self):
        self.profile=PROFILES[self.index];self.target=self.spawn(self.profile,False);self.cleanup_events=[]
        self.timer_start=self.game_time();self.target.call_function("Fire");self.retriggered=False;self.survived=False;self.enter("timer")
    def timer(self):
        elapsed=self.game_time()-self.timer_start
        if not self.retriggered and elapsed>=1.:
            require(not dead(self.target),"FX died before original delay");self.target.call_function("Fire");self.retriggered=True
        if 3.1<=elapsed<3.4:require(not dead(self.target),"retriggerable delay did not reset");self.survived=True
        if not dead(self.target):require(elapsed<5.5,"native retriggered cleanup failed to destroy empty FX");return
        self.timer_row=dict(profile=self.profile,native_retrigger_observed=self.retriggered,survived_original_deadline=getattr(self,"survived",False),destroyed_after_retrigger=True,destroy_elapsed=elapsed)
        self.target=self.spawn(self.profile,False);self.cleanup_events=[];self.hold_component=self.target.add_actor_component(ue.find_class("NiagaraComponent"),"UEPValidInactiveHold")
        require(not self.hold_component.call_function("IsActive"),"native hold component is active");self.target.set_property("NS_ShellEject",self.hold_component)
        self.hold_start=self.game_time();self.target.call_function("Fire");self.hold_removed=False;self.enter("hold")
    def hold(self):
        elapsed=self.game_time()-self.hold_start
        if not self.hold_removed and self.cleanup_events:
            require(not dead(self.target) and valid(self.hold_component) and not self.hold_component.call_function("IsActive"),"valid inactive component did not keep FX alive")
            self.timer_row.update(valid_inactive_kept_actor_alive=True,native_repeat_cleanup_observed=True)
            self.hold_component.call_function("K2_DestroyComponent",self.target);self.hold_removed=True
        if not dead(self.target):require(elapsed<7.5,"native repeated cleanup did not finish");return
        self.timer_row["destroyed_after_component_removal"]=True;self.report["timer_cases"].append(self.timer_row);self.index+=1
        if self.index==len(PROFILES):self.finish()
        else:self.start_timer()
    def cleanup(self):
        self.target=None
        if hasattr(self,"original_view"):self.controller.call_function("SetViewTargetWithBlend",self.original_view,0.,0,0.,False)
        for actor in self.actors:
            if not dead(actor):actor.call_function("K2_DestroyActor")
        if self.original_classes:
            for name,base in self.original_classes.items():ue.register_mixin_profile(self.cls,name,base)
            binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cls]
            self.report["production_classes_restored"]=all(binding["profiles"][name]["python_class"] is base for name,base in self.original_classes.items())
        self.report["all_test_actors_destroyed"]=all(dead(actor) for actor in self.actors)
        self.report["original_pawn_health_unchanged"]=hasattr(self,"health_before") and self.healths()==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,"native fire FX total timeout")
            if self.phase=="ready":self.ready()
            elif self.phase=="warm":
                require(time.monotonic()-self.phase_started<20.,"native system readiness timeout")
                self.warm_ticks=self.warm_ticks+1 if all(c.call_function("IsActive") for c in self.warm_components) else 0
                if self.warm_ticks>=3:self.report["native_warmup_ready"]=True;self.warm.call_function("K2_DestroyActor");self.visual_trials()
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
        (ue.log_error if error else ue.log)("UEP_WEAPON_FIRE_FX_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_FIRE_FX_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPWeaponFireFXResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
