"""Exact bound receiver name, opaque component and original team-query branch."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterPartsChangedPolicyModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.found, self.team = [], True, 2
        self.display = types.SimpleNamespace(get_path_name=lambda: "native-team-display")
        engine = types.ModuleType("unreal_engine")
        engine.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=self.query))
        parent = types.ModuleType("uep_lyra_characters.lifecycle_mixin")
        class Lifecycle:
            def ClearInventory(self): pass
            def GetEmoteAudioComponent(self): pass
            def SetEmoteAudioComponent(self, AudioComponent): pass
            def ChangeQuickbarSlot(self, NewSlotIndex, SlotActionTag): pass
            def AddInitialInventory(self): pass
            def CreateOrUpdateOutlineIfNeeded(self, TeamID, OutlineColor): pass
            def OnTeamOrCosmeticsChanged(self, TeamID, TeamDisplayAsset): pass
            def UpdateCustomStencilFromTeamID(self, TeamId): pass
            def K2_OnDeathFinished(self): pass
            def K2_OnReset(self): pass
        parent.LyraCharacterLifecyclePythonProfile = parent.LyraCharacterLifecycleBlueprintFallbackProfile = Lifecycle
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/parts_changed_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._parts_changed_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": engine, parent.__name__: parent, native.__name__: native}): spec.loader.exec_module(self.module)
        self.parent, self.python, self.fallback = Lifecycle, self.module.LyraCharacterPartsChangedPythonProfile, self.module.LyraCharacterPartsChangedBlueprintFallbackProfile
        self.actor = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("actor", *args)), call_mixin_original=lambda *args: self.calls.append(("original", *args)))

    def query(self, *args):
        self.calls.append(("query", *args)); return self.found, self.team, self.display

    def test_queries_self_with_original_no_warning_flag_not_component_payload(self):
        self.python.PythonCharacterPartsChanged(self.actor, object())
        self.assertEqual(self.calls[0], ("query", "FindTeamFromObject", self.actor, False))

    def test_valid_team_passes_native_team_and_display_to_virtual_helper(self):
        self.python.PythonCharacterPartsChanged(self.actor, object())
        self.assertEqual(self.calls[1], ("actor", "OnTeamOrCosmeticsChanged", self.team, self.display))

    def test_unset_team_keeps_original_noop_even_with_a_display_object(self):
        self.found = False; self.team = -1
        self.python.PythonCharacterPartsChanged(self.actor, object())
        self.assertEqual(len(self.calls), 1); self.assertEqual(self.module.evidence(self.actor)["no_team_noops"], 1)

    def test_valid_team_with_missing_display_still_forwards(self):
        self.display = None; self.python.PythonCharacterPartsChanged(self.actor, None)
        self.assertEqual(self.calls[1], ("actor", "OnTeamOrCosmeticsChanged", 2, None))

    def test_component_payload_is_unused_and_need_not_be_dereferenceable(self):
        class Opaque:
            def __getattribute__(self, name): raise AssertionError("original BP never dereferences its component payload")
        self.python.PythonCharacterPartsChanged(self.actor, Opaque()); self.assertEqual(len(self.calls), 2)

    def test_exact_original_generated_receiver_is_explicit_on_both_profiles(self):
        for profile in (self.python, self.fallback):
            self.assertEqual(profile.PythonCharacterPartsChanged.override, self.module.BOUND_EVENT)
        self.assertIn("PawnCosmeticsComponent_K2Node_ComponentBoundEvent_2", self.module.BOUND_EVENT)

    def test_fallback_calls_only_original_receiver_with_exact_component(self):
        component = object(); self.fallback.PythonCharacterPartsChanged(self.actor, component)
        self.assertEqual(self.calls, [("original", self.module.BOUND_EVENT, component)])

    def test_no_authority_local_control_or_replication_guard_is_invented(self):
        self.python.PythonCharacterPartsChanged(self.actor, object())
        self.assertEqual([call[1] for call in self.calls], ["FindTeamFromObject", "OnTeamOrCosmeticsChanged"])

    def test_ten_prior_methods_are_explicit_aliases(self):
        for name, value in self.parent.__dict__.items():
            if not name.startswith("__"):
                with self.subTest(name=name): self.assertIs(self.python.__dict__[name], value)

    def test_evidence_is_per_actor_pod_and_does_not_hold_native_objects(self):
        self.python.PythonCharacterPartsChanged(self.actor, object()); value = self.module.evidence(self.actor)
        self.assertEqual(value["last_query"], dict(part_of_team=True, team_id=2, display_asset="native-team-display"))
        other = types.SimpleNamespace(); self.assertEqual(self.module.evidence(other)["python_calls"], 0)

    def test_query_failure_is_not_reported_as_a_completed_team_refresh(self):
        def fail(*args): raise RuntimeError("native query failed")
        self.query = fail
        # Replace the lookup to retain the same actual function-call boundary.
        self.module.ue.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=fail))
        with self.assertRaisesRegex(RuntimeError, "native query failed"): self.python.PythonCharacterPartsChanged(self.actor, None)
        self.assertEqual(self.module.evidence(self.actor)["team_updates"], 0)
