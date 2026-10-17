"""Two-store policy models; actual native server RPC ingress is a separate gate."""
import ast
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

with patch.dict(sys.modules, {"unreal_engine": types.ModuleType("unreal_engine")}):
    policy = importlib.import_module("uep_lyra_abilities.dash_rpc_input_mixin")


class Ability:
    def __init__(self): self.values = {}; self.writes = []; self.native_calls = []
    def call_function(self, name): self.native_calls.append(name); return True
    def set_property(self, name, value): self.writes.append(name); self.values[name] = value


class DashRPCInputPolicyModels(unittest.TestCase):
    def setUp(self):
        self.ability = Ability(); self.direction = types.SimpleNamespace(x=.25, y=-.75, z=0.)
        self.montage = types.SimpleNamespace(get_path_name=lambda: "/Game/NativeMontage")
    def python(self): return policy.LyraDashRPCInputPythonProfile.StoreRemoteInput(self.ability, self.direction, self.montage)
    def fallback(self): return policy.LyraDashRPCInputBlueprintFallbackProfile.StoreRemoteInput(self.ability, self.direction, self.montage)
    def test_python_skips_original_two_stores(self): self.assertIs(self.python(), False)
    def test_fallback_continues_original_two_stores(self): self.assertIs(self.fallback(), True)
    def test_python_original_assignment_order(self): self.python(); self.assertEqual(self.ability.writes, ["Direction", "Montage"])
    def test_no_vector_reinterpretation(self): self.python(); self.assertIs(self.ability.values["Direction"], self.direction)
    def test_native_montage_identity(self): self.python(); self.assertIs(self.ability.values["Montage"], self.montage)
    def test_fallback_does_not_duplicate_writes(self): self.fallback(); self.assertEqual(self.ability.writes, [])
    def test_python_only_selected_counter(self): self.python(); self.assertEqual((policy.evidence(self.ability)["python_calls"], policy.evidence(self.ability)["fallback_calls"]), (1, 0))
    def test_fallback_only_selected_counter(self): self.fallback(); self.assertEqual((policy.evidence(self.ability)["python_calls"], policy.evidence(self.ability)["fallback_calls"]), (0, 1))
    def test_pod_evidence_has_no_native_roots(self): self.python(); self.assertIn("/Game/NativeMontage", json.dumps(policy.evidence(self.ability)))
    def test_no_rpc_or_commit_replay(self): self.python(); self.assertEqual(self.ability.native_calls, ["K2_HasAuthority"])
    def test_null_montage_preserved(self): self.montage = None; self.python(); self.assertIsNone(self.ability.values["Montage"])
    def test_instances_are_independent(self): self.python(); self.assertEqual(policy.evidence(Ability())["python_calls"], 0)
    def test_selector_named_outputs_alias_is_preserved(self):
        for cls in (policy.LyraDashRPCInputPythonProfile, policy.LyraDashRPCInputBlueprintFallbackProfile):
            self.assertIs(cls.__dict__["SelectDirectionalMontage"].uep_named_outputs, True)
            self.assertEqual(cls.__dict__["StoreRemoteInput"].override, "UEPDashStoreRemoteInput")
    def test_authoring_keeps_net_signature_and_rejoins_after_the_two_stores(self):
        source = (Path(__file__).parents[1]/"Tools/generate_dash_rpc_input_assets.py").read_text(encoding="utf-8")
        ast.parse(source)
        for required in ('connect(branch, "then", first, "execute")', 'connect(branch, "else", commit, "execute")',
                '"K2Node_VariableSet_5", "K2Node_VariableSet_6", "K2Node_CallFunction_17"', 'native_server_rpc_flags_preserved=True',
                '"K2_ActivateAbility", "SendInfo"'):
            self.assertIn(required, source)
        self.assertNotIn("FunctionFlags =", source)
