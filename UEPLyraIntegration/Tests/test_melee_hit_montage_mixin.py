"""Original dot/range/strict-zero policy models; no native acceptance claim."""
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

with patch.dict(sys.modules, {"unreal_engine": types.ModuleType("unreal_engine")}):
    policy = importlib.import_module("uep_lyra_abilities.melee_hit_montage_mixin")


class Actor:
    def __init__(self): self.calls = []
    def call_function(self, name):
        self.calls.append(name); return (1., 0., 0.) if name == "GetActorForwardVector" else (0., 1., 0.)


class Ability:
    def __init__(self): self.originals = []
    def call_mixin_original(self, name, *args): self.originals.append((name, args)); return ("native-original",)


class MeleeHitMontagePolicyModels(unittest.TestCase):
    def setUp(self):
        self.ability, self.actor, self.calls = Ability(), Actor(), []
        def native(name, *args):
            self.calls.append((name, args))
            if name == "Dot_VectorVector": return sum(a*b for a, b in zip(*args))
            if name == "InRange_FloatFloat": return args[1] <= args[0] <= args[2]
            raise AssertionError(name)
        library = types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=native))
        self.patcher = patch.object(policy, "ue", types.SimpleNamespace(find_class=lambda name: library if name == "KismetMathLibrary" else name, load_object=lambda cls, path: path))
        self.patcher.start(); self.addCleanup(self.patcher.stop)
    def choose(self, normal):
        result = policy.select(self.ability, normal, self.actor)
        return next(name for name, path in policy.ASSETS.items() if path == result["Hit Montage"])
    def test_forward_positive_uses_front_heavy(self): self.assertEqual(self.choose((1., 0., 0.)), "front")
    def test_forward_negative_uses_back_medium(self): self.assertEqual(self.choose((-1., 0., 0.)), "back")
    def test_zero_forward_uses_original_back_branch(self): self.assertEqual(self.choose((0., 0., 0.)), "back")
    def test_positive_side_uses_left_not_right(self): self.assertEqual(self.choose((0., 1., 0.)), "left")
    def test_negative_side_uses_right(self): self.assertEqual(self.choose((0., -1., 0.)), "right")
    def test_half_boundaries_are_inclusive(self):
        for y in (-.5, .5): self.assertEqual(self.choose((1., y, 0.)), "front")
    def test_just_outside_half_is_side(self):
        self.assertEqual(self.choose((1., .500000001, 0.)), "left"); self.assertEqual(self.choose((1., -.500000001, 0.)), "right")
    def test_raw_hit_normal_not_normalized(self): self.assertEqual(self.choose((10., 1., 0.)), "left")
    def test_native_dot_and_inclusive_range_calls(self):
        self.choose((1., .25, 0.)); self.assertEqual([name for name, _ in self.calls], ["Dot_VectorVector", "Dot_VectorVector", "InRange_FloatFloat"])
        self.assertEqual(self.calls[-1][1], (.25, -.5, .5, True, True))
    def test_actor_native_basis_used(self): self.choose((1., 0., 0.)); self.assertEqual(self.actor.calls, ["GetActorForwardVector", "GetActorRightVector"])
    def test_no_implicit_original_after_python(self): self.choose((1., 0., 0.)); self.assertEqual(self.ability.originals, [])
    def test_null_actor_uses_actual_original_vm_behavior(self):
        self.assertEqual(policy.select(self.ability, (1., 0., 0.), None), {"Hit Montage": "native-original"})
        self.assertEqual(policy.evidence(self.ability)["invalid_actor_native_fallback"], 1); self.assertEqual(self.calls, [])
    def test_fallback_returns_actual_named_native_output(self):
        self.assertEqual(policy.LyraMeleeHitMontageBlueprintFallbackProfile.SelectHitMontage(self.ability, (1., 0., 0.), self.actor), {"Hit Montage": "native-original"})
        self.assertEqual(policy.evidence(self.ability)["fallback_calls"], 1)
    def test_original_public_name_and_named_output_metadata(self):
        for cls in (policy.LyraMeleeHitMontagePythonProfile, policy.LyraMeleeHitMontageBlueprintFallbackProfile):
            self.assertEqual(cls.SelectHitMontage.override, "Slelect Hit Montage"); self.assertIs(cls.SelectHitMontage.uep_named_outputs, True)
    def test_asset_authoring_keeps_graphs_and_uses_typed_external_bp_caller(self):
        source = (Path(__file__).parents[1]/"Tools/generate_melee_hit_montage_assets.py").read_text(encoding="utf-8")
        for marker in ("original_graphs_unmodified=True", "original_full_cdo_preserved=True", "native_register_restore_passed=True", "typed_ability_and_actor_references=True"):
            self.assertIn(marker, source)
        self.assertNotIn("graph_remove_node", source)
