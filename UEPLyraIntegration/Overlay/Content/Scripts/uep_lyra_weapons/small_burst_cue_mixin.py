"""Four small Burst Cue policies; native parents still create all effects."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .hero_burst_cue_mixin import lib

CLASSES={
    'pickup':'/ShooterCore/GameplayCues/GCN_InteractPickUp.GCN_InteractPickUp_C',
    'melee':'/ShooterCore/GameplayCues/GCN_Weapon_Melee.GCN_Weapon_Melee_C',
    'heal':'/Game/GameplayCueNotifies/GCN_Character_Heal.GCN_Character_Heal_C',
    'grenade':'/ShooterCore/Weapons/Grenade/GCN_Grenade_Detonate.GCN_Grenade_Detonate_C'}
SPAWNER='/ShooterCore/Blueprint/B_WeaponSpawner.B_WeaponSpawner_C'
GRENADE='/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C'
AUDIO='/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions_C'


def evidence(cue):
    if not hasattr(cue,'_uep_small_burst'):cue._uep_small_burst=dict(python_burst=0,fallback_burst=0,diagnostic_fallbacks=0,color_writes=0,invalid_fx_prints=0,typed_noops=0,weapon_fire_calls=0,audio_play_calls=0)
    return cue._uep_small_burst


def original(cue,target,params,results):
    evidence(cue)['diagnostic_fallbacks']+=1;return cue.call_mixin_original('OnBurst',target,params,results)


def pickup(cue,target,params,results):
    counts=evidence(cue);counts['python_burst']+=1;effects=list(results.FxSystemComponents)
    if not effects:return original(cue,target,params,results)
    effect=effects[0]
    if not valid(effect) or not effect.is_a(ue.find_class('NiagaraComponent')):
        lib('KismetSystemLibrary').call_function('PrintString',WorldContextObject=cue,InString='NOT VALID',bPrintToScreen=True,bPrintToLog=True,TextColor=ue.FLinearColor(0.,.66,1.,1.),Duration=2.,Key='None');counts['invalid_fx_prints']+=1;return
    instigator=native_outputs('AbilitySystemBlueprintLibrary','BreakGameplayCueParameters',lib('AbilitySystemBlueprintLibrary').call_function('BreakGameplayCueParameters',params))['Instigator']
    if not valid(instigator) or not instigator.is_a(ue.load_class(SPAWNER)):return original(cue,target,params,results)
    effect.call_function('SetVariableLinearColor','GunPad_Color',instigator.get_property('LightColor'));counts['color_writes']+=1


def grenade(cue,target,params,results):
    counts=evidence(cue);counts['python_burst']+=1
    if not valid(target) or not target.is_a(ue.load_class(GRENADE)):counts['typed_noops']+=1;return
    effects=list(results.FxSystemComponents)
    if not effects:return original(cue,target,params,results)
    effect=effects[0]
    if not valid(effect) or not effect.is_a(ue.find_class('NiagaraComponent')):counts['typed_noops']+=1;return
    effect.call_function('SetVariableLinearColor','Team_Color',target.get_property('Team Color'));counts['color_writes']+=1


def melee(cue,target):
    counts=evidence(cue);counts['python_burst']+=1
    ue.load_class(AUDIO).get_cdo().call_function('SendWeaponFire',Player=target,Strength=.2,__WorldContext=cue);counts['weapon_fire_calls']+=1


def heal(cue,target,params,results):
    counts=evidence(cue);counts['python_burst']+=1;audio=cue.get_property('Audio_OnHeal')
    if not valid(audio):return original(cue,target,params,results)
    audio.call_function('Play',0.);counts['audio_play_calls']+=1


class LyraSmallBurstPickupPythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):return pickup(self,Target,Parameters,SpawnResults)


class LyraSmallBurstGrenadePythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):return grenade(self,Target,Parameters,SpawnResults)


class LyraSmallBurstMeleePythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):melee(self,Target)


class LyraSmallBurstHealPythonProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):return heal(self,Target,Parameters,SpawnResults)


class LyraSmallBurstBlueprintFallbackProfile:
    def OnBurst(self,Target,Parameters,SpawnResults):evidence(self)['fallback_burst']+=1;return self.call_mixin_original('OnBurst',Target,Parameters,SpawnResults)


LyraSmallBurstPickupBlueprintFallbackProfile=LyraSmallBurstBlueprintFallbackProfile
LyraSmallBurstMeleeBlueprintFallbackProfile=LyraSmallBurstBlueprintFallbackProfile
LyraSmallBurstHealBlueprintFallbackProfile=LyraSmallBurstBlueprintFallbackProfile
LyraSmallBurstGrenadeBlueprintFallbackProfile=LyraSmallBurstBlueprintFallbackProfile
