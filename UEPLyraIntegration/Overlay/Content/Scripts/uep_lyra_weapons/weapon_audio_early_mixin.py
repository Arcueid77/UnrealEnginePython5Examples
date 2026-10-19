"""Original EarlyReflections seven-query/eight-Tap scheduling on native backends."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs,trace_outputs,break_hit
from .weapon_audio_dispatch_mixin import tap_preset

CLASS="/Game/UEPMixins/BP_WeaponAudioEarlyRouter.BP_WeaponAudioEarlyRouter_C"
METHOD="UEPAudioEarlySchedule"
LIBRARY="/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions_C"
TRACE_DISTANCE=4000.


def lib(name):return ue.find_class(name).get_cdo()
def evidence(router):
    value=getattr(router,"_uep_audio_early",None)
    if value is None:value=dict(python_calls=0,fallback_calls=0,eligible=0,queries=0,taps=0);router._uep_audio_early=value
    return value
def f32(value):return float(lib("KismetMathLibrary").call_function("Conv_DoubleToFloat",value))
def subtract(a,b):return lib("KismetMathLibrary").call_function("Subtract_VectorVector",a,b)
def up(normal):
    math=lib("KismetMathLibrary");return math.call_function("GetUpVector",math.call_function("Conv_VectorToRotator",normal))
def angles(library,origin,normal,axis,world):return library.call_function("GetSideReflectionAngles",origin,normal,TRACE_DISTANCE,axis,world)


def trace(router,world,start,end,ignored):
    evidence(router)["queries"]+=1
    raw=lib("KismetSystemLibrary").call_function("LineTraceSingle",WorldContextObject=world,Start=start,End=end,TraceChannel=0,bTraceComplex=False,
        ActorsToIgnore=ignored,DrawDebugType=0,bIgnoreSelf=True,TraceColor=ue.FLinearColor(1.,0.,0.,1.),TraceHitColor=ue.FLinearColor(0.,1.,0.,1.),DrawTime=2.)
    did_hit,hit=trace_outputs("LineTraceSingle",raw);return did_hit,break_hit(hit)


def tap(router,library,world,suffix,camera,point,tap_id,travel,did_hit,listener):
    evidence(router)["taps"]+=1
    library.call_function("Calculate Tap Properties",suffix,camera,point,tap_id,TRACE_DISTANCE,f32(travel),did_hit,listener,world)


def schedule(router,target,params,world):
    statics=lib("GameplayStatics");platform=statics.call_function("GetPlatformName");strings=lib("KismetStringLibrary")
    if not any(strings.call_function("EqualEqual_StriStri",platform,name) for name in ("Windows","Linux","Mac")) or not valid(target):return False
    payload=native_outputs("AbilitySystemBlueprintLibrary","BreakGameplayCueParameters",lib("AbilitySystemBlueprintLibrary").call_function("BreakGameplayCueParameters",params))
    material=payload["PhysicalMaterial"]
    if valid(material) and int(material.get_property("SurfaceType"))==1:return False
    camera=statics.call_function("GetPlayerCameraManager",world,0)
    if not valid(camera):return False
    listener=camera.call_function("GetCameraLocation");origin=target.call_function("K2_GetActorLocation");point=payload["Location"];math=lib("KismetMathLibrary")
    distance=f32(math.call_function("VSize",subtract(point,listener)))
    if not (distance<TRACE_DISTANCE or target==statics.call_function("GetPlayerPawn",world,0)):return False
    ids,=tap_preset().call_function("GetTapIds")
    if len(ids)<8:return True  # Retain original array-access diagnostics.
    evidence(router)["eligible"]+=1;library=ue.load_class(LIBRARY).get_cdo();normal=payload["Normal"]
    tap(router,library,world,"Direct.Primary",camera,point,ids[0],distance,valid(material),listener)
    end=math.call_function("Add_VectorVector",point,math.call_function("Multiply_VectorVector",normal,math.call_function("Conv_DoubleToVector",TRACE_DISTANCE)))
    direct_hit,direct=trace(router,world,point,end,[]);direct_travel=f32(float(direct["Distance"])+distance)
    tap(router,library,world,"Direct.Second.C",camera,direct["Location"],ids[1],direct_travel,direct_hit,listener)
    left,right=angles(library,point,normal,up(normal),world)
    for suffix,index,endpoint in (("Side.Second.L",4,left),("Side.Second.R",5,right)):
        did_hit,hit=trace(router,world,point,endpoint,[])
        tap(router,library,world,suffix,camera,hit["Location"],ids[index],distance+float(hit["Distance"]),did_hit,listener)
    left,right=angles(library,direct["Location"],direct["Normal"],up(direct["Normal"]),world)
    for suffix,index,endpoint in (("Direct.Second.L",2,left),("Direct.Second.R",3,right)):
        did_hit,hit=trace(router,world,direct["Location"],endpoint,[])
        tap(router,library,world,suffix,camera,hit["Location"],ids[index],direct_travel+float(hit["Distance"]),did_hit,listener)
    forward=math.call_function("Normal",subtract(point,origin),.0001);axis=math.call_function("GetUpVector",camera.call_function("GetCameraRotation"))
    left,right=angles(library,origin,forward,axis,world)
    # These two source pins are deliberately unconnected, hence zero listeners.
    for suffix,index,endpoint in (("Side.First.L",6,left),("Side.First.R",7,right)):
        did_hit,hit=trace(router,world,origin,endpoint,[target])
        tap(router,library,world,suffix,camera,hit["Location"],ids[index],float(hit["Distance"]),did_hit,ue.FVector())
    return False


class LyraWeaponAudioEarlyPythonProfile:
    def Early(self,Target,Parameters,WorldContext):
        evidence(self)["python_calls"]+=1;return dict(UseOriginal=bool(schedule(self,Target,Parameters,WorldContext)))
    Early.override=METHOD;Early.uep_named_outputs=True


class LyraWeaponAudioEarlyBlueprintFallbackProfile:
    def Early(self,Target,Parameters,WorldContext):evidence(self)["fallback_calls"]+=1;return dict(UseOriginal=True)
    Early.override=METHOD;Early.uep_named_outputs=True
