"""Original WhizBy eligibility, native spawn/attenuation/parameters/play order."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs

CLASS="/Game/UEPMixins/BP_WeaponAudioWhizRouter.BP_WeaponAudioWhizRouter_C"
METHOD="UEPAudioWhizSchedule"
SOUND="/Game/Audio/MetaSounds/sfx_WhizBys_nl_meta.sfx_WhizBys_nl_meta"
LIBRARY="/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions_C"


def lib(name):return ue.find_class(name).get_cdo()
def evidence(router):
    value=getattr(router,"_uep_audio_whiz",None)
    if value is None:value=dict(python_calls=0,fallback_calls=0,native_spawn_requests=0,valid_components=0);router._uep_audio_whiz=value
    return value


def schedule(router,actor,params,world):
    statics=lib("GameplayStatics");platform=statics.call_function("GetPlatformName");string=lib("KismetStringLibrary")
    if not any(string.call_function("EqualEqual_StriStri",platform,name) for name in ("Windows","Linux","Mac")):return False
    pawn=statics.call_function("GetPlayerPawn",world,0)
    payload=native_outputs("AbilitySystemBlueprintLibrary","BreakGameplayCueParameters",lib("AbilitySystemBlueprintLibrary").call_function("BreakGameplayCueParameters",params))
    material=payload["PhysicalMaterial"];surface=int(material.get_property("SurfaceType")) if valid(material) else 0
    if not valid(actor) or not valid(pawn) or surface==1 or actor==pawn:return False
    camera=statics.call_function("GetPlayerCameraManager",pawn,0)
    if not valid(camera):return True
    location,spread,from_right,distance=ue.load_class(LIBRARY).get_cdo().call_function("Calculate Whiz By",camera.call_function("GetCameraLocation"),actor.call_function("K2_GetActorLocation"),1000.,payload["Location"],actor)
    evidence(router)["native_spawn_requests"]+=1
    component=statics.call_function("SpawnSoundAtLocation",WorldContextObject=world,Sound=ue.load_object(ue.find_class("SoundBase"),SOUND),Location=location,
        Rotation=ue.FRotator(),VolumeMultiplier=1.,PitchMultiplier=1.,StartTime=0.,AttenuationSettings=None,ConcurrencySettings=None,bAutoDestroy=True)
    if not valid(component):return False
    evidence(router)["valid_components"]+=1
    attenuation=native_outputs("AudioComponent","BP_GetAttenuationSettingsToApply",component.call_function("BP_GetAttenuationSettingsToApply"))["OutAttenuationSettings"]
    # The Blueprint ignores the getter's success bool and changes only spread.
    attenuation.StereoSpread=spread;component.call_function("AdjustAttenuation",attenuation)
    component.call_function("SetFloatParameter","OnsetDelay",distance*.000010)
    component.call_function("SetFloatParameter","SwapLR",1. if from_right else 0.)
    component.call_function("Play",0.)
    return False


class LyraWeaponAudioWhizPythonProfile:
    def Whiz(self,Actor,Parameters,WorldContext):
        evidence(self)["python_calls"]+=1;return dict(UseOriginal=bool(schedule(self,Actor,Parameters,WorldContext)))
    Whiz.override=METHOD;Whiz.uep_named_outputs=True


class LyraWeaponAudioWhizBlueprintFallbackProfile:
    def Whiz(self,Actor,Parameters,WorldContext):evidence(self)["fallback_calls"]+=1;return dict(UseOriginal=True)
    Whiz.override=METHOD;Whiz.uep_named_outputs=True
