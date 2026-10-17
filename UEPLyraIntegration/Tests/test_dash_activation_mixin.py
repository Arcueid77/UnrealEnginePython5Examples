"""Native primitive stand-ins check ordering, not native activation acceptance."""
from pathlib import Path
import importlib
import sys
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch
with patch.dict(sys.modules, {"unreal_engine": ModuleType("unreal_engine")}):
    policy = importlib.import_module("uep_lyra_abilities.dash_activation_mixin")


class Ability:
    def __init__(self):
        self.local = self.commit = self.authority = True; self.zero = self.crouched = False
        self.calls = []; self.fields = dict(Direction="native-vector", Montage="native-montage")
    def get_property(self, name): return self.crouched if name == "bIsCrouched" else self.fields[name]
    def call_function(self, name, *args):
        self.calls.append((name, args))
        return {"IsLocallyControlled": self.local, "K2_CommitAbility": self.commit, "K2_HasAuthority": self.authority,
            "GetLyraCharacterFromActorInfo": self}.get(name)
    def call_mixin_original(self, name): self.calls.append(("original", (name,)))


class ActivationPolicyModels(unittest.TestCase):
    def setUp(self):
        self.ability = Ability(); self.math_calls = []
        def native(name, *args): self.math_calls.append((name, args)); return self.ability.zero
        self.patcher = patch.object(policy.ue, "find_class", lambda name: SimpleNamespace(get_cdo=lambda: SimpleNamespace(call_function=native)), create=True)
        self.patcher.start(); self.addCleanup(self.patcher.stop)
    def activate(self): policy.activate(self.ability); return policy.evidence(self.ability)["last"]
    def names(self): return [row[0] for row in self.ability.calls]
    def test_remote_waits_for_real_native_rpc(self): self.ability.local = False; self.activate(); self.assertEqual(self.names(), ["IsLocallyControlled"])
    def test_zero_cancels_before_commit(self): self.ability.zero = True; self.activate(); self.assertEqual(self.names(), ["IsLocallyControlled", "UEPDashPrepareLocalDirection", "K2_CancelAbility"])
    def test_original_native_nearzero_tolerance(self): self.activate(); self.assertEqual(self.math_calls, [("Vector_IsNearlyZero", ("native-vector", .0001))])
    def test_commit_failure_cancels_without_tasks_or_crouch(self):
        self.ability.commit = False; self.activate(); self.assertEqual(self.names()[-2:], ["K2_CommitAbility", "K2_CancelAbility"])
        self.assertNotIn(policy.TASKS, self.names()); self.assertNotIn("GetLyraCharacterFromActorInfo", self.names())
    def test_authority_does_not_send_rpc(self): self.activate(); self.assertNotIn("SendInfo", self.names()); self.assertEqual(self.names()[-1], policy.TASKS)
    def test_client_sends_original_payload_before_native_tasks(self):
        self.ability.authority = False; self.activate(); self.assertEqual(self.ability.calls[-2:], [("SendInfo", ("native-vector", "native-montage")), (policy.TASKS, ())])
    def test_crouch_uses_native_uncrouch_before_authority(self):
        self.ability.crouched = True; data = self.activate(); self.assertLess(self.names().index("UnCrouch"), self.names().index("K2_HasAuthority")); self.assertTrue(data["uncrouch_called"])
        self.assertIn(("UnCrouch", (False,)), self.ability.calls)
    def test_not_crouched_does_not_uncrouch(self): self.activate(); self.assertNotIn("UnCrouch", self.names())
    def test_local_preparation_runs_exactly_once(self): self.activate(); self.assertEqual(self.names().count("UEPDashPrepareLocalDirection"), 1)
    def test_native_task_entry_runs_once(self): self.activate(); self.assertEqual(self.names().count(policy.TASKS), 1)
    def test_no_automatic_original_after_python(self): self.activate(); self.assertNotIn("original", self.names())
    def test_fallback_invokes_preserved_actual_event(self):
        policy.LyraDashActivationBlueprintFallbackProfile.Activate(self.ability); self.assertEqual(self.ability.calls, [("original", (policy.METHOD,))])
        self.assertEqual(policy.evidence(self.ability)["fallback_calls"], 1)
    def test_profile_has_four_explicit_metadata_preserving_aliases(self):
        for cls in (policy.LyraDashActivationPythonProfile, policy.LyraDashActivationBlueprintFallbackProfile):
            self.assertEqual(cls.__dict__["Activate"].override, "K2_ActivateAbility")
            self.assertIs(cls.__dict__["SelectDirectionalMontage"].uep_named_outputs, True)
            self.assertEqual(cls.__dict__["PrepareLocalDirection"].override, "UEPDashPrepareLocalDirection")
            self.assertEqual(cls.__dict__["StoreRemoteInput"].override, "UEPDashStoreRemoteInput")
    def test_native_graph_entry_only_not_cloning_business(self):
        source = (Path(__file__).parents[1]/"Tools/generate_dash_activation_assets.py").read_text(encoding="utf-8")
        self.assertIn('connect(entry, "then", task, "execute")', source)
        self.assertIn("native_task_entry_nodes=1", source)
        for fragment in ("break_link_to", "graph_remove_node", "graph_add_node_call_function"):
            self.assertNotIn(fragment, source)
