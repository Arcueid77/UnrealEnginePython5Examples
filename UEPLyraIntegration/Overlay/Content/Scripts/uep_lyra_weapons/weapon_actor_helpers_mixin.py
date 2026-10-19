"""Retained B_Weapon helper policy; native trace/audio/material backends."""
import unreal_engine as ue
from unreal_engine.enums import ETraceTypeQuery, EDrawDebugTrace, EAttachLocation, ERelativeTransformSpace
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import trace_outputs, break_hit, native_outputs

CLASS = "/Game/Weapons/B_Weapon.B_Weapon_C"
FAKE = "Add Fake Projectile Data"


def library(name): return ue.find_class(name).get_cdo()


def evidence(actor):
    value = getattr(actor, "_uep_weapon_actor_helpers", None)
    if value is None:
        value = dict(fake_python=0, fake_fallback=0, traces=0, hits=0, audio_python=0, audio_fallback=0,
                     audio_spawns=0, audio_triggers=0, stencil_python=0, stencil_fallback=0,
                     primitive_queries=0, stencil_writes=0, colors_python=0, colors_fallback=0, team_applications=0)
        actor._uep_weapon_actor_helpers = value
    return value


def append(actor, name, value):
    values = list(actor.get_property(name))
    values.append(value)
    actor.set_property(name, values)


def fake_projectiles(actor, number, angle):
    counts = evidence(actor)
    counts["fake_python"] += 1
    math = library("KismetMathLibrary")
    for _ in range(max(int(number), 0)):
        mesh = actor.get_property("SkeletalMesh")
        transform = mesh.call_function("GetSocketTransform", "Muzzle", ERelativeTransformSpace.RTS_World) if valid(mesh) else ue.FTransform()
        start = native_outputs("KismetMathLibrary", "BreakTransform", math.call_function("BreakTransform", transform))["Location"]
        positions = list(actor.get_property("Impact Positions"))
        target = positions[0] if positions else ue.FVector()
        direction = math.call_function("Normal", math.call_function("Subtract_VectorVector", target, start), .0001)
        spread = math.call_function("RandomUnitVectorInConeInDegrees", direction, angle)
        end = math.call_function("Add_VectorVector", math.call_function("Multiply_VectorFloat", spread, 1000000.), start)
        hit, result = trace_outputs("LineTraceSingle", library("KismetSystemLibrary").call_function(
            "LineTraceSingle", WorldContextObject=actor, Start=start, End=end, TraceChannel=ETraceTypeQuery.TraceTypeQuery1,
            bTraceComplex=False, ActorsToIgnore=[], DrawDebugType=getattr(EDrawDebugTrace, "None"), bIgnoreSelf=True,
            TraceColor=ue.FLinearColor(1., 0., 0., 1.), TraceHitColor=ue.FLinearColor(0., 1., 0., 1.), DrawTime=5.))
        counts["traces"] += 1
        if hit:
            data = break_hit(result)
            # Original arrays are independent and appended in this order.
            append(actor, "ImpactSurfaceTypes", library("GameplayStatics").call_function("GetSurfaceType", result))
            append(actor, "Impact Positions", data["Location"])
            append(actor, "Impact Normals", data["Normal"])
            counts["hits"] += 1


def trigger_audio(actor, sound, target):
    counts = evidence(actor)
    counts["audio_python"] += 1
    component = actor.get_property("AudioComponent")
    if not valid(component):
        attach = target.call_function("GetComponentByClass", ue.find_class("SkeletalMeshComponent")) if valid(target) else None
        component = library("GameplayStatics").call_function("SpawnSoundAttached", Sound=sound, AttachToComponent=attach,
            AttachPointName="hand_r", Location=ue.FVector(), Rotation=ue.FRotator(), LocationType=EAttachLocation.KeepRelativeOffset,
            bStopWhenAttachedToDestroyed=False, VolumeMultiplier=1., PitchMultiplier=1., StartTime=0.,
            AttenuationSettings=None, ConcurrencySettings=None, bAutoDestroy=True)
        actor.set_property("AudioComponent", component)
        counts["audio_spawns"] += 1
    if valid(component):
        component.call_function("SetTriggerParameter", "Fire")
        counts["audio_triggers"] += 1


def stencil(actor, team):
    counts = evidence(actor)
    counts["stencil_python"] += 1
    owner = actor.get_property("OwnerAsPawn")
    local = bool(owner.call_function("IsLocallyControlled")) if valid(owner) else False
    # This weapon graph checks only local control, including a local bot.
    value = 0 if local else team
    components = library("LyraSystemStatics").call_function("FindComponentsByClass", actor, ue.find_class("PrimitiveComponent"), True)
    counts["primitive_queries"] += 1
    for component in components:
        component.call_function("SetCustomDepthStencilValue", value)
        counts["stencil_writes"] += 1


class LyraWeaponActorHelpersPythonProfile:
    def AddFakeProjectileData(self, NumerOfFakeProjectiles, ConeHalfAngleInDegrees):
        fake_projectiles(self, NumerOfFakeProjectiles, ConeHalfAngleInDegrees)
    AddFakeProjectileData.override = FAKE
    def TriggerFireAudio(self, Sound, Actor): trigger_audio(self, Sound, Actor)
    def UpdateCustomStencil(self, TeamId): stencil(self, TeamId)
    def UpdateTeamColors(self, TeamDisplayAsset):
        counts = evidence(self)
        counts["colors_python"] += 1
        if valid(TeamDisplayAsset) and self.get_property("ApplyTeamColorsToWeapon"):
            TeamDisplayAsset.call_function("ApplyToActor", self, True)
            counts["team_applications"] += 1


class LyraWeaponActorHelpersBlueprintFallbackProfile:
    def AddFakeProjectileData(self, NumerOfFakeProjectiles, ConeHalfAngleInDegrees):
        evidence(self)["fake_fallback"] += 1
        return self.call_mixin_original(FAKE, NumerOfFakeProjectiles, ConeHalfAngleInDegrees)
    AddFakeProjectileData.override = FAKE
    def TriggerFireAudio(self, Sound, Actor):
        evidence(self)["audio_fallback"] += 1
        return self.call_mixin_original("TriggerFireAudio", Sound, Actor)
    def UpdateCustomStencil(self, TeamId):
        evidence(self)["stencil_fallback"] += 1
        return self.call_mixin_original("UpdateCustomStencil", TeamId)
    def UpdateTeamColors(self, TeamDisplayAsset):
        evidence(self)["colors_fallback"] += 1
        return self.call_mixin_original("UpdateTeamColors", TeamDisplayAsset)
