"""Control-point construction and atomic helpers; original arbitration/RPCs remain."""
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib

CLASS='/ShooterCore/Blueprint/B_ControlPointVolume.B_ControlPointVolume_C'
GATES={n:'UEPControlPoint'+n for n in ('Construct','CheckCounter','Contest','Recapture')}


def evidence(actor):
    if not hasattr(actor,'_uep_control_point_helpers'):
        actor._uep_control_point_helpers={p+'_'+n:0 for p in ('python','fallback') for n in GATES};actor._uep_control_point_helpers.update(diagnostic_fallbacks=0,activations=0)
    return actor._uep_control_point_helpers


def construct(actor):
    counts=evidence(actor);counts['python_Construct']+=1;cube=actor.get_property('Cube');base=actor.get_property('NS_CapturePoint');counter=actor.get_property('NS_CapturePointCounter')
    if not all(valid(x) for x in (cube,base,counter)):counts['diagnostic_fallbacks']+=1;return True
    math=lib('KismetMathLibrary');area=actor.get_property('AreaScale');scale=math.call_function('Divide_VectorFloat',area,10.);cube.call_function('SetRelativeScale3D',scale)
    actual=cube.get_property('RelativeScale3D');height=math.call_function('Add_DoubleDouble',math.call_function('Multiply_DoubleDouble',actual.z,50.),1.)
    cube.call_function('K2_SetRelativeLocation',NewLocation=math.call_function('MakeVector',0.,0.,height),bSweep=False,bTeleport=False)
    positive=math.call_function('Multiply_VectorFloat',area,5.);negative=math.call_function('Multiply_VectorFloat',positive,-1.)
    value=math.call_function('MakeVector4',positive.x,positive.y,negative.x,negative.y);base.call_function('SetVariableVec4','SidesOffset',value)
    counter.call_function('SetVariableFloat','RibbonProgression',0.);counter.call_function('SetVariableFloat','LifeTime',actor.get_property('TimeRequiredForCapture'));return False


def check(actor):
    counts=evidence(actor);counts['python_CheckCounter']+=1;counter=actor.get_property('NS_CapturePointCounter')
    if not valid(counter):counts['diagnostic_fallbacks']+=1;return True
    if not counter.call_function('IsActive'):counter.call_function('Activate',True);counts['activations']+=1
    return False


def mark(actor,recapture):
    counts=evidence(actor);counts['python_'+('Recapture' if recapture else 'Contest')]+=1;scoring=actor.get_property('ControlPointGameMode')
    if not valid(scoring):counts['diagnostic_fallbacks']+=1;return True
    if recapture:scoring.call_function('RecapturePointByTeam',actor,actor.get_property('OwnerTeamID'))
    else:scoring.call_function('ContestPoint',actor)
    return False


class LyraControlPointHelpersPythonProfile:
    def Construct(self):return construct(self)
    Construct.override=GATES['Construct']
    def Check(self):return check(self)
    Check.override=GATES['CheckCounter']
    def Contest(self):return mark(self,False)
    Contest.override=GATES['Contest']
    def Recapture(self):return mark(self,True)
    Recapture.override=GATES['Recapture']


def fallback(name):
    def invoke(self):evidence(self)['fallback_'+name]+=1;return True
    invoke.override=GATES[name];return invoke


class LyraControlPointHelpersBlueprintFallbackProfile:
    Construct=fallback('Construct');Check=fallback('CheckCounter');Contest=fallback('Contest');Recapture=fallback('Recapture')
