"""TDM score, style and countdown decisions with original native UMG/audio."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from .scoreboard_rows_mixin import slate
from .scoreboard_style_mixin import brush
from .control_point_widgets_mixin import style_resource

CLASS='/ShooterCore/Elimination/UI/W_ScoreWidget_Elimination.W_ScoreWidget_Elimination_C'
GATES={k:'UEPTDMHud'+v for k,v in dict(ally='Ally',enemy='Enemy',style='Style',sides='Sides',clock='Clock',sound='Sound',score='Score',team='Team').items()}
CLOCK='UEPTDMHudNativeClockValues'
SCORE_SOUND='/Game/Audio/MetaSounds/sfx_EndOfRound-LowScore_nl_meta.sfx_EndOfRound-LowScore_nl_meta'
CLOCK_SOUND='/Game/Audio/MetaSounds/sfx_EndOfRound-Tick_nl_meta.sfx_EndOfRound-Tick_nl_meta'


def evidence(w):
    if not hasattr(w,'_uep_elimination_score'):w._uep_elimination_score={p+'_'+k:0 for p in ('python','fallback') for k in GATES};w._uep_elimination_score.update(diagnostic_fallbacks=0,score_audio_spawns=0,clock_audio_spawns=0)
    return w._uep_elimination_score
def mark(w,key):evidence(w)['python_'+key]+=1
def diagnostic(w):evidence(w)['diagnostic_fallbacks']+=1;return True
def spawn(w,path,name,value,key):
    audio=lib('GameplayStatics').call_function('SpawnSound2D',w,ue.load_object(ue.find_class('SoundBase'),path),1.,1.,0.,None,False,True);evidence(w)[key+'_audio_spawns']+=1
    if not valid(audio):return False
    audio.call_function('SetIntParameter',name,int(value));return True


def team_score(w,mode,enemy):
    mark(w,'enemy' if enemy else 'ally');prefix='Enemy' if enemy else 'Ally';value,target=mode.call_function('GetTeamScore',int(w.get_property('EnemyTeamID' if enemy else 'MyTeamID')))[:2];ratio=0. if int(target)==0 else float(value)/float(target)
    w.get_property(prefix+'Score').call_function('SetCurrentValue',float(value));w.get_property(prefix+'Goal').call_function('SetCurrentValue',float(target));materials=[w.get_property(prefix+n).call_function('GetDynamicMaterial') for n in ('ProgressBar','ProgressBarGlow')]
    for material in materials:material.call_function('SetScalarParameterValue','AnimateArcFill',ratio)
    return False
def resource(kind,team):
    if kind in ('logo','glow'):return style_resource(kind,team)
    if team==0:return None
    name='MI_UI_TeamScore_BarFill'+('_Glow' if kind=='arcglow' else '')+('_Enemy' if team==1 else '');return ue.load_object(ue.find_class('MaterialInterface'),'/Game/UI/Hud/Art/'+name+'.'+name)
def style(w):
    mark(w,'style');ally=int(w.get_property('MyTeamID'));enemy=int(w.get_property('EnemyTeamID'))
    if ally not in (0,1,2) or enemy not in (0,1,2):return diagnostic(w)
    rgb={0:(0.,0.,0.),1:(1.,.496933,.318547),2:(.283149,.887923,.822786)}
    for name,team,alpha in (('AllyGoal',ally,.6),('EnemyGoal',enemy,.6),('AllyScore',ally,1.),('EnemyScore',enemy,1.)):w.get_property(name).call_function('SetColorAndOpacity',slate(ue.FLinearColor(*rgb[team],alpha if team else 0.)))
    for name,kind,team in (('AllyScoreGlow','glow',ally),('EnemyScoreGlow','glow',enemy),('AllyLogo','logo',ally),('EnemyLogo','logo',enemy),('AllyProgressBar','arc',ally),('EnemyProgressBar','arc',enemy),('AllyProgressBarGlow','arcglow',ally),('EnemyProgressBarGlow','arcglow',enemy)):
        target=w.get_property(name);brush(target,target.get_property('Brush'),resource(kind,team))
    return False
def sides(w):
    mark(w,'sides');team=int(w.get_property('MyTeamID'))
    if team not in (0,1,2):return diagnostic(w)
    w.get_property('ScoreBorder').call_function('GetDynamicMaterial').call_function('SetScalarParameterValue','InverseGradient',float(team==1));return False
def clock(w,time):
    mark(w,'clock');formatted,current=w.call_function(CLOCK,float(time));w.get_property('Clock').call_function('SetText',formatted);previous=int(w.get_property('PreviousTime'))
    if float(time)<=10. and previous>0:
        if int(current)==previous:return False
        if not spawn(w,CLOCK_SOUND,'SecondsLeft',current,'clock'):return False
    w.set_property('PreviousTime',int(current));return False
def sound(w,mode):
    mark(w,'sound');a,at=mode.call_function('GetTeamScore',int(w.get_property('MyTeamID')))[:2];b,bt=mode.call_function('GetTeamScore',int(w.get_property('EnemyTeamID')))[:2];left=min(int(at)-int(a),int(bt)-int(b))
    if left==int(w.get_property('PreviousScoreLeft')):return False
    if 0<left<=5 and not spawn(w,SCORE_SOUND,'ScoreLeft',left,'score'):return False
    w.set_property('PreviousScoreLeft',left);return False
def score(w):
    mark(w,'score');mode=w.get_property('TDMScoring')
    if int(w.get_property('MyTeamID'))<0 or not valid(mode):return False
    w.call_function('UpdateAllyTeamScore',mode);w.call_function('Update Enemy Team Score',mode);w.call_function('EvaluateSound_RoundEnding',mode);return False
def team(w,value):
    mark(w,'team');value=int(value)
    if value not in (0,1,2):return diagnostic(w)
    w.set_property('MyTeamID',value);w.set_property('EnemyTeamID',{0:0,1:2,2:1}[value]);w.call_function('UpdateTeamStyles');w.call_function('UpdateStyleSides');return False


class LyraEliminationScorePythonProfile:
    def Ally(self,TDMScoring):return team_score(self,TDMScoring,False)
    Ally.override=GATES['ally']
    def Enemy(self,TDMScoring):return team_score(self,TDMScoring,True)
    Enemy.override=GATES['enemy']
    def Style(self):return style(self)
    Style.override=GATES['style']
    def Sides(self):return sides(self)
    Sides.override=GATES['sides']
    def Clock(self,Time):return clock(self,Time)
    Clock.override=GATES['clock']
    def Sound(self,TDMScoring):return sound(self,TDMScoring)
    Sound.override=GATES['sound']
    def Score(self):return score(self)
    Score.override=GATES['score']
    def Team(self,TeamId):return team(self,TeamId)
    Team.override=GATES['team']


def fallback(key):
    def invoke(self,*args):evidence(self)['fallback_'+key]+=1;return True
    invoke.override=GATES[key];return invoke
class LyraEliminationScoreBlueprintFallbackProfile:
    Ally=fallback('ally');Enemy=fallback('enemy');Style=fallback('style');Sides=fallback('sides');Clock=fallback('clock');Sound=fallback('sound');Score=fallback('score');Team=fallback('team')
