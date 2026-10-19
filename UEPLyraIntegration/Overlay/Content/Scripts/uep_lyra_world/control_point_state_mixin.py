"""Control-point initialization, server overlap intent and contest arbitration."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from . import control_point_helpers_mixin as helpers

CLASS=helpers.CLASS
SCORING='/ShooterCore/ControlPoint/B_ControlPointScoring.B_ControlPointScoring_C'
GATES={name:'UEPControlPoint'+name for name in ('Ready','EnterAuthority','ExitAuthority','Recompute')}


def evidence(actor):
    if not hasattr(actor,'_uep_control_point_state'):
        actor._uep_control_point_state={p+'_'+n:0 for p in ('python','fallback') for n in GATES};actor._uep_control_point_state.update(diagnostic_fallbacks=0,reverse_requests=0,play_requests=0)
    return actor._uep_control_point_state


def ready(actor):
    counts=evidence(actor);counts['python_Ready']+=1;state=lib('GameplayStatics').call_function('GetGameState',actor)
    scoring=state.call_function('GetComponentByClass',ue.load_class(SCORING)) if valid(state) else None
    if not actor.call_function('HasAuthority'):actor.set_property('ControlPointGameMode',scoring);return False
    if not valid(scoring):actor.call_function('K2_DestroyActor');return False
    actor.set_property('ControlPointGameMode',scoring);scoring.call_function('RegisterControlPoint',actor)
    rate=lib('KismetMathLibrary').call_function('Divide_DoubleDouble',1.,actor.get_property('TimeRequiredForCapture'));actor.get_property('TL_ConvertPoint').call_function('SetPlayRate',rate);return False


def phase(actor):
    system=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',actor,ue.find_class('LyraGamePhaseSubsystem'))
    return system.call_function('IsPhaseActive',GameplayTag(TagName='ShooterGame.GamePhase.Playing'))


def overlap(actor,pawn,enter):
    counts=evidence(actor);counts['python_'+('EnterAuthority' if enter else 'ExitAuthority')]+=1;values=list(actor.get_property('OverlappingPawns'))
    if enter:
        if pawn not in values:values.append(pawn)
    else:values=[p for p in values if p!=pawn]
    actor.set_property('OverlappingPawns',values)
    if phase(actor):actor.call_function('RecomputeContest');actor.call_function('Enter Audio ' if enter else 'Exit Audio',pawn)
    return False


def one(value):return value[0] if isinstance(value,tuple) else value


def recompute(actor):
    counts=evidence(actor);counts['python_Recompute']+=1;system=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',actor,ue.find_class('LyraTeamSubsystem'));scoring=actor.get_property('ControlPointGameMode');timeline=actor.get_property('TL_ConvertPoint')
    if not all(valid(x) for x in (system,scoring,timeline)):counts['diagnostic_fallbacks']+=1;return True
    teams=[];actor.set_property('OverlappingTeams',[])
    for pawn in actor.get_property('OverlappingPawns'):
        fields=native_outputs('LyraTeamSubsystem','FindTeamFromActor',system.call_function('FindTeamFromActor',pawn))
        if fields['bIsPartOfTeam'] and int(fields['TeamId']) not in teams:teams.append(int(fields['TeamId']));actor.set_property('OverlappingTeams',teams)
    owner=int(actor.get_property('OwnerTeamID'))
    if len(teams)==1:
        if teams[0]==owner:actor.call_function('MarkThisPointRecaptured');return False
        actor.call_function('MarkThisPointContested')
        actor.set_property('OwningTeamColor',one(scoring.call_function('GetTeamColor',owner)) if owner>=0 else ue.FLinearColor(1.,1.,1.,1.))
        actor.set_property('TargetColor',one(scoring.call_function('GetTeamColor',teams[0])));actor.call_function('Activate VFX');timeline.call_function('Play');counts['play_requests']+=1;return False
    actor.call_function('MarkThisPointContested' if len(teams)>1 else 'MarkThisPointRecaptured')
    if timeline.call_function('IsPlaying'):timeline.call_function('Reverse');counts['reverse_requests']+=1
    return False


class LyraControlPointStatePythonProfile:
    Construct=helpers.LyraControlPointHelpersPythonProfile.Construct
    Check=helpers.LyraControlPointHelpersPythonProfile.Check
    Contest=helpers.LyraControlPointHelpersPythonProfile.Contest
    Recapture=helpers.LyraControlPointHelpersPythonProfile.Recapture
    def Ready(self):return ready(self)
    Ready.override=GATES['Ready']
    def Enter(self,Pawn):return overlap(self,Pawn,True)
    Enter.override=GATES['EnterAuthority']
    def Exit(self,Pawn):return overlap(self,Pawn,False)
    Exit.override=GATES['ExitAuthority']
    def Recompute(self):return recompute(self)
    Recompute.override=GATES['Recompute']


def fallback(name):
    def invoke(self,*args):evidence(self)['fallback_'+name]+=1;return True
    invoke.override=GATES[name];return invoke


class LyraControlPointStateBlueprintFallbackProfile:
    Construct=helpers.LyraControlPointHelpersBlueprintFallbackProfile.Construct
    Check=helpers.LyraControlPointHelpersBlueprintFallbackProfile.Check
    Contest=helpers.LyraControlPointHelpersBlueprintFallbackProfile.Contest
    Recapture=helpers.LyraControlPointHelpersBlueprintFallbackProfile.Recapture
    Ready=fallback('Ready');Enter=fallback('EnterAuthority');Exit=fallback('ExitAuthority');Recompute=fallback('Recompute')
