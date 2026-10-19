"""Establish original native WhizBy component behavior on the offline renderer."""
import atexit
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,GameplayEffectContextHandle
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs

SOUND="/Game/Audio/MetaSounds/sfx_WhizBys_nl_meta.sfx_WhizBys_nl_meta"


def xyz(value):return [float(value.x),float(value.y),float(value.z)]


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.owned=[];self.audio=[];self.materials=[]
        self.report=dict(status="running",error=None,original_cases=[],full_acceptance=False,audible_playback_tested=False,preset_asset_saved=False,cpp_compile_executed=False)
    def components(self):return [obj for obj in self.world.all_objects() if valid(obj) and obj.is_a(ue.find_class("AudioComponent")) and obj.get_property("Sound")==self.sound]
    def begin(self):
        self.health_before=float(self.health.call_function("GetHealth"));self.sound=ue.load_object(ue.find_class("SoundBase"),SOUND)
        library=ue.load_class("/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions_C").get_cdo()
        self.report["native_attenuation_signature"]=ue.describe_function(ue.find_class("AudioComponent"),"BP_GetAttenuationSettingsToApply")
        self.fixture=self.world.actor_spawn(ue.find_class("Actor"));self.owned.append(self.fixture);self.fixture.add_actor_root_component(ue.find_class("SceneComponent"),"UEPWhizOrigin")
        cam=self.controller.get_property("PlayerCameraManager").call_function("GetCameraLocation")
        self.fixture.call_function("K2_SetActorLocation",NewLocation=ue.FVector(cam.x+1000.,cam.y+250.,cam.z),bSweep=False,bTeleport=False)
        self.report["origin_location"]=xyz(self.fixture.call_function("K2_GetActorLocation"))
        for actor_label,actor in (("foreign",self.fixture),("local",self.pawn),("null",None)):
            for surface in (0,1,4):
                material=ue.new_object(ue.find_class("PhysicalMaterial"));material.set_property("SurfaceType",surface);material.add_to_root();self.materials.append(material)
                params=ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("MakeGameplayCueParameters",NormalizedMagnitude=0.,RawMagnitude=0.,
                    EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),AggregatedSourceTags=GameplayTagContainer(),
                    AggregatedTargetTags=GameplayTagContainer(),Location=ue.FVector(cam.x-1000.,cam.y-250.,cam.z),Normal=ue.FVector(0.,0.,1.),
                    Instigator=None,EffectCauser=None,SourceObject=None,PhysicalMaterial=material,GameplayEffectLevel=1,AbilityLevel=1,
                    TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
                before={obj.get_path_name() for obj in self.components()};library.call_function("WhizBy",actor,params,self.world)
                created=[obj for obj in self.components() if obj.get_path_name() not in before];self.audio.extend(created);rows=[]
                for component in created:
                    attenuation=native_outputs("AudioComponent","BP_GetAttenuationSettingsToApply",component.call_function("BP_GetAttenuationSettingsToApply"))
                    rows.append(dict(sound=component.get_property("Sound").get_path_name(),location=xyz(component.call_function("K2_GetComponentLocation")),
                        playing=bool(component.call_function("IsPlaying")),auto_destroy=bool(component.get_property("bAutoDestroy")),
                        volume=float(component.get_property("VolumeMultiplier")),pitch=float(component.get_property("PitchMultiplier")),
                        parameters={str(p.ParamName):float(p.FloatParam) for p in component.get_property("InstanceParameters")},
                        attenuation_success=bool(attenuation["ReturnValue"]),stereo_spread=float(attenuation["OutAttenuationSettings"].StereoSpread)))
                self.report["original_cases"].append(dict(actor=actor_label,surface=surface,components=rows))
                for component in created:
                    component.call_function("Stop")
                    if valid(component):component.call_function("K2_DestroyComponent",component)
        self.finish()
    def cleanup(self):
        for component in self.audio:
            if valid(component):
                component.call_function("Stop")
                if valid(component):component.call_function("K2_DestroyComponent",component)
        for actor in self.owned:
            if valid(actor):actor.call_function("K2_DestroyActor")
        for material in self.materials:material.remove_from_root()
        self.report["owned_components_destroyed"]=all(not valid(component) for component in self.audio)
        self.report["owned_actors_destroyed"]=all(not valid(actor) for actor in self.owned)
        if hasattr(self,"health_before"):self.report["player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:self.ready();self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_AUDIO_WHIZ_PROBE_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            rows=self.report["original_cases"]
            valid_rows=len(rows)==9 and all(len(row["components"])==(1 if row["actor"]=="foreign" and row["surface"]!=1 else 0) for row in rows)
            if valid_rows and self.report.get("owned_components_destroyed") and self.report.get("owned_actors_destroyed"):self.report["status"]="passed"
            else:self.report.update(status="failed",error="Original offline audio component/branch/cleanup matrix incomplete")
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_AUDIO_WHIZ_SHUTDOWN_"+self.report["status"].upper())


def plain(value):
    if value is None or isinstance(value,(bool,int,float,str)):return value
    if hasattr(value,"get_path_name"):return value.get_path_name()
    if hasattr(value,"x"):return xyz(value)
    if hasattr(value,"as_dict"):return {key:plain(item) for key,item in value.as_dict().items()}
    if isinstance(value,dict):return {str(key):plain(item) for key,item in value.items()}
    if isinstance(value,(tuple,list)):return [plain(item) for item in value]
    raise RuntimeError("unsupported native audio state type: "+type(value).__name__)


class Differential(Validation):
    def __init__(self,result):
        super().__init__(result)
        self.report.update(whiz_pairs=[],math_regression=[],network_acceptance=False,static_functions_registered_as_mixins=False,
            no_sound=any(v.lower()=="-nosound" for v in sys.argv))
    def cue(self,material,impact):
        return ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("MakeGameplayCueParameters",NormalizedMagnitude=0.,RawMagnitude=0.,
            EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),AggregatedSourceTags=GameplayTagContainer(),
            AggregatedTargetTags=GameplayTagContainer(),Location=impact,Normal=ue.FVector(0.,0.,1.),Instigator=None,EffectCauser=None,SourceObject=None,
            PhysicalMaterial=material,GameplayEffectLevel=1,AbilityLevel=1,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
    def snapshot(self,component):
        attenuation=native_outputs("AudioComponent","BP_GetAttenuationSettingsToApply",component.call_function("BP_GetAttenuationSettingsToApply"))
        return dict(sound=component.get_property("Sound").get_path_name(),location=xyz(component.call_function("K2_GetComponentLocation")),
            playing=bool(component.call_function("IsPlaying")),auto_destroy=bool(component.get_property("bAutoDestroy")),
            volume=float(component.get_property("VolumeMultiplier")),pitch=float(component.get_property("PitchMultiplier")),
            parameters={str(p.ParamName):float(p.FloatParam) for p in component.get_property("InstanceParameters")},
            attenuation_success=bool(attenuation["ReturnValue"]),attenuation=plain(attenuation["OutAttenuationSettings"]))
    def invoke(self,actor,params,caller):
        before={obj.get_path_name() for obj in self.components()}
        (self.caller if caller else self.library).call_function("Call"+self.policy.METHOD if caller else "WhizBy",actor,params,self.world)
        created=[obj for obj in self.components() if obj.get_path_name() not in before];self.audio.extend(created)
        try:return [self.snapshot(component) for component in created]
        finally:
            for component in created:
                if valid(component):component.call_function("Stop")
                if valid(component):component.call_function("K2_DestroyComponent",component)
    def begin(self):
        from . import weapon_audio_whiz_mixin as policy,weapon_audio_math_mixin as math_policy
        from .weapon_audio_whiz_contract import PLAN,TRAJECTORIES,PROFILES
        self.policy=policy;self.health_before=float(self.health.call_function("GetHealth"));self.sound=ue.load_object(ue.find_class("SoundBase"),SOUND)
        cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(cls);self.router=cls.get_cdo();self.router_original=str(ue.get_mixin_profile(self.router))
        self.library_cls=ue.load_class(policy.LIBRARY);self.library=self.library_cls.get_cdo();self.caller=ue.load_class("/Game/UEPValidation/BP_WeaponAudioWhizCaller.BP_WeaponAudioWhizCaller_C").get_cdo()
        self.signatures={name:ue.describe_function(self.library_cls,name) for name in ("WhizBy","EarlyReflections","SendWeaponFire","SetWeaponSoundParams","DebugPrintTap","Calculate Tap Properties","GetSideReflectionAngles","Calculate Whiz By")}
        math_cls=ue.load_class(math_policy.CLASS);ue.register_declared_mixin(math_cls);math_router=math_cls.get_cdo()
        fixture=self.world.actor_spawn(ue.find_class("Actor"));self.owned.append(fixture);fixture.add_actor_root_component(ue.find_class("SceneComponent"),"UEPWhizOrigin")
        listener=self.controller.get_property("PlayerCameraManager").call_function("GetCameraLocation");materials={None:None}
        for surface in (0,1,4):
            material=ue.new_object(ue.find_class("PhysicalMaterial"));material.set_property("SurfaceType",surface);material.add_to_root();self.materials.append(material);materials[surface]=material
        for index,(label,surface,trajectory) in enumerate(PLAN):
            origin_offset,impact_offset=TRAJECTORIES[trajectory];origin=ue.FVector(*[a+b for a,b in zip(xyz(listener),origin_offset)]);impact=ue.FVector(*[a+b for a,b in zip(xyz(listener),impact_offset)])
            fixture.call_function("K2_SetActorLocation",NewLocation=origin,bSweep=False,bTeleport=True);actor=fixture if label=="foreign" else self.pawn if label=="local" else None;params=self.cue(materials[surface],impact)
            counts=[];values=[];before_math=dict(math_policy.evidence(math_router))
            for profile in PROFILES:
                ue.set_mixin_profile(self.router,profile);before=dict(policy.evidence(self.router));values.extend(self.invoke(actor,params,caller) for caller in (False,True))
                key="fallback_calls" if profile=="BlueprintFallback" else "python_calls";counts.append(policy.evidence(self.router)[key]-before[key])
            after_math=math_policy.evidence(math_router);math_count=sum(after_math[key]-before_math[key] for key in ("whiz_python","whiz_fallback"))
            self.report["whiz_pairs"].append(dict(index=index,observations=values,fallback_dispatches=counts[0],python_dispatches=counts[1],math_dispatches=math_count,listener=xyz(listener),origin=xyz(origin),impact=xyz(impact)))
        self.regressions();self.report["original_static_signatures_preserved"]=all(ue.describe_function(self.library_cls,name)==value for name,value in self.signatures.items());self.finish()
    def regressions(self):
        from . import weapon_audio_math_mixin as math_policy,weapon_audio_dispatch_mixin as dispatch
        from .weapon_audio_math_contract import SIDE_PLAN,WHIZ_PLAN
        from .weapon_audio_math_validation import model
        from unreal_engine.structs import GameplayCueNotify_SpawnResult,TapDelayInfo
        math_router=ue.load_class(math_policy.CLASS).get_cdo();math_original=str(ue.get_mixin_profile(math_router));math_caller=ue.load_class("/Game/UEPValidation/BP_WeaponAudioMathCaller.BP_WeaponAudioMathCaller_C").get_cdo()
        try:
            for method,plan,call in (("GetSideReflectionAngles",SIDE_PLAN,"CallSides"),("Calculate Whiz By",WHIZ_PLAN,"CallWhiz")):
                for args in (plan[0],plan[len(plan)//3],plan[len(plan)//2],plan[-1]):
                    args=[ue.FVector(*v) if isinstance(v,tuple) else v for v in args];values=[]
                    for profile in ("BlueprintFallback","Python"):
                        ue.set_mixin_profile(math_router,profile)
                        for target,name in ((self.library,method),(math_caller,call)):values.append(model(target.call_function(name,*args,self.world)))
                    self.report["math_regression"].append(values.count(values[0])==4)
        finally:ue.set_mixin_profile(math_router,math_original)
        cls=ue.load_class(dispatch.CLASS);ue.register_declared_mixin(cls);router=cls.get_cdo();original=str(ue.get_mixin_profile(router));caller=ue.load_class("/Game/UEPValidation/BP_WeaponAudioDispatchCaller.BP_WeaponAudioDispatchCaller_C").get_cdo()
        preset=dispatch.tap_preset();ids,=preset.call_function("GetTapIds");before={int(i):plain(preset.call_function("GetTap",i)[0]) for i in ids};tap,=preset.call_function("AddTap");values=[]
        try:
            for profile in ("BlueprintFallback","Python"):
                ue.set_mixin_profile(router,profile)
                for target,is_caller in ((self.library,False),(caller,True)):
                    preset.call_function("SetTap",tap,TapDelayInfo(DelayLength=17.25,PanInDegrees=-53.5,Gain=-3.))
                    for name,args in (("SendWeaponFire",[None,.25]),("SetWeaponSoundParams",[None,GameplayCueNotify_SpawnResult()]),("DebugPrintTap",["UEPWhizRegression",17.25,-60.,-53.5]),("Calculate Tap Properties",["Unused",None,ue.FVector(),tap,999.,0.,False,ue.FVector()])):
                        target.call_function("Call"+dispatch.METHODS[name] if is_caller else name,*args,self.world)
                    values.append(plain(preset.call_function("GetTap",tap)[0]))
        finally:
            preset.call_function("RemoveTap",tap);ue.set_mixin_profile(router,original)
        ids,=preset.call_function("GetTapIds");after={int(i):plain(preset.call_function("GetTap",i)[0]) for i in ids}
        self.report["dispatch_regression_passed"]=len(values)==4 and values.count(values[0])==4 and values[0]["Gain"]==-60. and before==after and str(ue.get_mixin_profile(router))==original
    def cleanup(self):
        if hasattr(self,"router_original"):
            ue.set_mixin_profile(self.router,self.router_original);self.report["router_profile_restored"]=str(ue.get_mixin_profile(self.router))==self.router_original
        super().cleanup()
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_AUDIO_WHIZ_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:
                from .weapon_audio_whiz_contract import validate
                self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_AUDIO_WHIZ_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPWeaponAudioWhizResult=")),None)
if result:
    validation=(Validation if "-UEPWeaponAudioWhizOriginalProbe" in sys.argv else Differential)(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
