"""Launcher BP decisions; native collision, CharacterMovement and RPC remain."""
import copy
import math
import unreal_engine as ue
from unreal_engine import FVector
from .effect_pad_mixin import valid

NAMES = ("B_Launcher", "B_Launcher_Push", "B_Launcher_Up")
CLASSES = tuple("/ShooterCore/Blueprint/"+name+"."+name+"_C" for name in NAMES)
PREFIX = "UEPDispatchLauncher"
_stats = dict(constructions=0, push_constructions=0, begins=0, parent_overlaps=0,
              push_overlaps=0, up_overlaps=0, launches=0, rejected=0, cues=0, errors=[])

def snapshot():
    return copy.deepcopy(_stats)

def library(name):
    return ue.find_class(name).get_cdo()

def construct(actor):
    material = actor.LauncherMesh.call_function("GetMaterial", 0)
    mid = actor.LauncherMesh.call_function("CreateDynamicMaterialInstance", 0, material, "None")
    mid.call_function("SetScalarParameterValue", "Intensity", actor.get_property("Glow Intensity"))
    # Original MaterialParameterInfo is global, index -1, name Color.
    mid.call_function("SetVectorParameterValue", "Color", actor.get_property("Light Color"))
    actor.PointLight.call_function("SetLightColor", actor.get_property("Light Color"), True)
    actor.PointLight.call_function("SetIntensity", actor.get_property("Light Intensity"))
    actor.PointLight.call_function("SetAttenuationRadius", actor.get_property("Light Attenuation"))
    actor.Sphere.call_function("SetSphereRadius", actor.SphereRadius, True)
    _stats["constructions"] += 1

def clamp(value, low, high):
    return max(low, min(high, value))

def construct_push(actor):
    # The retained native parent Construction call has already executed.
    target = actor.Target
    # Original Y Clamp has BOTH literal bounds zero (unlike X). Preserve the
    # authored behavior rather than silently correcting the official BP.
    actor.set_property("Target", FVector(clamp(target.x, -actor.XYBounds, actor.XYBounds),
        0.0, clamp(target.z, -actor.ZBounds, actor.ZBounds)))
    _stats["push_constructions"] += 1

def overlap(actor, kind):
    _stats[kind+"_overlaps"] += 1
    if kind == "parent":
        return True  # Original base Overlap returns the constant true.
    pawn = actor.OverlappingPawn
    if not valid(pawn):
        _stats["rejected"] += 1
        return False
    velocity = pawn.CharacterMovement.call_function("GetLastUpdateVelocity")
    if actor.get_property("Do Not Activate on Fall Entry") and velocity.z < actor.MinimumVerticalVelocityAllowed:
        _stats["rejected"] += 1
        return False
    forward = pawn.call_function("GetActorForwardVector")
    if kind == "up":
        launch = FVector(forward.x, forward.y, actor.UpOverride)
    elif actor.get_property("Use Target"):
        target = actor.Target
        speed = math.hypot(target.x, target.y)*2.1
        xyz = (forward.x*speed, forward.y*speed, clamp(target.z*2.0, 250.0, 850.0))
        length = math.sqrt(sum(value*value for value in xyz))
        scale = 12000.0/length if length > 12000.0 else 1.0
        launch = FVector(*(value*scale for value in xyz))
    else:
        launch = FVector(forward.x*actor.Multiplier, forward.y*actor.Multiplier, actor.UpOverride*actor.Multiplier)
    pawn.call_function("LaunchCharacter", launch, False, kind == "up")
    _stats["launches"] += 1
    return True  # Both children's retained local return defaults are true.

def begin(actor, other):
    _stats["begins"] += 1
    if not valid(other) or not other.is_a(ue.find_class("Character")):
        return
    actor.set_property("OverlappingPawn", other)  # Also assigned on clients in BP.
    if not actor.call_function("HasAuthority"):
        return
    if valid(library("AIBlueprintHelperLibrary").call_function("GetAIController", other)):
        return
    # BP's output named Return is an out parameter, NOT CPF_ReturnParm, and
    # may be packed. Use the existing typed output transport, not legacy
    # generic-call tuple truthiness or raw packed-bool buffer conversion.
    result = ue.call_function_by_class(actor, actor.get_class(), "Overlap", {})["Return"]
    if not isinstance(result, bool):
        raise RuntimeError("launcher Overlap requires one boolean output")
    if result:
        # Do not replace/reflag the existing NetMulticast UFunction.
        actor.call_function("Activate VFX")

def cue(actor):
    if valid(actor.OverlappingPawn):
        # Location inside this struct is FVector_NetQuantize10, not FVector.
        # Let the retained native constructor perform that typed conversion.
        parameters = library("AbilitySystemBlueprintLibrary").call_function("MakeGameplayCueParameters",
            Location=actor.get_actor_location(), EffectCauser=actor, GameplayEffectLevel=1, AbilityLevel=1)
        library("GameplayCueFunctionLibrary").call_function("ExecuteGameplayCueOnActor", actor.OverlappingPawn,
            actor.get_property("Gameplay Tag"), parameters)
        _stats["cues"] += 1

def guarded(function, *args):
    try:
        return function(*args)
    except Exception as error:
        _stats["errors"].append(str(error))
        raise

class LyraLauncherPythonProfile:
    def Construction(self):
        guarded(construct, self)
        return False
    Construction.override = PREFIX+"Construction"

    def PushConstruction(self):
        guarded(construct_push, self)
        return False
    PushConstruction.override = PREFIX+"PushConstruction"

    def Begin(self, OtherActor):
        guarded(begin, self, OtherActor)
        return False
    Begin.override = PREFIX+"Begin"

    def Cue(self):
        guarded(cue, self)
        return False
    Cue.override = PREFIX+"Cue"

    def ParentOverlap(self):
        return int(guarded(overlap, self, "parent"))
    ParentOverlap.override = PREFIX+"ParentOverlap"

    def PushOverlap(self):
        return int(guarded(overlap, self, "push"))
    PushOverlap.override = PREFIX+"PushOverlap"

    def UpOverlap(self):
        return int(guarded(overlap, self, "up"))
    UpOverlap.override = PREFIX+"UpOverlap"

class LyraLauncherBlueprintFallbackProfile:
    def Construction(self):
        return self.call_mixin_original(PREFIX+"Construction")
    Construction.override = PREFIX+"Construction"

    def PushConstruction(self):
        return self.call_mixin_original(PREFIX+"PushConstruction")
    PushConstruction.override = PREFIX+"PushConstruction"

    def Begin(self, OtherActor):
        return self.call_mixin_original(PREFIX+"Begin", OtherActor)
    Begin.override = PREFIX+"Begin"

    def Cue(self):
        return self.call_mixin_original(PREFIX+"Cue")
    Cue.override = PREFIX+"Cue"

    def ParentOverlap(self):
        return self.call_mixin_original(PREFIX+"ParentOverlap")
    ParentOverlap.override = PREFIX+"ParentOverlap"

    def PushOverlap(self):
        return self.call_mixin_original(PREFIX+"PushOverlap")
    PushOverlap.override = PREFIX+"PushOverlap"

    def UpOverlap(self):
        return self.call_mixin_original(PREFIX+"UpOverlap")
    UpOverlap.override = PREFIX+"UpOverlap"
