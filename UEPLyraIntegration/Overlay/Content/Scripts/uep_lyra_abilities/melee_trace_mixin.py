"""Original Melee authority decisions; native query/GAS/root-motion/Cue backends."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayTagContainer, GameplayEffectContextHandle, HitResult
from unreal_engine.enums import EObjectTypeQuery, ETraceTypeQuery, EDrawDebugTrace, ERootMotionFinishVelocityMode, ELyraTeamComparison
from .melee_activation_mixin import LyraMeleeActivationPythonProfile, LyraMeleeActivationBlueprintFallbackProfile, TRACE

_stats = dict(queries=0, fallback_queries=0, misses=0, invalid_asc=0, nondifferent_team=0, occluded=0, root_tasks=0, effects=0, cues=0)


def snapshot(): return copy.deepcopy(_stats)
def library(name): return ue.find_class(name).get_cdo()
def path(value): return value.get_path_name() if value is not None else None
def vector(value): return [float(value.x), float(value.y), float(value.z)]
def native_outputs(cls, method, value):
    parameters = ue.describe_function(ue.find_class(cls), method)["parameters"]
    # Match the existing UEP call wrapper: ReturnParm first; const reference
    # arrays also appear in its out tuple. Do not assume only OutHit survives.
    returns = [item for item in parameters if int(item["flags"]) & 0x400]
    outputs = [item for item in parameters if int(item["flags"]) & 0x100 and not int(item["flags"]) & 0x400 and
        (item["type"] == "TArray" or item["type"].startswith("TArray<") or not int(item["flags"]) & 0x2)]
    names = [item["name"] for item in returns+outputs]
    if outputs:
        if not isinstance(value, tuple) or len(value) != len(names): raise RuntimeError("native output shape differs: "+method+" "+str(names)+" actual="+str(len(value) if isinstance(value, tuple) else type(value).__name__))
        return dict(zip(names, value))
    if len(returns) == 1: return {names[0]: value}
    if names or value is not None: raise RuntimeError("native output signature differs: "+method)
    return {}


def trace_outputs(method, value):
    fields = native_outputs("KismetSystemLibrary", method, value)
    if type(fields.get("ReturnValue")) is not bool or "OutHit" not in fields: raise RuntimeError("native trace output ABI differs")
    return fields["ReturnValue"], fields["OutHit"]
def break_hit(hit):
    result = library("GameplayStatics").call_function("BreakHitResult", hit)
    return native_outputs("GameplayStatics", "BreakHitResult", result)


def trace(ability):
    _stats["queries"] += 1
    actor = ability.call_function("GetLyraCharacterFromActorInfo"); math = library("KismetMathLibrary")
    start = actor.get_property("Mesh").call_function("GetSocketLocation", "hand_r")
    facing = actor.call_function("GetActorForwardVector"); distance = float(ability.get_property("Distance"))
    scale = math.call_function("MakeVector", distance, distance, distance)
    end = math.call_function("Add_VectorVector", math.call_function("Multiply_VectorVector", facing, scale), start)
    data = dict(start=vector(start), end=vector(end), target=None, outcome="query")
    ability._uep_melee_trace_last = data
    options = dict(WorldContextObject=ability, bTraceComplex=False, DrawDebugType=getattr(EDrawDebugTrace, "None"), bIgnoreSelf=True,
        TraceColor=ue.FLinearColor(1., 0., 0., 1.), TraceHitColor=ue.FLinearColor(0., 1., 0., 1.), DrawTime=5.)
    hit, result = trace_outputs("CapsuleTraceSingleForObjects", library("KismetSystemLibrary").call_function("CapsuleTraceSingleForObjects", Start=start, End=end,
        Radius=float(ability.get_property("Radius")), HalfHeight=float(ability.get_property("Half Height")),
        ObjectTypes=[EObjectTypeQuery.ObjectTypeQuery3], ActorsToIgnore=[actor], **options))
    if not hit: _stats["misses"] += 1; data["outcome"] = "miss"; return
    fields = break_hit(result); target = fields["HitActor"]; data["target"] = path(target)
    target_asc = library("AbilitySystemBlueprintLibrary").call_function("GetAbilitySystemComponent", target)
    if not library("KismetSystemLibrary").call_function("IsValid", target_asc):
        _stats["invalid_asc"] += 1; data["outcome"] = "invalid-asc"; return
    teams = library("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem", ability, ue.find_class("LyraTeamSubsystem"))
    comparison = teams.call_function("CompareTeams", target, actor)
    if not isinstance(comparison, tuple) or len(comparison) != 3: raise RuntimeError("native team comparison must return enum/two team IDs")
    data["team_comparison"] = int(comparison[0]); data["team_ids"] = [int(value) for value in comparison[1:]]
    if comparison[0] != ELyraTeamComparison.DifferentTeams:
        _stats["nondifferent_team"] += 1; data["outcome"] = "not-different-teams"; return
    blocked, _ = trace_outputs("LineTraceSingle", library("KismetSystemLibrary").call_function("LineTraceSingle", Start=start, End=fields["ImpactPoint"],
        TraceChannel=ETraceTypeQuery.TraceTypeQuery4, ActorsToIgnore=[target, actor], **options))
    if blocked: _stats["occluded"] += 1; data["outcome"] = "occluded"; return
    ratio = math.call_function("NormalizeToRange", float(fields["Distance"]), 0., distance)
    strength = math.call_function("Multiply_DoubleDouble", float(ability.get_property("Strength")), ratio)
    root = library("AbilityTask_ApplyRootMotionConstantForce").call_function("ApplyRootMotionConstantForce", OwningAbility=ability,
        TaskInstanceName="None", WorldDirection=facing, Strength=strength, Duration=float(ability.get_property("Duration")), bIsAdditive=True,
        StrengthOverTime=None, VelocityOnFinishMode=ERootMotionFinishVelocityMode.MaintainLastRootMotionVelocity,
        SetVelocityOnFinish=math.call_function("MakeVector", 0., 0., 0.), ClampVelocityOnFinish=1000., bEnableGravity=True)
    root.call_function("ReadyForActivation"); _stats["root_tasks"] += 1
    source = ability.call_function("GetLyraAbilitySystemComponentFromActorInfo")
    context = source.call_function("MakeEffectContext"); ability.set_property("Gameplay Effect Control Handle Struct", context)
    # Original pin is deliberately unconnected: preserve its empty hit result.
    library("AbilitySystemBlueprintLibrary").call_function("EffectContextAddHitResult", ability.get_property("Gameplay Effect Control Handle Struct"), HitResult(), True)
    source.call_function("BP_ApplyGameplayEffectToTarget", ue.load_class("/ShooterCore/Weapons/GE_Damage_Melee.GE_Damage_Melee_C"), target_asc, 1., ability.get_property("Gameplay Effect Control Handle Struct"))
    _stats["effects"] += 1
    params = library("AbilitySystemBlueprintLibrary").call_function("MakeGameplayCueParameters", NormalizedMagnitude=0., RawMagnitude=0.,
        EffectContext=GameplayEffectContextHandle(), MatchedTagName=GameplayTag(), OriginalTag=GameplayTag(),
        AggregatedSourceTags=GameplayTagContainer(), AggregatedTargetTags=GameplayTagContainer(),
        Location=math.call_function("MakeVector", 0., 0., 0.), Normal=math.call_function("MakeVector", 0., 0., 0.),
        Instigator=None, EffectCauser=None, SourceObject=None, PhysicalMaterial=None, GameplayEffectLevel=1, AbilityLevel=1,
        TargetAttachComponent=None, bReplicateLocationWhenUsingMinimalRepProxy=False)
    ability.call_function("K2_ExecuteGameplayCueWithParams", GameplayTag(TagName="GameplayCue.Weapon.Melee.Hit"), params)
    _stats["cues"] += 1; data.update(outcome="applied", native_strength=float(strength))


class LyraMeleeTracePythonProfile:
    def __init__(self): LyraMeleeActivationPythonProfile.__init__(self)
    SelectHitMontage = LyraMeleeActivationPythonProfile.__dict__["SelectHitMontage"]
    Activate = LyraMeleeActivationPythonProfile.__dict__["Activate"]
    NativeEnded = LyraMeleeActivationPythonProfile.__dict__["NativeEnded"]
    def AuthorityTrace(self): trace(self)
    AuthorityTrace.override = TRACE
    def __uep_mixin_teardown__(self): LyraMeleeActivationPythonProfile.__uep_mixin_teardown__(self)


class LyraMeleeTraceBlueprintFallbackProfile:
    def __init__(self): LyraMeleeActivationBlueprintFallbackProfile.__init__(self)
    SelectHitMontage = LyraMeleeActivationBlueprintFallbackProfile.__dict__["SelectHitMontage"]
    Activate = LyraMeleeActivationBlueprintFallbackProfile.__dict__["Activate"]
    NativeEnded = LyraMeleeActivationBlueprintFallbackProfile.__dict__["NativeEnded"]
    def AuthorityTrace(self): _stats["fallback_queries"] += 1; return self.call_mixin_original(TRACE)
    AuthorityTrace.override = TRACE
    def __uep_mixin_teardown__(self): LyraMeleeActivationBlueprintFallbackProfile.__uep_mixin_teardown__(self)
