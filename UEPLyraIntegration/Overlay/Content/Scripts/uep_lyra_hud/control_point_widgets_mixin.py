"""Control-point HUD policy with native async, material, text and audio backends."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from .scoreboard_rows_mixin import slate,text
from .scoreboard_style_mixin import brush

CLASSES={k:'/ShooterCore/ControlPoint/UI/'+n+'.'+n+'_C' for k,n in (('score','W_CPScoreWidget'),('marker','W_ControlPointMarker'),('status','W_ControlPointStatusWidget'))}
VOLUME='/ShooterCore/Blueprint/B_ControlPointVolume.B_ControlPointVolume_C'
GATES={k:'UEPCPHud'+v for k,v in dict(sides='Sides',style='Style',score='Score',sound='Sound',scoreteam='ScoreTeam',materials='Materials',initialize='Initialize',marker='Marker',owner='Owner',owned='Owned',occupied='Occupied',status='Status',statusteam='StatusTeam').items()}
SOUND='/Game/Audio/MetaSounds/sfx_EndOfRound-LowScore_nl_meta.sfx_EndOfRound-LowScore_nl_meta'
MATERIALS=('Fill','Ring','RingGlow','PointLetter','SoftGlow','BurstRing')


def evidence(w):
    if not hasattr(w,'_uep_control_point_widgets'):w._uep_control_point_widgets={p+'_'+k:0 for p in ('python','fallback') for k in GATES};w._uep_control_point_widgets.update(diagnostic_fallbacks=0,audio=[])
    return w._uep_control_point_widgets
def mark(w,k):evidence(w)['python_'+k]+=1
def diagnostic(w):evidence(w)['diagnostic_fallbacks']+=1;return True
def scalar(w,fields,name,value):
    for field in fields:w.get_property(field+'MID').call_function('SetScalarParameterValue',name,float(value))


def sides(w):
    mark(w,'sides');team=int(w.get_property('MyTeamID'))
    if team not in (0,1,2):return diagnostic(w)
    w.get_property('ScoreBorder').call_function('GetDynamicMaterial').call_function('SetScalarParameterValue','InverseGradient',float(team==1));return False
def style_resource(kind,team):
    if team==0:return None
    name=('MI_UI_Teams_'+('Red' if team==1 else 'Blue')+'Team_ScoreCounter') if kind=='logo' else 'MI_UI_TeamScore_BarFill_NumberGlow'+('_Enemy' if team==1 else '')
    folder='/Game/UI/Menu/Art/' if kind=='logo' else '/Game/UI/Hud/Art/'
    return ue.load_object(ue.find_class('MaterialInterface'),folder+name+'.'+name)
def style(w):
    mark(w,'style');ally=int(w.get_property('MyTeamID'));enemy=int(w.get_property('EnemyTeamID'))
    if ally not in (0,1,2) or enemy not in (0,1,2):return diagnostic(w)
    colors={0:(0.,0.,0.,0.),1:(1.,.496933,.318547,1.),2:(.283149,.887923,.822786,1.)}
    for field,team in (('AllyScore',ally),('EnemyScore',enemy)):w.get_property(field).call_function('SetColorAndOpacity',slate(ue.FLinearColor(*colors[team])))
    for field,kind,team in (('AllyScoreGlow','glow',ally),('EnemyScoreGlow','glow',enemy),('AllyLogo','logo',ally),('EnemyLogo','logo',enemy)):
        target=w.get_property(field);brush(target,target.get_property('Brush'),style_resource(kind,team))
    return False
def score(w):
    mark(w,'score');mode=w.get_property('ControlPointMode')
    if not valid(mode):return False
    team=int(w.get_property('MyTeamID'))
    if team not in (0,1,2):return diagnostic(w)
    current,target=mode.call_function('GetTeamScoreCP',team)[:2];w.get_property('Goal').call_function('SetText',text(target));w.get_property('AllyScore').call_function('SetText',text(max(0,min(int(current),int(target)))))
    current,target=mode.call_function('GetTeamScoreCP',{0:0,1:2,2:1}[team])[:2];w.get_property('EnemyScore').call_function('SetText',text(max(0,min(int(current),int(target)))))
    w.call_function('EvaluateSound_RoundEnding',mode);return False
def sound(w,mode):
    mark(w,'sound');a,at=mode.call_function('GetTeamScoreCP',int(w.get_property('MyTeamID')))[:2];b,bt=mode.call_function('GetTeamScoreCP',int(w.get_property('EnemyTeamID')))[:2];left=min(int(at)-int(a),int(bt)-int(b))
    if left==int(w.get_property('PreviousScoreLeft')):return False
    if 0<left<=5:
        audio=lib('GameplayStatics').call_function('SpawnSound2D',w,ue.load_object(ue.find_class('SoundBase'),SOUND),1.,1.,0.,None,False,True)
        evidence(w)['audio'].append(dict(left=left,valid=valid(audio),component=audio))
        if not valid(audio):return False
        audio.call_function('SetIntParameter','ScoreLeft',left)
    w.set_property('PreviousScoreLeft',left);return False
def scoreteam(w,team):
    mark(w,'scoreteam');team=int(team)
    if team not in (0,1,2):return diagnostic(w)
    w.set_property('MyTeamID',team);w.set_property('EnemyTeamID',{0:0,1:2,2:1}[team]);w.call_function('UpdateStyleSides');w.call_function('UpdateTeamStyles');w.call_function('UpdateScore');return False


def materials(w):
    mark(w,'materials')
    for name in MATERIALS:w.set_property(name+'MID',w.get_property(name).call_function('GetDynamicFontMaterial' if name=='PointLetter' else 'GetDynamicMaterial'))
    return False
def initialize(w):mark(w,'initialize');w.get_property('PointLetter').call_function('SetText',w.get_property('PointLetterText'));w.call_function('SetDynamicMaterial');return False
def marker(w,volume):
    mark(w,'marker');w.set_property('PointOwnerTeamId',volume.get_property('OwnerTeamID'));w.call_function('PointOwnerChanged',volume);w.call_function('IsPointOwned');w.call_function('IsPointOccupied',volume);return False
def owner(w,volume):
    mark(w,'owner');team=int(w.get_property('PointOwnerTeamId'))
    if team==int(w.get_property('PreviousPointOwnerTeamId')):return False
    w.call_function('PlayAnimationForward',w.get_property('OnPointOwnerChanged'),1.,False);w.set_property('PreviousPointOwnerTeamId',volume.get_property('OwnerTeamID'));scalar(w,('BurstRing',),'IsEmptyPoint',team not in (1,2));scalar(w,('BurstRing',),'IsRedOrBlue',team!=1);return False
def owned(w):
    mark(w,'owned');team=int(w.get_property('PointOwnerTeamId'));scalar(w,('Fill','SoftGlow'),'IsEmptyPoint',team not in (1,2));scalar(w,('PointLetter',),'bIsDisabled',team not in (1,2));scalar(w,('PointLetter',),'Hover_Animate',team!=1);scalar(w,('Fill','SoftGlow'),'IsRedOrBlue',team!=1);return False
def occupied(w,volume):
    mark(w,'occupied');teams=list(volume.get_property('OverlappingTeams'));fields=('Ring','RingGlow');scalar(w,fields,'IsEmptyPoint',not teams)
    for team in teams:
        scalar(w,fields,'IsContested',len(teams)!=1)
        if len(teams)==1:scalar(w,fields,'IsRedOrBlue',int(team)!=1)
        scalar(w,fields,'IsFlashing',len(teams)!=1 or int(w.get_property('PointOwnerTeamId'))!=int(team))
    return False
def status(w):
    mark(w,'status');mode=w.get_property('ControlPointMode')
    if not valid(mode) or int(w.get_property('MyTeamID'))<0:return False
    cls=ue.load_class(VOLUME)
    for index,volume in enumerate(mode.get_property('ControlPoints')):
        if valid(volume) and volume.is_a(cls):w.get_property('W_ControlPointMarker_'+('A' if index==0 else 'B' if index==1 else 'C')).call_function('UpdateControlPointStatus',volume)
    return False
def statusteam(w,team):mark(w,'statusteam');w.set_property('MyTeamID',int(team));return False


def method(key,fn):
    def invoke(self,*args):return fn(self,*args)
    invoke.override=GATES[key];return invoke
def fallback(key):
    def invoke(self,*args):evidence(self)['fallback_'+key]+=1;return True
    invoke.override=GATES[key];return invoke

class LyraCPScorePythonProfile:
    Sides=method('sides',sides);Style=method('style',style);Score=method('score',score);Sound=method('sound',sound);Team=method('scoreteam',scoreteam)
class LyraCPScoreBlueprintFallbackProfile:
    Sides=fallback('sides');Style=fallback('style');Score=fallback('score');Sound=fallback('sound');Team=fallback('scoreteam')
class LyraCPMarkerPythonProfile:
    Materials=method('materials',materials);Initialize=method('initialize',initialize);Marker=method('marker',marker);Owner=method('owner',owner);Owned=method('owned',owned);Occupied=method('occupied',occupied)
class LyraCPMarkerBlueprintFallbackProfile:
    Materials=fallback('materials');Initialize=fallback('initialize');Marker=fallback('marker');Owner=fallback('owner');Owned=fallback('owned');Occupied=fallback('occupied')
class LyraCPStatusPythonProfile:
    Status=method('status',status);Team=method('statusteam',statusteam)
class LyraCPStatusBlueprintFallbackProfile:
    Status=fallback('status');Team=fallback('statusteam')
