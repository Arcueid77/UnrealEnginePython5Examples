"""Hero BP orchestration only: Chaos, skeletal bodies and animation stay native."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from . import equipment_hide_mixin as hiding


def vector(value): return [float(value.x), float(value.y), float(value.z)]


def evidence(actor):
    value = getattr(actor, "_uep_character_ragdoll", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, collision_calls=0, simulation_calls=0, impulse_calls=0,
            missing_mesh_noops=0, trace=[], last_call=None)
        actor._uep_character_ragdoll = value
    return value


class LyraCharacterRagdollPythonProfile:
    def Ragdoll(self):
        counts = evidence(self); counts["python_calls"] += 1
        mesh = self.get_property("Mesh")
        if not valid(mesh): counts["missing_mesh_noops"] += 1; return
        bone = self.get_property("RagdollImpulseBone"); strength = float(self.get_property("RagdollImpulseStrength"))
        mesh.call_function("SetCollisionProfileName", "Ragdoll", True)
        counts["collision_calls"] += 1; counts["trace"].append("collision")
        mesh.call_function("SetAllBodiesBelowSimulatePhysics", bone, True, True)
        counts["simulation_calls"] += 1; counts["trace"].append("simulation")
        movement = self.get_property("CharacterMovement")
        velocity = movement.call_function("GetLastUpdateVelocity") if valid(movement) else ue.FVector(0., 0., 0.)
        math = ue.find_class("KismetMathLibrary").get_cdo()
        direction = math.call_function("Normal", velocity, .0001)
        impulse = math.call_function("Add_VectorVector", velocity, math.call_function("Multiply_VectorFloat", direction, strength))
        mesh.call_function("AddImpulse", impulse, bone, True)
        counts["impulse_calls"] += 1; counts["trace"].append("impulse")
        counts["last_call"] = dict(bone=str(bone), strength=strength, velocity=vector(velocity), impulse=vector(impulse),
            collision_profile="Ragdoll", include_self=True, velocity_change=True, normalize_tolerance=.0001)


class LyraCharacterRagdollBlueprintFallbackProfile:
    def Ragdoll(self):
        evidence(self)["fallback_calls"] += 1; self.call_mixin_original("Ragdoll")


for profile, parent in ((LyraCharacterRagdollPythonProfile, hiding.LyraCharacterEquipmentHidePythonProfile),
                        (LyraCharacterRagdollBlueprintFallbackProfile, hiding.LyraCharacterEquipmentHideBlueprintFallbackProfile)):
    for name, method in parent.__dict__.items():
        if not name.startswith("__"): setattr(profile, name, method)
