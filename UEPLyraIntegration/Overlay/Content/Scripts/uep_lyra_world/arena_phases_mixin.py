"""Arena phase policy; GAS phase authority, native Delay and travel stay native."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayCueParameters
CLASSES={k:'/TopDownArena/Game/Modes/'+v+'.'+v+'_C' for k,v in (('warmup','Phase_Warmup'),('playing','Phase_Playing'),('postgame','Phase_PostGame'))}
EFFECT='/TopDownArena/Game/Modes/GE_Warmup.GE_Warmup_C'
CUE='GameplayCue.TopDownArenaGame.UserMessage.GetReady'
WARM_WAIT='UEPArenaWarmupNativeWait'
PLAY='UEPArenaNativeStartPlaying'
WARM_AFTER='UEPArenaWarmupAfterNativeWait'
POST_WAIT='UEPArenaPostGameNativeWait'
POST_AFTER='UEPArenaPostGameAfterNativeWait'
def lib(name):return ue.find_class(name).get_cdo()
def subsystem(a,name):return lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',a,ue.find_class(name))
def params(raw=0.):return GameplayCueParameters(NormalizedMagnitude=0.,RawMagnitude=float(raw),GameplayEffectLevel=1,AbilityLevel=1)
def display(a,value):lib('KismetSystemLibrary').call_function('PrintString',a,value,True,True,ue.FLinearColor(0.,.66,1.,1.),2.,'None')
def evidence(a):
    value=getattr(a,'_uep_arena_phases',None)
    if value is None:
        value={p+k:0 for p in ('python_','fallback_') for k in ('activate','end','clear','cue','after')};value.update(skip_noops=0,effects_applied=0,effects_removed=0,cues_added=0,cues_removed=0,waits=0,starts=0,travels=0);a._uep_arena_phases=value
    return value
class LyraArenaWarmupPythonProfile:
    def K2_ActivateAbility(self):
        value=evidence(self);value['python_activate']+=1
        # Original true branch is unconnected. Do not invent a phase transition.
        if lib('LyraDevelopmentStatics').call_function('ShouldSkipDirectlyToGameplay'):value['skip_noops']+=1;return
        subsystem(self,'LyraGlobalAbilitySystem').call_function('ApplyEffectToAll',ue.load_class(EFFECT));value['effects_applied']+=1
        self.call_function('ActivateUserFacingCue',GameplayTag(TagName=CUE),params(self.get_property('GetReadyTime')));self.call_function(WARM_WAIT);value['waits']+=1
    def K2_OnEndAbility(self,bWasCancelled):evidence(self)['python_end']+=1;display(self,'Warmup Phase Ended')
    def ClearUserFacingCue(self):
        value=evidence(self);value['python_clear']+=1;tag=self.get_property('Active User Facing Cue').clone()
        if lib('BlueprintGameplayTagLibrary').call_function('IsGameplayTagValid',tag):
            lib('GameplayCueFunctionLibrary').call_function('RemoveGameplayCueOnActor',lib('GameplayStatics').call_function('GetGameState',self),tag,params());self.set_property('Active User Facing Cue',GameplayTag());value['cues_removed']+=1
    def ActivateUserFacingCue(self,GameplayCueTag,Parameters):
        value=evidence(self);value['python_cue']+=1;self.call_function('ClearUserFacingCue');self.set_property('Active User Facing Cue',GameplayCueTag.clone());lib('GameplayCueFunctionLibrary').call_function('AddGameplayCueOnActor',lib('GameplayStatics').call_function('GetGameState',self),GameplayCueTag,Parameters);value['cues_added']+=1
    def AfterWait(self):
        value=evidence(self);value['python_after']+=1;self.call_function('ClearUserFacingCue');subsystem(self,'LyraGlobalAbilitySystem').call_function('RemoveEffectFromAll',ue.load_class(EFFECT));value['effects_removed']+=1;value['starts']+=1;self.call_function(PLAY);return False
    AfterWait.override=WARM_AFTER
class LyraArenaPlayingPythonProfile:
    def K2_ActivateAbility(self):evidence(self)['python_activate']+=1;display(self,'Playing Phase')
    def K2_OnEndAbility(self,bWasCancelled):evidence(self)['python_end']+=1;display(self,'Playing Phase Ended')
class LyraArenaPostgamePythonProfile:
    def K2_ActivateAbility(self):evidence(self)['python_activate']+=1;self.call_function(POST_WAIT);evidence(self)['waits']+=1
    def AfterWait(self):
        value=evidence(self);value['python_after']+=1;value['travels']+=1;lib('LyraSystemStatics').call_function('PlayNextGame',self);return False
    AfterWait.override=POST_AFTER
class LyraArenaWarmupBlueprintFallbackProfile:
    def K2_ActivateAbility(self):evidence(self)['fallback_activate']+=1;self.call_mixin_original('K2_ActivateAbility')
    def K2_OnEndAbility(self,bWasCancelled):evidence(self)['fallback_end']+=1;self.call_mixin_original('K2_OnEndAbility',bWasCancelled)
    def ClearUserFacingCue(self):evidence(self)['fallback_clear']+=1;self.call_mixin_original('ClearUserFacingCue')
    def ActivateUserFacingCue(self,GameplayCueTag,Parameters):evidence(self)['fallback_cue']+=1;self.call_mixin_original('ActivateUserFacingCue',GameplayCueTag,Parameters)
    def AfterWait(self):evidence(self)['fallback_after']+=1;return True
    AfterWait.override=WARM_AFTER
class LyraArenaPlayingBlueprintFallbackProfile:
    def K2_ActivateAbility(self):evidence(self)['fallback_activate']+=1;self.call_mixin_original('K2_ActivateAbility')
    def K2_OnEndAbility(self,bWasCancelled):evidence(self)['fallback_end']+=1;self.call_mixin_original('K2_OnEndAbility',bWasCancelled)
class LyraArenaPostgameBlueprintFallbackProfile:
    def K2_ActivateAbility(self):evidence(self)['fallback_activate']+=1;self.call_mixin_original('K2_ActivateAbility')
    def AfterWait(self):evidence(self)['fallback_after']+=1;return True
    AfterWait.override=POST_AFTER
