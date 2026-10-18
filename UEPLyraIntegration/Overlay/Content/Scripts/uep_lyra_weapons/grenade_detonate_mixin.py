"""Grenade explosion decisions behind the retained reliable RPC/DoOnce gate.

Physics queries, GameplayCue, damage execution and weak Niagara delegates stay
native. Preserve the source graph's hit-distance/radius level (including its
increasing curve), and its choice of overlap Pawn rather than trace-hit Actor.
"""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayTagContainer, GameplayEffectContextHandle
from unreal_engine.enums import EObjectTypeQuery, ETraceTypeQuery, EDrawDebugTrace
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs, break_hit
from .grenade_hit_mixin import LyraGrenadeHitPythonProfile as HitPython, LyraGrenadeHitBlueprintFallbackProfile as HitBlueprint

BODY = "UEPGrenadeDetonateBody"
BIND = "UEPGrenadeBindTrailFinished"
CONTEXT = "Gameplay Effect Context Handle Struct"
DAMAGE = "/ShooterCore/Weapons/Grenade/GE_Damage_Grenade.GE_Damage_Grenade_C"


def library(name):
    return ue.find_class(name).get_cdo()


def evidence(actor):
    row = getattr(actor, "_uep_grenade_detonate", None)
    if row is None:
        row = dict(python_bodies=0, fallback_bodies=0, cues=0, hidden=0,
                   movement_stops=0, authority_queries=0, overlaps=0,
                   traces=0, effects=0, trail_bindings=0, destroys=0)
        actor._uep_grenade_detonate = row
    return row


def detonate(actor):
    counts = evidence(actor)
    counts["python_bodies"] += 1
    abilities, system = library("AbilitySystemBlueprintLibrary"), library("KismetSystemLibrary")
    location = actor.get_actor_location()
    parameters = abilities.call_function(
        "MakeGameplayCueParameters", NormalizedMagnitude=0., RawMagnitude=0.,
        EffectContext=GameplayEffectContextHandle(), MatchedTagName=GameplayTag(),
        OriginalTag=GameplayTag(), AggregatedSourceTags=GameplayTagContainer(),
        AggregatedTargetTags=GameplayTagContainer(), Location=location, Normal=ue.FVector(),
        Instigator=None, EffectCauser=None, SourceObject=None, PhysicalMaterial=None,
        GameplayEffectLevel=1, AbilityLevel=1, TargetAttachComponent=None,
        bReplicateLocationWhenUsingMinimalRepProxy=False)
    library("GameplayCueFunctionLibrary").call_function(
        "ExecuteGameplayCueOnActor", actor, actor.get_property("Gameplay Tag"), parameters)
    counts["cues"] += 1
    mesh = actor.get_property("Mesh")
    if valid(mesh):
        mesh.call_function("SetHiddenInGame", True, False)
        counts["hidden"] += 1
    movement = actor.get_property("ProjectileMovement")
    if valid(movement):
        movement.call_function("Deactivate")
        counts["movement_stops"] += 1
    counts["authority_queries"] += 1
    if not actor.call_function("HasAuthority"):
        return  # Original Remote pin has no cleanup or damage continuation.
    outputs = native_outputs("KismetSystemLibrary", "SphereOverlapActors", system.call_function(
        "SphereOverlapActors", WorldContextObject=actor, SpherePos=actor.get_actor_location(),
        SphereRadius=actor.get_property("Radius"), ObjectTypes=[EObjectTypeQuery.ObjectTypeQuery3],
        ActorClassFilter=ue.find_class("Pawn"), ActorsToIgnore=[]))
    counts["overlaps"] += 1
    if outputs["ReturnValue"]:
        source = abilities.call_function("GetAbilitySystemComponent", actor.get_property("Instigator"))
        context = source.call_function("MakeEffectContext") if valid(source) else GameplayEffectContextHandle()
        actor.set_property(CONTEXT, context)
        pawns = list(outputs["OutActors"])
        for pawn in pawns:
            ignored = [other for other in pawns if other != pawn]
            actor.set_property("IgnoreActors", ignored)
            hit = native_outputs("KismetSystemLibrary", "LineTraceSingle", system.call_function(
                "LineTraceSingle", WorldContextObject=actor, Start=actor.get_actor_location(),
                End=pawn.get_actor_location(), TraceChannel=ETraceTypeQuery.TraceTypeQuery5,
                bTraceComplex=True, ActorsToIgnore=ignored, DrawDebugType=getattr(EDrawDebugTrace, "None"),
                bIgnoreSelf=True, TraceColor=ue.FLinearColor(1., 0., 0., 1.),
                TraceHitColor=ue.FLinearColor(0., 1., 0., 1.), DrawTime=25.))
            counts["traces"] += 1
            if not hit["ReturnValue"]:
                continue
            abilities.call_function("EffectContextAddHitResult", actor.get_property(CONTEXT), hit["OutHit"], True)
            # The original graph uses the selected overlap Pawn, even when the
            # trace hits an occluder. Do not silently change that gameplay rule.
            target = abilities.call_function("GetAbilitySystemComponent", pawn)
            source = abilities.call_function("GetAbilitySystemComponent", actor.get_property("Instigator"))
            math = library("KismetMathLibrary")
            ratio = math.call_function("Divide_DoubleDouble", break_hit(hit["OutHit"])["Distance"], actor.get_property("Radius"))
            level = math.call_function("FClamp", ratio, .1, 1.)
            if valid(source):
                source.call_function("BP_ApplyGameplayEffectToTarget", ue.load_class(DAMAGE), target, level, actor.get_property(CONTEXT))
                counts["effects"] += 1
    if valid(actor.get_property("NS_Trail")):
        # Existing native AddDelegate binds the Actor UFunction weakly. No
        # Python closure, duplicate delegate, replacement Niagara system or
        # synthetic completion is introduced.
        actor.call_function(BIND)
        counts["trail_bindings"] += 1
    else:
        counts["destroys"] += 1
        actor.call_function("K2_DestroyActor")


class LyraGrenadeDetonatePythonProfile:
    SetupVFX = HitPython.SetupVFX
    PostLaunchCleanup = HitPython.PostLaunchCleanup
    TeleportGrenade = HitPython.TeleportGrenade
    DestroyGrenade = HitPython.DestroyGrenade
    ReceiveBeginPlay = HitPython.ReceiveBeginPlay
    ReceiveHit = HitPython.ReceiveHit

    def DetonateBody(self):
        detonate(self)
    DetonateBody.override = BODY


class LyraGrenadeDetonateBlueprintFallbackProfile:
    SetupVFX = HitBlueprint.SetupVFX
    PostLaunchCleanup = HitBlueprint.PostLaunchCleanup
    TeleportGrenade = HitBlueprint.TeleportGrenade
    DestroyGrenade = HitBlueprint.DestroyGrenade
    ReceiveBeginPlay = HitBlueprint.ReceiveBeginPlay
    ReceiveHit = HitBlueprint.ReceiveHit

    def DetonateBody(self):
        evidence(self)["fallback_bodies"] += 1
        return self.call_mixin_original(BODY)
    DetonateBody.override = BODY
