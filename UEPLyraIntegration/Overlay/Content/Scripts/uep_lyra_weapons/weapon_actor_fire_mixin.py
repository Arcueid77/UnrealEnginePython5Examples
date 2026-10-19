"""Original weapon Fire orchestration; native FX Actors and render backends."""
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod, ESpawnActorScaleMethod, EAttachmentRule
from uep_lyra_world.effect_pad_mixin import valid
from .weapon_actor_helpers_mixin import LyraWeaponActorHelpersPythonProfile as HelpersPython, LyraWeaponActorHelpersBlueprintFallbackProfile as HelpersBlueprint

STAGES = (("WeaponFire", "/Game/Effects/Blueprints/B_WeaponFire.B_WeaponFire_C", "Fire"),
          ("Weapon Impacts", "/Game/Effects/Blueprints/B_WeaponImpacts.B_WeaponImpacts_C", "Fire"),
          ("Weapon Decals", "/Game/Effects/Blueprints/B_WeaponDecals.B_WeaponDecals_C", "fire"))


def evidence(actor):
    value = getattr(actor, "_uep_weapon_actor_fire", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, fake_calls=0, spawns=0, attachments=0, fx_calls=0, order=[])
        actor._uep_weapon_actor_fire = value
    return value


def fire(actor, positions, normals, surfaces):
    counts = evidence(actor)
    counts["python_calls"] += 1
    actor.set_property("Impact Positions", positions)
    actor.set_property("Impact Normals", normals)
    actor.set_property("ImpactSurfaceTypes", surfaces)
    mesh = actor.get_property("SkeletalMesh")
    actor.set_property("MuzzlePosition", mesh.call_function("GetSocketLocation", "Muzzle") if valid(mesh) else ue.FVector())
    if actor.get_property("NeedsFakeProjectileData"):
        actor.call_function("Add Fake Projectile Data", actor.get_property("Numer Of Fake Projectiles"), 5.)
        counts["fake_calls"] += 1
    for index, (field, cls_path, entry) in enumerate(STAGES):
        target = actor.get_property(field)
        if not valid(target):
            transform = ue.FTransform(ue.FVector(), ue.FRotator(), ue.FVector(1.,1.,1.))
            scale = ESpawnActorScaleMethod.OverrideRootScale
            statics = ue.find_class("GameplayStatics").get_cdo()
            target = statics.call_function("BeginDeferredActorSpawnFromClass", actor, ue.load_class(cls_path), transform,
                ESpawnActorCollisionHandlingMethod.Undefined, None, scale)
            if valid(target):
                if index == 0:
                    target.set_property("Skeletal Mesh Component", mesh)
                    for name in ("Enable Shell Eject", "Enable Muzzle Flash", "Enable Tracer"): target.set_property(name, True)
                    for name in ("Shell Eject System", "Muzzle Flash System", "Tracer System", "Shell Eject Mesh"):
                        target.set_property(name, actor.get_property(name))
                elif index == 1:
                    target.set_property("Distance Threshold", 500.)
                statics.call_function("FinishSpawningActor", target, transform, scale)
                counts["spawns"] += 1
            actor.set_property(field, target)
            if valid(target):
                target.call_function("K2_AttachToComponent", Parent=mesh, SocketName="None",
                    LocationRule=EAttachmentRule.KeepRelative, RotationRule=EAttachmentRule.KeepRelative,
                    ScaleRule=EAttachmentRule.KeepRelative, bWeldSimulatedBodies=True)
                counts["attachments"] += 1
        if not valid(target): continue
        target.set_property("ImpactPositions", actor.get_property("Impact Positions"))
        target.set_property("ImpactNormals", actor.get_property("Impact Normals"))
        target.set_property("Impact Surface Types" if index == 2 else "ImpactSurfaceTypes", actor.get_property("ImpactSurfaceTypes"))
        if index == 1: target.set_property("MuzzlePosition", actor.get_property("MuzzlePosition"))
        counts["order"].append(field)
        counts["order"] = counts["order"][-24:]
        target.call_function(entry)
        counts["fx_calls"] += 1


class LyraWeaponActorFirePythonProfile:
    AddFakeProjectileData = HelpersPython.AddFakeProjectileData
    TriggerFireAudio = HelpersPython.TriggerFireAudio
    UpdateCustomStencil = HelpersPython.UpdateCustomStencil
    UpdateTeamColors = HelpersPython.UpdateTeamColors
    def Fire(self, ImpactPositions, ImpactNormals, ImpactSurfaceTypes): fire(self, ImpactPositions, ImpactNormals, ImpactSurfaceTypes)


class LyraWeaponActorFireBlueprintFallbackProfile:
    AddFakeProjectileData = HelpersBlueprint.AddFakeProjectileData
    TriggerFireAudio = HelpersBlueprint.TriggerFireAudio
    UpdateCustomStencil = HelpersBlueprint.UpdateCustomStencil
    UpdateTeamColors = HelpersBlueprint.UpdateTeamColors
    def Fire(self, ImpactPositions, ImpactNormals, ImpactSurfaceTypes):
        evidence(self)["fallback_calls"] += 1
        return self.call_mixin_original("Fire", ImpactPositions, ImpactNormals, ImpactSurfaceTypes)
