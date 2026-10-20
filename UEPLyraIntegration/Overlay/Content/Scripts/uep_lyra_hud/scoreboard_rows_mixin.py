"""Player-row/cell policy; original native 1Hz delegates and interfaces remain."""
import unreal_engine as ue
from unreal_engine.structs import SlateColor
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib

FOLDER='/ShooterCore/UserInterface/ScoreBoard/PlayerRow/'
CLASSES={k:FOLDER+n+'.'+n+'_C' for k,n in (('base','W_BasePlayerRow'),('name','W_SB_PlayerName'),('icon','W_SB_PlayerIcon'),('stat','W_SB_PlayerStat'))}
CLASSES.update({k:'/ShooterCore/'+folder+'/UI/'+n+'.'+n+'_C' for k,folder,n in (('cp','ControlPoint','W_SB_PlayerRow_CP'),('tdm','Elimination','W_SB_PlayerRow_TDM'))})
GATES={k:'UEPSB'+v for k,v in dict(base='BasePlayer',name='NamePlayer',local='LocalName',icon='IconPlayer',stat='StatPlayer',update='StatUpdate',construct='StatConstruct',pre='StatPreConstruct',row='ModePlayer',color='RowColor',score='IndividualScore',children='AwareChildren').items()}
TIMER='UEPSBStatStartNativeTimer'
INTERFACE='/ShooterCore/UserInterface/ITakesLyraPlayerState.ITakesLyraPlayerState_C'


def evidence(w):
    if not hasattr(w,'_uep_scoreboard_rows'):w._uep_scoreboard_rows={p+'_'+n:0 for p in ('python','fallback') for n in GATES};w._uep_scoreboard_rows['diagnostic_fallbacks']=0
    return w._uep_scoreboard_rows
def mark(w,n):evidence(w)['python_'+n]+=1
def diagnostic(w):evidence(w)['diagnostic_fallbacks']+=1;return True
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def color(team,alpha=1.):
    return ue.FLinearColor(*{0:(0.,0.,0.,0.),1:(1.,.539480,.318547,alpha),2:(.283149,.982251,.973446,alpha)}[team])
def slate(c):return SlateColor(SpecifiedColor=c,ColorUseRule=0)
def text(number):return lib('KismetTextLibrary').call_function('Conv_IntToText',int(number),False,True,1,324)


def base(w,ps):
    mark(w,'base');w.set_property('AssociatedPlayerState',ps);children=one(w.call_function('GetPlayerStateAwareChildren'))
    for child in children:
        if valid(child) and lib('KismetSystemLibrary').call_function('DoesImplementInterface',child,ue.load_class(INTERFACE)):child.call_function('SetPlayerState',ps)
    return False
def icon(w,ps):mark(w,'icon');w.set_property('Player State',ps);return False
def name(w,ps):
    mark(w,'name')
    if not valid(ps) or int(ps.call_function('GetTeamId')) not in (0,1,2):return diagnostic(w)
    w.set_property('Player State',ps);control=w.get_property('PlayerNameWidget');control.call_function('SetText',lib('KismetTextLibrary').call_function('Conv_StringToText',ps.call_function('GetPlayerName')));control.call_function('SetColorAndOpacity',slate(color(int(ps.call_function('GetTeamId')))));return False
def local(w):mark(w,'local');w.get_property('PlayerNameWidget').call_function('SetColorAndOpacity',slate(ue.FLinearColor(1.,1.,1.,1.)));return False
def stat(w,ps):mark(w,'stat');w.set_property('AssociatedPlayerState',ps);w.call_function(TIMER);return False
def update(w):
    mark(w,'update');ps=w.get_property('AssociatedPlayerState')
    if not valid(ps):return False
    team=int(ps.call_function('GetTeamId'))
    if team not in (0,1,2):return diagnostic(w)
    value=int(ps.call_function('GetStatTagStackCount',w.get_property('Stat Tag')));control=w.get_property('StatTextWidget');control.call_function('SetText',text(value));control.call_function('SetColorAndOpacity',slate(color(team,.4) if value==0 else ue.FLinearColor(1.,1.,1.,1.)));return False
def width(w,pre):
    mark(w,'pre' if pre else 'construct');value=float(w.get_property('StatWidth'))
    if not pre or value>0.:w.get_property('ForcedWidthSB').call_function('SetWidthOverride',value)
    return False
def row(w):
    mark(w,'row');ps=w.get_property('AssociatedPlayerState');pc=w.call_function('GetOwningPlayer')
    if not valid(ps) or not valid(pc):return diagnostic(w)
    w.set_property('TeamId',int(ps.call_function('GetTeamId')))
    if ps==pc.get_property('PlayerState'):w.get_property('PlayerName').call_function('SetAsLocalPlayer')
    return False
def row_color(w,odd):
    mark(w,'color');team=int(w.get_property('TeamId'))
    if team not in (0,1,2):return diagnostic(w)
    values={0:(0.,0.,0.,0.),1:(.107023,.014444,.011612,.3) if odd else (.036889,.005182,.005605,.3),2:(.006995,.068478,.107023,.3) if odd else (.003035,.021219,.040915,.3)};w.get_property('EntryBorder').call_function('SetBrushColor',ue.FLinearColor(*values[team]));return False
def score(w,widget,score_tag):
    mark(w,'score');ps=w.get_property('AssociatedPlayerState')
    if not valid(ps) or not valid(widget):return diagnostic(w)
    widget.call_function('SetText',text(ps.call_function('GetStatTagStackCount',score_tag)));return False
def children(w):mark(w,'children');return dict(UseOriginal=False,Children=list(one(w.get_property('MyHorizontalBox').call_function('GetAllChildren'))))


def bind(fn,key,named=False):fn.override=GATES[key];fn.uep_named_outputs=named;return fn
class LyraScoreboardBasePythonProfile:
    def Base(self,PlayerState):return base(self,PlayerState)
    Base.override=GATES['base']
class LyraScoreboardNamePythonProfile:
    def Player(self,PlayerState):return name(self,PlayerState)
    Player.override=GATES['name']
    def Local(self):return local(self)
    Local.override=GATES['local']
class LyraScoreboardIconPythonProfile:
    def Player(self,PlayerState):return icon(self,PlayerState)
    Player.override=GATES['icon']
class LyraScoreboardStatPythonProfile:
    def Player(self,PlayerState):return stat(self,PlayerState)
    Player.override=GATES['stat']
    def Update(self):return update(self)
    Update.override=GATES['update']
    def Construct(self):return width(self,False)
    Construct.override=GATES['construct']
    def Pre(self,IsDesignTime):return width(self,True)
    Pre.override=GATES['pre']
class LyraScoreboardModePythonProfile:
    Base=LyraScoreboardBasePythonProfile.Base
    def Player(self):return row(self)
    Player.override=GATES['row']
    def Color(self,IsOddNumberedRow):return row_color(self,IsOddNumberedRow)
    Color.override=GATES['color']
    def Score(self,Widget,ScoreTag):return score(self,Widget,ScoreTag)
    Score.override=GATES['score']
    def Children(self):return children(self)
    Children.override=GATES['children'];Children.uep_named_outputs=True
def fallback(key,named=False):
    def invoke(self,*args):evidence(self)['fallback_'+key]+=1;return dict(UseOriginal=True,Children=[]) if named else True
    return bind(invoke,key,named)
class LyraScoreboardBaseBlueprintFallbackProfile:Base=fallback('base')
class LyraScoreboardNameBlueprintFallbackProfile:Player=fallback('name');Local=fallback('local')
class LyraScoreboardIconBlueprintFallbackProfile:Player=fallback('icon')
class LyraScoreboardStatBlueprintFallbackProfile:Player=fallback('stat');Update=fallback('update');Construct=fallback('construct');Pre=fallback('pre')
class LyraScoreboardModeBlueprintFallbackProfile:Base=LyraScoreboardBaseBlueprintFallbackProfile.Base;Player=fallback('row');Color=fallback('color');Score=fallback('score');Children=fallback('children',True)
