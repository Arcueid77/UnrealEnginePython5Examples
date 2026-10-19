"""TDM decisions; original experience/phase delegates, timers and RepNotify stay native."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,GameplayEffectContextHandle
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import scoring_base_mixin as base
from .hero_burst_cue_mixin import lib

CLASS='/ShooterCore/Elimination/B_TeamDeathMatchScoring.B_TeamDeathMatchScoring_C'
WAIT='UEPTDMNativeWaitExperience'
TIMER='UEPTDMNativeStartCountdown'
POSTGAME='UEPTDMNativePostGame'
CLEAR_TIMER='UEPTDMClearCountdown'
SET_TARGET='UEPTDMSetTargetScore'
SET_TIME='UEPTDMSetCountDownTime'
GATES={name:'UEPTDM'+name for name in ('Begin','GameStarted','CountDown','ForceGameOver','Elimination','SetDamage','ActivateCue','ClearCue','Restart','Victory','TeamScore')}
IMMUNITY='/ShooterCore/Experiences/Phases/GE_DamageImmunity_FromGameMode.GE_DamageImmunity_FromGameMode_C'


def evidence(c):
    if not hasattr(c,'_uep_tdm_scoring'):
        c._uep_tdm_scoring={p+'_'+n:0 for p in ('python','fallback') for n in GATES}
        c._uep_tdm_scoring.update(last_start_players=None,last_winner=None,damage_applies=0,damage_removes=0,restarts=0,diagnostic_fallbacks=0)
    return c._uep_tdm_scoring


def mark(c,name):evidence(c)['python_'+name]+=1
def game_state(c):return lib('GameplayStatics').call_function('GetGameState',c)


def params(ability=1):
    return lib('AbilitySystemBlueprintLibrary').call_function('MakeGameplayCueParameters',NormalizedMagnitude=0.,RawMagnitude=0.,EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),AggregatedSourceTags=GameplayTagContainer(),AggregatedTargetTags=GameplayTagContainer(),Location=ue.FVector(),Normal=ue.FVector(),Instigator=None,EffectCauser=None,SourceObject=None,PhysicalMaterial=None,GameplayEffectLevel=1,AbilityLevel=ability,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)


def score(c,team):
    mark(c,'TeamScore');system=base.teams(c)
    if not valid(system):evidence(c)['diagnostic_fallbacks']+=1;return dict(UseOriginal=True,CurrentScore=0,TargetScore=0,Victory=False)
    current=int(system.call_function('GetTeamTagStackCount',team,base.tag('ShooterGame.Score.Eliminations')));target=int(c.get_property('TargetScore'))
    return dict(UseOriginal=False,CurrentScore=current,TargetScore=target,Victory=current==target)


def query(c,team):
    value=c.call_function('GetTeamScore',team)
    if not isinstance(value,tuple) or len(value)!=3:raise RuntimeError('original TDM score output ABI differs')
    return value


def elimination(c):
    mark(c,'Elimination')
    for team in (1,2):
        current,target,victory=query(c,team)
        if victory:c.call_function('HandleVictory',team);break
    return False


def started(c):
    mark(c,'GameStarted');players=len(base.actors(c,ue.find_class('LyraCharacter')));big=players>=6;evidence(c)['last_start_players']=players
    c.call_function(SET_TARGET,30 if big else 15);c.call_function(SET_TIME,1200. if big else 720.);c.call_function(TIMER)
    c.call_function('ResetAllActivePlayers');c.call_function('PostWarmup');return False


def countdown(c):
    mark(c,'CountDown');value=lib('KismetMathLibrary').call_function('Subtract_DoubleDouble',c.get_property('CountDownTime'),1.);c.call_function(SET_TIME,value)
    if not value<=0.:return False
    c.call_function(CLEAR_TIMER);a=query(c,1)[0];c.set_property('Team0Score',a);b=query(c,2)[0];c.set_property('Team1Score',b)
    c.call_function('HandleVictory',0 if a==b else 1 if a>=b else 2);return False


def damage(c,allow):
    mark(c,'SetDamage');count=int(lib('GameplayStatics').call_function('GetNumPlayerStates',c));systems=[]
    for i in range(count):
        state=lib('GameplayStatics').call_function('GetPlayerState',c,i);asc=lib('AbilitySystemBlueprintLibrary').call_function('GetAbilitySystemComponent',state)
        if not valid(asc):evidence(c)['diagnostic_fallbacks']+=1;return True
        systems.append(asc)
    for asc in systems:
        if allow:asc.call_function('RemoveActiveEffectsWithTags',GameplayTagContainer(GameplayTags=[base.tag('TODO.GameModeDamageImmunity')]));evidence(c)['damage_removes']+=1
        else:asc.call_function('BP_ApplyGameplayEffectToSelf',ue.load_class(IMMUNITY),0.,GameplayEffectContextHandle());evidence(c)['damage_applies']+=1
    return False


def clear(c):
    mark(c,'ClearCue');tag=c.get_property('ActiveUserFacingCue')
    if lib('BlueprintGameplayTagLibrary').call_function('IsGameplayTagValid',tag):
        lib('GameplayCueFunctionLibrary').call_function('RemoveGameplayCueOnActor',game_state(c),tag,params());c.set_property('ActiveUserFacingCue',GameplayTag())
    return False


def activate(c,tag,parameters):
    mark(c,'ActivateCue');c.call_function('ClearUserFacingCue');c.set_property('ActiveUserFacingCue',tag)
    lib('GameplayCueFunctionLibrary').call_function('AddGameplayCueOnActor',game_state(c),tag,parameters);return False


def victory(c,team):
    mark(c,'Victory');c.set_property('WinningTeamId',team);evidence(c)['last_winner']=int(team)
    c.call_function('ActivateUserFacingCue',base.tag('GameplayCue.ShooterGame.UserMessage.MatchDecided'),params(int(c.get_property('WinningTeamId'))));c.call_function(POSTGAME);return False


def restart(c):
    mark(c,'Restart');mode=lib('GameplayStatics').call_function('GetGameMode',c)
    if not valid(mode):evidence(c)['diagnostic_fallbacks']+=1;return True
    for i in range(int(lib('GameplayStatics').call_function('GetNumPlayerControllers',c))):
        mode.call_function('RestartPlayer',lib('GameplayStatics').call_function('GetPlayerController',c,i));evidence(c)['restarts']+=1
    return False


class LyraTDMScoringPythonProfile:
    BaseBegin=base.LyraScoringBasePythonProfile.Begin
    BaseElimination=base.LyraScoringBasePythonProfile.Elimination
    BaseAssist=base.LyraScoringBasePythonProfile.Assist
    BaseReset=base.LyraScoringBasePythonProfile.Reset
    BaseWarmup=base.LyraScoringBasePythonProfile.Warmup
    def Begin(self):mark(self,'Begin');self.call_function(WAIT);return False
    Begin.override=GATES['Begin']
    def GameStarted(self,Phase):return started(self)
    GameStarted.override=GATES['GameStarted']
    def CountDown(self):return countdown(self)
    CountDown.override=GATES['CountDown']
    def Force(self):mark(self,'ForceGameOver');self.call_function('HandleVictory',0);return False
    Force.override=GATES['ForceGameOver']
    def Elimination(self):return elimination(self)
    Elimination.override=GATES['Elimination']
    def Damage(self,AllowDamage):return damage(self,AllowDamage)
    Damage.override=GATES['SetDamage']
    def Activate(self,GameplayCueTag,Parameters):return activate(self,GameplayCueTag,Parameters)
    Activate.override=GATES['ActivateCue']
    def Clear(self):return clear(self)
    Clear.override=GATES['ClearCue']
    def Restart(self):return restart(self)
    Restart.override=GATES['Restart']
    def Victory(self,TeamId):return victory(self,TeamId)
    Victory.override=GATES['Victory']
    def Score(self,TeamId):return score(self,TeamId)
    Score.override=GATES['TeamScore'];Score.uep_named_outputs=True


def fallback(name):
    def invoke(self,*args):evidence(self)['fallback_'+name]+=1;return True
    invoke.override=GATES[name];return invoke


class LyraTDMScoringBlueprintFallbackProfile:
    BaseBegin=base.LyraScoringBaseBlueprintFallbackProfile.Begin
    BaseElimination=base.LyraScoringBaseBlueprintFallbackProfile.Elimination
    BaseAssist=base.LyraScoringBaseBlueprintFallbackProfile.Assist
    BaseReset=base.LyraScoringBaseBlueprintFallbackProfile.Reset
    BaseWarmup=base.LyraScoringBaseBlueprintFallbackProfile.Warmup
    Begin=fallback('Begin');GameStarted=fallback('GameStarted');CountDown=fallback('CountDown');Force=fallback('ForceGameOver');Elimination=fallback('Elimination');Damage=fallback('SetDamage');Activate=fallback('ActivateCue');Clear=fallback('ClearCue');Restart=fallback('Restart');Victory=fallback('Victory')
    def Score(self,TeamId):evidence(self)['fallback_TeamScore']+=1;return dict(UseOriginal=True,CurrentScore=0,TargetScore=0,Victory=False)
    Score.override=GATES['TeamScore'];Score.uep_named_outputs=True
