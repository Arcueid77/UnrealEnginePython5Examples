"""Original motion-effect footprint policy with native Niagara and latent delay."""
import unreal_engine as ue
from unreal_engine.enums import EAttachLocation, ENCPoolMethod, ERelativeTransformSpace
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import break_hit

CLASS = "/Game/Effects/Blueprints/B_FootStep.B_FootStep_C"
DELAY, AFTER = "UEPFootstepBeginNativeDelay", "UEPFootstepAfterNativeDelay"


def lib(name): return ue.find_class(name).get_cdo()


def evidence(actor):
    if not hasattr(actor, "_uep_footstep"):
        actor._uep_footstep = dict(python_calls=0, fallback_calls=0, original_diagnostic_calls=0,
            spawns=0, reuses=0, writes=0, native_delay_requests=0, python_cleanup=0,
            fallback_cleanup=0, cleanup_repeats=0, destroys=0)
    return actor._uep_footstep


def footprint(actor, Bone, HitResult):
    counts = evidence(actor)
    actor.set_property("Hit Result", HitResult)
    surface = lib("GameplayStatics").call_function("GetSurfaceType", HitResult)
    actor.set_property("FootStepSurfaceType", surface)
    if int(surface) not in (0, 1, 2, 3): return
    math = lib("KismetMathLibrary")
    actor.set_property("FootStepSurfaceTypeNiagara", math.call_function("Conv_ByteToInt", surface))
    actor.set_property("FootStepSide", math.call_function("EqualEqual_NameName", Bone, actor.get_property("FootStepRightFootBone")))
    text = lib("KismetStringLibrary").call_function("Conv_NameToString", Bone)
    socket = lib("KismetStringLibrary").call_function("Conv_StringToName",
        lib("KismetStringLibrary").call_function("Concat_StrStr", text, "_Socket"))
    actor.set_property("CurrentSocket", socket)
    transform = actor.get_property("Skeletal Mesh Component").call_function("GetSocketTransform", socket, ERelativeTransformSpace.RTS_World)
    actor.set_property("FootStepSocketTransform", transform)
    hit = break_hit(HitResult)
    actor.set_property("FootStepHitLocation", hit["Location"])
    actor.set_property("FootStepHitNormal", hit["Normal"])
    forward = math.call_function("TransformDirection", transform, ue.FVector(1., 0., 0.))
    right = math.call_function("Normal", math.call_function("Cross_VectorVector", hit["Normal"], forward), .0001)
    axes = math.call_function("MakeRotationFromAxes", math.call_function("Cross_VectorVector", right, hit["Normal"]), right, hit["Normal"])
    actor.set_property("FootStepOrientation", math.call_function("Conv_RotatorToQuaternion", axes))
    component = actor.get_property("NS_FootPrint")
    if not valid(component) or not component.call_function("IsActive"):
        component = lib("NiagaraFunctionLibrary").call_function("SpawnSystemAttached",
            SystemTemplate=actor.get_property("Foot Print System"), AttachToComponent=actor.get_property("DefaultSceneRoot"),
            AttachPointName="None", Location=ue.FVector(), Rotation=ue.FRotator(),
            LocationType=EAttachLocation.KeepRelativeOffset, bAutoDestroy=True, bAutoActivate=True,
            PoolingMethod=getattr(ENCPoolMethod, "None"), bPreCullCheck=True)
        actor.set_property("NS_FootPrint", component); actor.set_property("FootPrintTrigger", False); counts["spawns"] += 1
    else: counts["reuses"] += 1
    actor.set_property("FootPrintTrigger", not bool(actor.get_property("FootPrintTrigger")))
    if valid(component):
        for method, name, field in (("SetVariableBool", "User.Trigger", "FootPrintTrigger"),
                ("SetVariableVec3", "User.StepLocation", "FootStepHitLocation"),
                ("SetVariableQuat", "User.Orientation", "FootStepOrientation"),
                ("SetVariableInt", "User.SurfaceType", "FootStepSurfaceTypeNiagara"),
                ("SetVariableBool", "User.StepSide", "FootStepSide")):
            component.call_function(method, name, actor.get_property(field)); counts["writes"] += 1


def motion(actor, *args):
    counts = evidence(actor); counts["python_calls"] += 1
    # The source uses the actor's stored mesh, ignoring the interface component.
    # Retain its native diagnostics when that stored mesh or system is absent.
    if actor.get_property("Enable FootPlantEffect") and bool(args[6]):
        if not valid(actor.get_property("Skeletal Mesh Component")) or not valid(actor.get_property("Foot Print System")):
            counts["original_diagnostic_calls"] += 1
            return actor.call_mixin_original("AnimMotionEffect", *args)
        footprint(actor, args[0], args[7])
    counts["native_delay_requests"] += 1; actor.call_function(DELAY)


def cleanup(actor):
    counts = evidence(actor); counts["python_cleanup"] += 1
    if valid(actor.get_property("NS_FootPrint")):
        counts["cleanup_repeats"] += 1; counts["native_delay_requests"] += 1; actor.call_function(DELAY)
    else: counts["destroys"] += 1; actor.call_function("K2_DestroyActor")


class LyraFootstepPythonProfile:
    def AnimMotionEffect(self, Bone, MotionEffect, StaticMeshComponent, LocationOffset, RotationOffset,
            AnimationSequence, bHitSuccess, HitResult, Contexts, VFXScale, AudioVolume, AudioPitch):
        return motion(self, Bone, MotionEffect, StaticMeshComponent, LocationOffset, RotationOffset,
            AnimationSequence, bHitSuccess, HitResult, Contexts, VFXScale, AudioVolume, AudioPitch)
    def AfterDelay(self): cleanup(self)
    AfterDelay.override = AFTER


class LyraFootstepBlueprintFallbackProfile:
    def AnimMotionEffect(self, Bone, MotionEffect, StaticMeshComponent, LocationOffset, RotationOffset,
            AnimationSequence, bHitSuccess, HitResult, Contexts, VFXScale, AudioVolume, AudioPitch):
        evidence(self)["fallback_calls"] += 1
        return self.call_mixin_original("AnimMotionEffect", Bone, MotionEffect, StaticMeshComponent,
            LocationOffset, RotationOffset, AnimationSequence, bHitSuccess, HitResult, Contexts, VFXScale, AudioVolume, AudioPitch)
    def AfterDelay(self):
        evidence(self)["fallback_cleanup"] += 1; return self.call_mixin_original(AFTER)
    AfterDelay.override = AFTER
