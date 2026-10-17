"""Native API-order/parameter models only; actual Chaos proof is separate."""
import importlib.util
import math
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import test_character_equipment_hide_mixin as hide_models


def vec(x=0., y=0., z=0.): return types.SimpleNamespace(x=x, y=y, z=z)


class CharacterRagdollPolicyModels(unittest.TestCase):
    def setUp(self):
        setup = hide_models.CharacterEquipmentHidePolicyModels(); setup.setUp(); self.parent = setup.module
        self.calls = []; self.velocity = vec(3., 4., 0.)
        self.mesh = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        self.movement = types.SimpleNamespace(call_function=lambda name: self.velocity)
        self.fields = dict(Mesh=self.mesh, CharacterMovement=self.movement, RagdollImpulseBone="Pelvis", RagdollImpulseStrength=500.)
        self.actor = types.SimpleNamespace(get_property=lambda name: self.fields[name], call_mixin_original=lambda *args: self.calls.append(("original",)+args))
        self.math_calls = []
        def native(name, a, b):
            self.math_calls.append((name, b))
            if name == "Normal":
                square = a.x*a.x+a.y*a.y+a.z*a.z
                return vec(a.x/math.sqrt(square), a.y/math.sqrt(square), a.z/math.sqrt(square)) if square >= b else vec()
            if name == "Multiply_VectorFloat": return vec(a.x*b, a.y*b, a.z*b)
            if name == "Add_VectorVector": return vec(a.x+b.x, a.y+b.y, a.z+b.z)
            raise AssertionError(name)
        native_math = types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=native))
        engine = types.ModuleType("unreal_engine"); engine.find_class = lambda name: native_math; engine.FVector = vec
        native_module = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native_module.valid = lambda value: value is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/ragdoll_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._ragdoll_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"uep_lyra_characters.equipment_hide_mixin": self.parent, "unreal_engine": engine, native_module.__name__: native_module}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterRagdollPythonProfile, self.module.LyraCharacterRagdollBlueprintFallbackProfile
    def start(self): self.python.Ragdoll(self.actor)
    def test_exact_three_native_mutations_in_original_order(self): self.start(); self.assertEqual([value[0] for value in self.calls], ["SetCollisionProfileName", "SetAllBodiesBelowSimulatePhysics", "AddImpulse"])
    def test_original_collision_profile_updates_overlaps(self): self.start(); self.assertEqual(self.calls[0], ("SetCollisionProfileName", "Ragdoll", True))
    def test_original_bone_include_self_true(self): self.start(); self.assertEqual(self.calls[1], ("SetAllBodiesBelowSimulatePhysics", "Pelvis", True, True))
    def test_native_additive_velocity_change_not_mass_impulse(self): self.start(); self.assertEqual(self.calls[2][2:], ("Pelvis", True))
    def test_original_velocity_plus_normalized_strength_formula(self): self.start(); self.assertEqual(self.module.evidence(self.actor)["last_call"]["impulse"], [303., 404., 0.])
    def test_zero_velocity_keeps_zero_impulse(self): self.velocity = vec(); self.start(); self.assertEqual(self.module.evidence(self.actor)["last_call"]["impulse"], [0., 0., 0.])
    def test_zero_strength_keeps_original_velocity(self): self.fields["RagdollImpulseStrength"] = 0.; self.start(); self.assertEqual(self.module.evidence(self.actor)["last_call"]["impulse"], [3., 4., 0.])
    def test_negative_strength_not_clamped(self): self.fields["RagdollImpulseStrength"] = -5.; self.start(); self.assertEqual(self.module.evidence(self.actor)["last_call"]["impulse"], [0., 0., 0.])
    def test_original_native_normal_tolerance(self): self.start(); self.assertEqual(self.math_calls[0], ("Normal", .0001))
    def test_tiny_velocity_uses_native_safe_normal_noop(self): self.velocity = vec(.00001, 0., 0.); self.start(); self.assertEqual(self.module.evidence(self.actor)["last_call"]["impulse"], [.00001, 0., 0.])
    def test_repeated_requests_preserve_all_native_calls(self): self.start(); self.start(); self.assertEqual(len(self.calls), 6)
    def test_missing_mesh_quiet_like_bp_null_receiver_effect(self): self.fields["Mesh"] = None; self.start(); self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["missing_mesh_noops"], 1)
    def test_no_original_bp_on_python_path(self): self.start(); self.assertNotIn("original", [value[0] for value in self.calls])
    def test_fallback_exact_inherited_original(self): self.fallback.Ragdoll(self.actor); self.assertEqual(self.calls, [("original", "Ragdoll")])
    def test_accepted_twenty_seven_methods_raw_aliases(self):
        for name, method in self.parent.LyraCharacterEquipmentHidePythonProfile.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], method)
    def test_no_movement_disable_or_authority_branch_added(self):
        self.start(); self.assertEqual(len(self.calls), 3); self.assertNotIn("HasAuthority", [value[0] for value in self.calls])
    def test_fixture_does_not_call_unreflected_physics_asset_getter(self):
        root = Path(__file__).resolve().parents[1]
        for relative in ("Tools/generate_character_ragdoll_probe.py", "Overlay/Content/Scripts/uep_lyra_characters/ragdoll_observation.py"):
            self.assertNotIn('call_function("GetPhysicsAsset"', (root/relative).read_text(encoding="utf-8"))
