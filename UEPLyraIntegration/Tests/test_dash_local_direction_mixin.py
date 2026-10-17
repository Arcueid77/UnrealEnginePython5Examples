"""Native-call shape/choice models; real original BP and gameplay gates remain separate."""
import importlib
import math
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

with patch.dict(sys.modules, {"unreal_engine": types.ModuleType("unreal_engine")}):
    policy = importlib.import_module("uep_lyra_abilities.dash_local_direction_mixin")


class V:
    def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z
    def data(self): return [self.x, self.y, self.z]


class Actor:
    def __init__(self):
        self.last, self.facing, self.camera, self.location = V(0., 2., 0.), V(1., 0., 0.), V(.25, .5, -.75), V(10., 20., 30.)
    def call_function(self, name): return {"GetActorForwardVector": self.facing, "GetLastMovementInputVector": self.last, "GetForwardVector": self.camera}[name]
    def get_property(self, name): assert name == "CameraComponent"; return self
    def get_actor_location(self): return self.location


class Ability:
    def __init__(self): self.actor = Actor(); self.calls = []; self.writes = []; self.bias = True; self.montage = None
    def call_function(self, name, *args):
        self.calls.append((name, args))
        if name == "GetLyraCharacterFromActorInfo": return self.actor
        assert name == "SelectDirectionalMontage"; return self.montage, self.bias
    def set_property(self, name, value): self.writes.append((name, value))


class LocalDirectionModels(unittest.TestCase):
    def setUp(self):
        self.ability = Ability(); self.ai = False; self.projected = V(13., 24., 99.); self.success = True; self.calls = []
        self.native = patch.object(policy, "ue", types.SimpleNamespace(FVector=V)); self.native.start(); self.addCleanup(self.native.stop)
        self.libs = patch.object(policy, "library", lambda cls: types.SimpleNamespace(call_function=lambda method, *args, **kwargs: self.call(cls, method, args, kwargs)))
        self.libs.start(); self.addCleanup(self.libs.stop)
    def call(self, cls, name, args, kwargs):
        self.calls.append((cls, name, args, kwargs))
        if name == "GetAIController": return object() if self.ai else None
        if name == "IsValid": return args[0] is not None
        if name == "K2_ProjectPointToNavigation": return self.success, self.projected
        if name == "Multiply_VectorVector": return V(*(a*b for a, b in zip(args[0].data(), args[1].data())))
        if name == "Subtract_VectorVector": return V(*(a-b for a, b in zip(args[0].data(), args[1].data())))
        if name == "Normal":
            length = math.sqrt(sum(x*x for x in args[0].data())); return V(*(x/length if length*length >= args[1] else 0. for x in args[0].data()))
        raise AssertionError(name)
    def resolve(self): return policy.resolve(self.ability)
    def test_native_actor_facing_not_camera(self): self.assertIs(self.resolve()[0], self.ability.actor.facing)
    def test_player_last_input_keeps_original_magnitude(self): self.assertIs(self.resolve()[1], self.ability.actor.last)
    def test_native_camera_z_multiplier_is_retained(self):
        for actual, expected in zip(self.resolve()[2].data(), [.25, .5, -.9]): self.assertAlmostEqual(actual, expected)
    def test_player_branch_does_not_invent_ai_navigation(self): self.resolve(); self.assertNotIn("K2_ProjectPointToNavigation", [row[1] for row in self.calls])
    def test_ai_uses_native_projected_delta_not_input(self):
        self.ai = True; result = self.resolve(); self.assertEqual(result[1].data(), [.6, .8, 0.]); self.assertIs(result[1], result[2])
    def test_ai_flattens_projected_z(self): self.ai = True; self.assertEqual(self.resolve()[1].z, 0.)
    def test_ai_normalization_tolerance_matches_original(self):
        self.ai = True; self.resolve(); self.assertEqual(next(row for row in self.calls if row[1] == "Normal")[2][1], .0001)
    def test_native_projection_extent_and_default_filter(self):
        self.ai = True; self.resolve(); kwargs = next(row for row in self.calls if row[1] == "K2_ProjectPointToNavigation")[3]
        self.assertEqual(kwargs["QueryExtent"].data(), [500., 500., 500.]); self.assertIsNone(kwargs["NavData"]); self.assertIsNone(kwargs["FilterClass"])
        self.assertIs(kwargs["WorldContextObject"], self.ability)
    def test_failed_projection_keeps_native_output_not_fallback_input(self):
        self.ai = True; self.success = False; self.assertEqual(self.resolve()[1].data(), [.6, .8, 0.]); self.assertIs(self.resolve()[3]["projection_succeeded"], False)
    def test_zero_projected_delta_remains_zero(self):
        self.ai = True; self.projected = self.ability.actor.location; self.assertEqual(self.resolve()[1].data(), [0., 0., 0.])
    def test_python_replaces_original_local_span(self): self.assertIs(policy.prepare(self.ability), False)
    def test_original_montage_then_direction_store_order(self): policy.prepare(self.ability); self.assertEqual([name for name, value in self.ability.writes], ["Montage", "Direction"])
    def test_forward_bias_uses_camera_branch(self): policy.prepare(self.ability); self.assertAlmostEqual(self.ability.writes[1][1].z, -.9)
    def test_nonforward_bias_uses_last_input(self): self.ability.bias = False; policy.prepare(self.ability); self.assertIs(self.ability.writes[1][1], self.ability.actor.last)
    def test_selector_is_routed_not_reimplemented(self):
        policy.prepare(self.ability); self.assertEqual([name for name, args in self.ability.calls], ["GetLyraCharacterFromActorInfo", "SelectDirectionalMontage"])
    def test_fallback_does_not_execute_python_or_stores(self):
        self.assertIs(policy.LyraDashLocalDirectionBlueprintFallbackProfile.PrepareLocalDirection(self.ability), True)
        self.assertEqual(self.ability.calls+self.ability.writes, []); self.assertEqual(policy.evidence(self.ability)["fallback_calls"], 1)
    def test_selected_route_counter_only(self): policy.prepare(self.ability); self.assertEqual((policy.evidence(self.ability)["python_calls"], policy.evidence(self.ability)["fallback_calls"]), (1, 0))
    def test_unused_positive_output_is_not_new_business(self): self.resolve(); self.assertNotIn("VSize", [row[1] for row in self.calls])
    def test_explicit_local_aliases_retain_remote_and_named_selector_metadata(self):
        for cls in (policy.LyraDashLocalDirectionPythonProfile, policy.LyraDashLocalDirectionBlueprintFallbackProfile):
            self.assertEqual(cls.__dict__["PrepareLocalDirection"].override, policy.GATE)
            self.assertIs(cls.__dict__["SelectDirectionalMontage"].uep_named_outputs, True)
            self.assertEqual(cls.__dict__["StoreRemoteInput"].override, "UEPDashStoreRemoteInput")
    def test_gateway_keeps_original_graph_and_reads_live_direction_on_bypass(self):
        source = (Path(__file__).parents[1]/"Tools/generate_dash_local_direction_assets.py").read_text(encoding="utf-8")
        for required in ('connect(branch, "then", selector, "execute")', 'connect(branch, "else", zero, "execute")', 'connect(getter, "Direction", zero_math, "A")', 'local_direction_transport_nodes=5'):
            self.assertIn(required, source)
        self.assertNotIn("graph_remove_node", source)
