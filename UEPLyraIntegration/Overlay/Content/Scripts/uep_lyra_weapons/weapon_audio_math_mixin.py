"""Static audio math via typed Object dispatch; public static functions stay native."""
import unreal_engine as ue

CLASS="/Game/UEPMixins/BP_WeaponAudioMathRouter.BP_WeaponAudioMathRouter_C"
SIDE="UEPAudioSideAngles"
WHIZ="UEPAudioWhizBy"
METHODS={"GetSideReflectionAngles":SIDE,"Calculate Whiz By":WHIZ}


def math():return ue.find_class("KismetMathLibrary").get_cdo()
def evidence(router):
    value=getattr(router,"_uep_audio_math",None)
    if value is None:value=dict(side_python=0,side_fallback=0,whiz_python=0,whiz_fallback=0);router._uep_audio_math=value
    return value
def zero():return math().call_function("MakeVector",0.,0.,0.)


def side(origin,normal,distance,axis):
    lib=math();scale=lib.call_function("Conv_DoubleToVector",float(distance));values=[]
    for angle in (45.,-45.):
        rotated=lib.call_function("RotateAngleAxis",normal,angle,axis)
        values.append(lib.call_function("Add_VectorVector",origin,lib.call_function("Multiply_VectorVector",rotated,scale)))
    return dict(UseOriginal=False,**{"Angle L":values[0],"Angle R":values[1]})


def whiz(listener,origin,minimum,impact):
    lib=math();closest=lib.call_function("FindClosestPointOnSegment",listener,origin,impact)
    delta=lib.call_function("Subtract_VectorVector",listener,closest);perpendicular=lib.call_function("Normal",delta,.0001)
    distance=float(lib.call_function("Conv_DoubleToFloat",lib.call_function("VSize",delta)))
    forward=lib.call_function("Normal",lib.call_function("Subtract_VectorVector",impact,origin),.0001)
    right=lib.call_function("GetRightVector",lib.call_function("Conv_VectorToRotator",forward))
    from_right=float(lib.call_function("Dot_VectorVector",right,perpendicular))<=0.
    firing_distance=float(lib.call_function("Conv_DoubleToFloat",lib.call_function("VSize",lib.call_function("Subtract_VectorVector",listener,origin))))
    spread=float(lib.call_function("Conv_DoubleToFloat",distance+float(minimum)))
    return dict(UseOriginal=False,Location=closest,StereoSpread=spread,FromTheRight=from_right,FiringDistance=firing_distance)


class LyraWeaponAudioMathPythonProfile:
    def SideAngles(self,Origin,Normal,TraceDistance,Axis,WorldContext):evidence(self)["side_python"]+=1;return side(Origin,Normal,TraceDistance,Axis)
    SideAngles.override=SIDE;SideAngles.uep_named_outputs=True
    def WhizBy(self,ListenerOrigin,FireOrigin,MinStereoSpread,ImpactPosition,WorldContext):evidence(self)["whiz_python"]+=1;return whiz(ListenerOrigin,FireOrigin,MinStereoSpread,ImpactPosition)
    WhizBy.override=WHIZ;WhizBy.uep_named_outputs=True


class LyraWeaponAudioMathBlueprintFallbackProfile:
    def SideAngles(self,Origin,Normal,TraceDistance,Axis,WorldContext):evidence(self)["side_fallback"]+=1;return dict(UseOriginal=True,**{"Angle L":zero(),"Angle R":zero()})
    SideAngles.override=SIDE;SideAngles.uep_named_outputs=True
    def WhizBy(self,ListenerOrigin,FireOrigin,MinStereoSpread,ImpactPosition,WorldContext):evidence(self)["whiz_fallback"]+=1;return dict(UseOriginal=True,Location=zero(),StereoSpread=0.,FromTheRight=False,FiringDistance=0.)
    WhizBy.override=WHIZ;WhizBy.uep_named_outputs=True
