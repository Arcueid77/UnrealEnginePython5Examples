"""Original firing Cue orchestration; BurstEffects and audio backends stay native."""
import unreal_engine as ue
from unreal_engine.structs import GameplayCueParameters
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import macro_policies

WEAPONS=("Pistol","Rifle","Shotgun")
CLASSES={name:"/ShooterCore/Weapons/"+name+"/GCN_Weapon_"+name+"_Fire.GCN_Weapon_"+name+"_Fire_C" for name in WEAPONS}
STRENGTHS=dict(zip(WEAPONS,(.1,.15,.2)))
AUDIO="/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions_C"
RIFLE_SOUND="/Game/Audio/Sounds/Weapons/Rifle2/MSS_Weapons_Rifle2_Fire.MSS_Weapons_Rifle2_Fire"


def evidence(cue):
    row=getattr(cue,"_uep_weapon_fire_cue",None)
    if row is None:
        row={key:0 for key in ("python_calls","fallback_calls","invalid_target_original","send_weapon_fire","lookup_failed","weapon_fire","rifle_audio","sound_params","early_reflections","whiz_by")}
        row["last_orders"]=[];cue._uep_weapon_fire_cue=row
    return row


def weapon_for(target):
    return macro_policies.weapon_for(target)


def burst(cue,target,params,spawns):
    row=evidence(cue);row["python_calls"]+=1
    if not valid(target):
        row["invalid_target_original"]+=1;return cue.call_mixin_original("OnBurst",target,params,spawns)
    name=next(name for name,cls in CLASSES.items() if cue.get_class().get_path_name()==cls)
    audio=ue.load_class(AUDIO).get_cdo();order=[]
    audio.call_function("SendWeaponFire",target,STRENGTHS[name],cue);row["send_weapon_fire"]+=1;order.append("SendWeaponFire")
    weapon=weapon_for(target)
    if valid(weapon):
        fields=native_outputs("AbilitySystemBlueprintLibrary","BreakGameplayCueParameters",ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("BreakGameplayCueParameters",params))
        physical=fields["PhysicalMaterial"];surface=physical.get_property("SurfaceType") if valid(physical) else 0
        weapon.call_function("Fire",[fields["Location"]],[fields["Normal"]],[surface]);row["weapon_fire"]+=1;order.append("Weapon.Fire")
        if name=="Rifle":
            weapon.call_function("TriggerFireAudio",ue.load_object(ue.find_class("SoundBase"),RIFLE_SOUND),target);row["rifle_audio"]+=1;order.append("Weapon.TriggerFireAudio")
        audio.call_function("SetWeaponSoundParams",target,spawns,cue);row["sound_params"]+=1;order.append("SetWeaponSoundParams")
        audio.call_function("EarlyReflections",target,GameplayCueParameters() if name=="Rifle" else params,cue);row["early_reflections"]+=1;order.append("EarlyReflections")
        audio.call_function("WhizBy",target,params,cue);row["whiz_by"]+=1;order.append("WhizBy")
    else:row["lookup_failed"]+=1
    row["last_orders"]=(row["last_orders"]+[order])[-8:]


class LyraWeaponFireCuePythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):return burst(self,Target,Parameters,SpawnResults)


class LyraWeaponFireCueBlueprintFallbackProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):evidence(self)["fallback_calls"]+=1;return self.call_mixin_original("OnBurst",Target,Parameters,SpawnResults)
