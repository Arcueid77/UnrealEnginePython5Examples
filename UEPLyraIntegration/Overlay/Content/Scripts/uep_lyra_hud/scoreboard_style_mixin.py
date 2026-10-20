"""Team/header styling, native team-stat reads and original activation behavior."""
import unreal_engine as ue
from unreal_engine.structs import SlateBrush
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from .scoreboard_rows_mixin import color,slate,text,one

CLASSES={k:'/ShooterCore/'+folder+'/'+n+'.'+n+'_C' for k,folder,n in (('team','UserInterface/ScoreBoard','W_SB_TeamStat'),('headercp','ControlPoint/UI','W_ScoreBoard_HeaderRow_CP'),('headertdm','Elimination/UI','W_ScoreBoard_HeaderRow_EliminationMode'),('boardcp','ControlPoint/UI','W_MatchScoreBoard_CP'),('boardtdm','Elimination/UI','W_MatchScoreBoard_Elimination'))}
GATES=dict(style='UEPSBTeamStyle',update='UEPSBTeamUpdate',goal='UEPSBTeamGoal',header='UEPSBHeaderStyle',activate='UEPSBBoardActivate')
NAME='UEPSBLocalizedTeamName'
BRUSH_FIELDS=('TintColor','DrawAs','Tiling','Mirroring','ImageSize','Margin','OutlineSettings')
ART='/Game/UI/Menu/Art/'
RESOURCES={k:{t:ART+stem+'_'+suffix+'.'+stem+'_'+suffix for t,suffix in ((1,'Red'),(2,'Blue'))} for k,stem in (('fill','MI_UI_ScoreBoard_ScoreFill'),('header','MI_UI_ScoreBoard_ScoreHeader'),('glow','MI_UI_Scoreboard_Glow'))}
RESOURCES['icon']={t:ART+'MI_UI_Teams_'+n+'Team.MI_UI_Teams_'+n+'Team' for t,n in ((1,'Red'),(2,'Blue'))}


def evidence(w):
    if not hasattr(w,'_uep_scoreboard_style'):w._uep_scoreboard_style={p+'_'+k:0 for p in ('python','fallback') for k in GATES};w._uep_scoreboard_style.update(diagnostic_fallbacks=0,stops=0)
    return w._uep_scoreboard_style
def mark(w,k):evidence(w)['python_'+k]+=1
def diagnostic(w):evidence(w)['diagnostic_fallbacks']+=1;return True
def brush(target,source,resource):
    value=SlateBrush()
    for field in BRUSH_FIELDS:setattr(value,field,getattr(source,field))
    value.ResourceObject=resource;target.call_function('SetBrush',value)
def resource(kind,team):return ue.load_object(ue.find_class('MaterialInterface'),RESOURCES[kind][team])
def header(w):
    mark(w,'header');team=int(w.get_property('TeamId'))
    if team not in (1,2):return diagnostic(w)
    for n in ('PlayerNameWidget','ElimCount','BeenEliminatedCount','AssistCount','ConnectionStatus'):w.get_property(n).call_function('SetColorAndOpacity',slate(color(team,.4)))
    border=w.get_property('HeaderBorder');brush(border,border.get_property('Background'),resource('header',team));return False
def style(w):
    mark(w,'style');team=int(w.get_property('TeamId'))
    if team not in (1,2):return diagnostic(w)
    w.get_property('TeamName').call_function('SetText',one(w.call_function(NAME,team)))
    for n,a in (('TeamName',.1),('StatGoalText',.6),('TeamText',.4),('StatTextWidget',1.)):w.get_property(n).call_function('SetColorAndOpacity',slate(color(team,a)))
    brush(w.get_property('TeamIcon'),w.get_property('TeamIcon').get_property('Brush'),resource('icon',team))
    for field,kind in (('BodyBorder','fill'),('HeaderBorder','header')):
        border=w.get_property(field);brush(border,border.get_property('Background'),resource(kind,team))
    brush(w.get_property('StatGlow'),w.get_property('StatGlow').get_property('Brush'),resource('glow',team));w.get_property('TeamIcon').call_function('GetDynamicMaterial').call_function('SetScalarParameterValue','RotationSpeed',-2.);return False
def update(w):
    mark(w,'update');subsystem=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',w,ue.find_class('LyraTeamSubsystem'))
    if not valid(subsystem):return diagnostic(w)
    value=subsystem.call_function('GetTeamTagStackCount',int(w.get_property('TeamId')),w.get_property('StatId'));w.get_property('StatTextWidget').call_function('SetText',text(value));return False
def goal(w):
    mark(w,'goal');tdm=bool(w.get_property('IsTDMScoring'));name='B_TeamDeathMatchScoring' if tdm else 'B_ControlPointScoring';folder='Elimination' if tdm else 'ControlPoint';cls=ue.load_class('/ShooterCore/'+folder+'/'+name+'.'+name+'_C');state=lib('GameplayStatics').call_function('GetGameState',w)
    if not valid(state):return diagnostic(w)
    scoring=state.get_component_by_type(cls)
    if not valid(scoring):return diagnostic(w)
    values=scoring.call_function('GetTeamScore' if tdm else 'GetTeamScoreCP',int(w.get_property('TeamId')));w.get_property('StatGoalText').call_function('SetText',text(values[1]));return False
def activate(w):
    mark(w,'activate');animation=w.get_property('OnActivated')
    if not valid(animation):return diagnostic(w)
    if w.call_function('IsAnimationPlayingForward',animation):w.call_function('StopAnimation',animation);evidence(w)['stops']+=1
    w.call_function('PlayAnimationForward',animation,1.,False);return False


class LyraScoreboardTeamPythonProfile:
    def Style(self):return style(self)
    Style.override=GATES['style']
    def Update(self):return update(self)
    Update.override=GATES['update']
    def Goal(self):return goal(self)
    Goal.override=GATES['goal']
class LyraScoreboardHeaderPythonProfile:
    def Style(self):return header(self)
    Style.override=GATES['header']
class LyraScoreboardBoardPythonProfile:
    def Activate(self):return activate(self)
    Activate.override=GATES['activate']
def fallback(k):
    def invoke(self):evidence(self)['fallback_'+k]+=1;return True
    invoke.override=GATES[k];return invoke
class LyraScoreboardTeamBlueprintFallbackProfile:Style=fallback('style');Update=fallback('update');Goal=fallback('goal')
class LyraScoreboardHeaderBlueprintFallbackProfile:Style=fallback('header')
class LyraScoreboardBoardBlueprintFallbackProfile:Activate=fallback('activate')
