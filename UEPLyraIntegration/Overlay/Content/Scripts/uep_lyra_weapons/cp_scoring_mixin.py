"""Control-point decisions with original authority, phase and scoring clock."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import scoring_base_mixin as base
from .hero_burst_cue_mixin import lib
from .tdm_scoring_mixin import params

CLASS='/ShooterCore/ControlPoint/B_ControlPointScoring.B_ControlPointScoring_C'
WAIT='UEPCPNativeWaitExperience'
POSTGAME='UEPCPNativePostGame'
CLEAR_TIMER='UEPCPClearScoringTimer'
SET_TARGET='UEPCPSetTargetScore'
GATES={n:'UEPCP'+n for n in ('Begin','GameStarted','Scoring','Capture','Register','Contest','Recapture','Color','Score','Status','ClearCue','ActivateCue','Victory')}


def evidence(c):
    if not hasattr(c,'_uep_cp_scoring'):
        c._uep_cp_scoring={p+'_'+n:0 for p in ('python','fallback') for n in GATES}
        c._uep_cp_scoring.update(team_score_adds=0,capture_awards=0,diagnostic_fallbacks=0,last_player_count=None,last_winner=None)
    return c._uep_cp_scoring


def mark(c,n):evidence(c)['python_'+n]+=1
def diagnostic(c):evidence(c)['diagnostic_fallbacks']+=1
def owner_index(c,point):
    try:return list(c.get_property('ControlPoints')).index(point)
    except ValueError:return -1


def set_owner(c,index,team):
    values=list(c.get_property('ControlPointOwnerTeams'))
    if index>=len(values):values.extend([0]*(index+1-len(values)))
    values[index]=int(team);c.set_property('ControlPointOwnerTeams',values)


def register(c,point):
    mark(c,'Register');points=list(c.get_property('ControlPoints'));index=len(points);points.append(point);c.set_property('ControlPoints',points);set_owner(c,index,-1);return False


def assign(c,point,team,kind):
    mark(c,kind);index=owner_index(c,point)
    if index<0:diagnostic(c);return True
    set_owner(c,index,team);return False


def capture(c,pawns,point):
    mark(c,'Capture');pawns=list(pawns);index=owner_index(c,point)
    if not pawns or index<0:diagnostic(c);return True
    system=base.teams(c)
    if not valid(system):diagnostic(c);return True
    fields=native_outputs('LyraTeamSubsystem','FindTeamFromActor',system.call_function('FindTeamFromActor',pawns[0]))
    if not fields['bIsPartOfTeam']:return False
    team=int(fields['TeamId']);set_owner(c,index,team)
    for pawn in pawns:
        state=pawn.get_property('PlayerState') if valid(pawn) else None
        if not valid(state) or not state.is_a(ue.find_class('LyraPlayerState')):continue
        found=native_outputs('LyraTeamStatics','FindTeamFromObject',lib('LyraTeamStatics').call_function('FindTeamFromObject',state,False))
        if int(found['TeamId'])==team:state.call_function('AddStatTagStack',base.tag('ShooterGame.Score.ControlPointCapture'),1);evidence(c)['capture_awards']+=1
    return False


def status(c,team):
    mark(c,'Status');own=unowned=enemy=0
    for value in c.get_property('ControlPointOwnerTeams'):
        if int(value)==team:own+=1
        elif int(value)==-1:unowned+=1
        else:enemy+=1
    return dict(UseOriginal=False,OwnedByTeam=own,Unowned=unowned,OwnedByEnemy=enemy)


def color(c,team):
    mark(c,'Color');colors=dict(c.get_property('TeamColors'))
    if team not in colors:
        raw=list(c.get_property('RawTeamColors'));index=int(c.get_property('TeamColorAssignIndex'))
        if not 0<=index<len(raw):diagnostic(c);return dict(UseOriginal=True,Color=ue.FLinearColor())
        colors[team]=raw[index];c.set_property('TeamColors',colors);c.set_property('TeamColorAssignIndex',lib('KismetMathLibrary').call_function('Add_IntInt',index,1))
    return dict(UseOriginal=False,Color=colors[team])


def score(c,team):
    mark(c,'Score');system=base.teams(c)
    if not valid(system):diagnostic(c);return dict(UseOriginal=True,Current=0,Target=0,Victory=False)
    current=int(system.call_function('GetTeamTagStackCount',team,base.tag('ShooterGame.ControlPoint.TeamScore')));target=int(c.get_property('TargetScore'))
    return dict(UseOriginal=False,Current=current,Target=target,Victory=current>=target)


def scoring(c):
    mark(c,'Scoring');a=c.call_function('GetPointStatus',1)[0];b=c.call_function('GetPointStatus',2)[0]
    if a==b:return False
    team=1 if a>b else 2;c.set_property('LeadingTeam',team);base.teams(c).call_function('AddTeamTagStack',team,base.tag('ShooterGame.ControlPoint.TeamScore'),1);evidence(c)['team_score_adds']+=1
    if c.call_function('GetTeamScoreCP',int(c.get_property('LeadingTeam')))[2]:c.call_function('HandleVictory',int(c.get_property('LeadingTeam')))
    return False


def started(c):
    mark(c,'GameStarted');players=len(base.actors(c,ue.find_class('LyraCharacter')));evidence(c)['last_player_count']=players;c.call_function(SET_TARGET,150 if players>6 else 125)
    c.call_function('ResetAllActivePlayers');c.call_function('PostWarmup');return False


def clear(c):
    mark(c,'ClearCue');tag=c.get_property('ActiveUserFacingCue')
    if lib('BlueprintGameplayTagLibrary').call_function('IsGameplayTagValid',tag):lib('GameplayCueFunctionLibrary').call_function('RemoveGameplayCueOnActor',lib('GameplayStatics').call_function('GetGameState',c),tag,params());c.set_property('ActiveUserFacingCue',GameplayTag())
    return False


def activate(c,tag,parameters):
    mark(c,'ActivateCue');c.call_function('ClearUserFacingCue');c.set_property('ActiveUserFacingCue',tag);lib('GameplayCueFunctionLibrary').call_function('AddGameplayCueOnActor',lib('GameplayStatics').call_function('GetGameState',c),tag,parameters);return False


def victory(c,team):
    mark(c,'Victory');c.set_property('WinningTeamId',team);evidence(c)['last_winner']=int(team);c.call_function('ActivateUserFacingCue',base.tag('GameplayCue.ShooterGame.UserMessage.MatchDecided'),params(int(c.get_property('WinningTeamId'))));c.call_function(POSTGAME);return False


class LyraCPScoringPythonProfile:
    BaseBegin=base.LyraScoringBasePythonProfile.Begin
    BaseElimination=base.LyraScoringBasePythonProfile.Elimination
    BaseAssist=base.LyraScoringBasePythonProfile.Assist
    BaseReset=base.LyraScoringBasePythonProfile.Reset
    BaseWarmup=base.LyraScoringBasePythonProfile.Warmup
    def Begin(self):mark(self,'Begin');self.call_function(WAIT);return False
    Begin.override=GATES['Begin']
    def GameStarted(self,Phase):return started(self)
    GameStarted.override=GATES['GameStarted']
    def Scoring(self):return scoring(self)
    Scoring.override=GATES['Scoring']
    def Capture(self,Pawns,ControlPoint):return capture(self,Pawns,ControlPoint)
    Capture.override=GATES['Capture']
    def Register(self,ControlPoint):return register(self,ControlPoint)
    Register.override=GATES['Register']
    def Contest(self,ControlPoint):return assign(self,ControlPoint,-1,'Contest')
    Contest.override=GATES['Contest']
    def Recapture(self,ControlPoint,TeamId):return assign(self,ControlPoint,TeamId,'Recapture')
    Recapture.override=GATES['Recapture']
    def Color(self,TeamID):return color(self,TeamID)
    Color.override=GATES['Color'];Color.uep_named_outputs=True
    def Score(self,TeamID):return score(self,TeamID)
    Score.override=GATES['Score'];Score.uep_named_outputs=True
    def Status(self,TeamID):return status(self,TeamID)
    Status.override=GATES['Status'];Status.uep_named_outputs=True
    def Clear(self):return clear(self)
    Clear.override=GATES['ClearCue']
    def Activate(self,GameplayCueTag,Parameters):return activate(self,GameplayCueTag,Parameters)
    Activate.override=GATES['ActivateCue']
    def Victory(self,TeamId):return victory(self,TeamId)
    Victory.override=GATES['Victory']


def fallback(name):
    def invoke(self,*args):evidence(self)['fallback_'+name]+=1;return True
    invoke.override=GATES[name];return invoke


class LyraCPScoringBlueprintFallbackProfile:
    BaseBegin=base.LyraScoringBaseBlueprintFallbackProfile.Begin
    BaseElimination=base.LyraScoringBaseBlueprintFallbackProfile.Elimination
    BaseAssist=base.LyraScoringBaseBlueprintFallbackProfile.Assist
    BaseReset=base.LyraScoringBaseBlueprintFallbackProfile.Reset
    BaseWarmup=base.LyraScoringBaseBlueprintFallbackProfile.Warmup
    Begin=fallback('Begin');GameStarted=fallback('GameStarted');Scoring=fallback('Scoring');Capture=fallback('Capture');Register=fallback('Register');Contest=fallback('Contest');Recapture=fallback('Recapture');Clear=fallback('ClearCue');Activate=fallback('ActivateCue');Victory=fallback('Victory')
    def Color(self,TeamID):evidence(self)['fallback_Color']+=1;return dict(UseOriginal=True,Color=ue.FLinearColor())
    Color.override=GATES['Color'];Color.uep_named_outputs=True
    def Score(self,TeamID):evidence(self)['fallback_Score']+=1;return dict(UseOriginal=True,Current=0,Target=0,Victory=False)
    Score.override=GATES['Score'];Score.uep_named_outputs=True
    def Status(self,TeamID):evidence(self)['fallback_Status']+=1;return dict(UseOriginal=True,OwnedByTeam=0,Unowned=0,OwnedByEnemy=0)
    Status.override=GATES['Status'];Status.uep_named_outputs=True
