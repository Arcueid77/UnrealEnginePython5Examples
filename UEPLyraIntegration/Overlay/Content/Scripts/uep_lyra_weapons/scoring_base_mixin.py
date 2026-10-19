"""Shared scoring/reset/warmup policy; native authority and message proxies remain."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from unreal_engine.enums import ELyraTeamComparison
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .hero_burst_cue_mixin import lib

CLASS='/ShooterCore/Game/B_ShooterGameScoring_Base.B_ShooterGameScoring_Base_C'
START='UEPScoringBeginNativeListeners'
GATES=dict(begin='UEPScoringBaseBegin',elimination='UEPScoringElimination',assist='UEPScoringAssist',reset='UEPScoringResetPlayers',warmup='UEPScoringPostWarmup')
SPAWNER='/ShooterCore/Blueprint/B_WeaponSpawner.B_WeaponSpawner_C'
GRENADE='/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C'


def evidence(component):
    if not hasattr(component,'_uep_scoring_base'):
        component._uep_scoring_base={p+'_'+m:0 for p in ('python','fallback') for m in GATES}
        component._uep_scoring_base.update(team_adds=0,kills=0,deaths=0,hooks=0,assists=0,reset_seen=0,reset_missing_asc=0,reset_missing_controller=0,reset_spawning_skips=0,reset_sent=0,spawners_reset=0,grenades_destroyed=0,diagnostic_fallbacks=0)
    return component._uep_scoring_base


def teams(component):return lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',component,ue.find_class('LyraTeamSubsystem'))
def tag(name):return GameplayTag(TagName=name)
def actors(component,cls):return native_outputs('GameplayStatics','GetAllActorsOfClass',lib('GameplayStatics').call_function('GetAllActorsOfClass',component,cls))['OutActors']


def elimination(component,message):
    counts=evidence(component);counts['python_elimination']+=1;system=teams(component)
    if not valid(system):counts['diagnostic_fallbacks']+=1;return True
    relation=native_outputs('LyraTeamSubsystem','CompareTeams',system.call_function('CompareTeams',message.Instigator,message.Target))
    if int(relation['ReturnValue'])!=int(ELyraTeamComparison.DifferentTeams):return False
    system.call_function('AddTeamTagStack',relation['TeamIdA'],tag('ShooterGame.Score.Eliminations'),1);counts['team_adds']+=1
    source,target=message.Instigator,message.Target;cls=ue.find_class('LyraPlayerState')
    if not valid(source) or not source.is_a(cls):return False
    source.call_function('AddStatTagStack',tag('ShooterGame.Score.Eliminations'),1);counts['kills']+=1
    if not valid(target) or not target.is_a(cls):return False
    target.call_function('AddStatTagStack',tag('ShooterGame.Score.Deaths'),1);counts['deaths']+=1
    component.call_function('OnEliminationScored');counts['hooks']+=1;return False


def assist(component,message):
    counts=evidence(component);counts['python_assist']+=1;source=message.Instigator
    if valid(source) and source.is_a(ue.find_class('LyraPlayerState')):source.call_function('AddStatTagStack',tag('ShooterGame.Score.Assists'),1);counts['assists']+=1
    return False


def reset(component):
    counts=evidence(component);counts['python_reset']+=1
    for pawn in actors(component,ue.find_class('LyraCharacter')):
        counts['reset_seen']+=1;asc=lib('AbilitySystemBlueprintLibrary').call_function('GetAbilitySystemComponent',pawn)
        if not valid(asc):counts['reset_missing_asc']+=1;continue
        if not valid(pawn.call_function('GetController')):counts['reset_missing_controller']+=1;continue
        if asc.call_function('HasMatchingGameplayTag',tag('Status.SpawningIn')):counts['reset_spawning_skips']+=1;continue
        lib('AbilitySystemBlueprintLibrary').call_function('SendGameplayEventToActor',pawn,tag('GameplayEvent.RequestReset'),GameplayEventData());counts['reset_sent']+=1
    return False


def warmup(component):
    counts=evidence(component);counts['python_warmup']+=1
    for actor in actors(component,ue.load_class(SPAWNER)):
        if valid(actor):actor.call_function('ResetCoolDown');counts['spawners_reset']+=1
    for actor in actors(component,ue.load_class(GRENADE)):
        if valid(actor):actor.call_function('K2_DestroyActor');counts['grenades_destroyed']+=1
    return False


class LyraScoringBasePythonProfile:
    def Begin(self):evidence(self)['python_begin']+=1;self.call_function(START);return False
    Begin.override=GATES['begin']
    def Elimination(self,Payload):return elimination(self,Payload)
    Elimination.override=GATES['elimination']
    def Assist(self,Payload):return assist(self,Payload)
    Assist.override=GATES['assist']
    def Reset(self):return reset(self)
    Reset.override=GATES['reset']
    def Warmup(self):return warmup(self)
    Warmup.override=GATES['warmup']


def fallback(name):
    def invoke(self,*args):evidence(self)['fallback_'+name]+=1;return True
    invoke.override=GATES[name];return invoke


class LyraScoringBaseBlueprintFallbackProfile:
    Begin=fallback('begin')
    Elimination=fallback('elimination')
    Assist=fallback('assist')
    Reset=fallback('reset')
    Warmup=fallback('warmup')
