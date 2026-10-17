"""Original async team-result branch and explicit callable-descriptor aliases."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterTeamObserverPolicyModels(unittest.TestCase):
    def setUp(self):
        names = ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent", "ChangeQuickbarSlot", "AddInitialInventory", "CreateOrUpdateOutlineIfNeeded", "OnTeamOrCosmeticsChanged", "UpdateCustomStencilFromTeamID", "K2_OnDeathFinished", "K2_OnReset", "PythonCharacterPartsChanged", "PythonHealthChanged")
        parent = types.ModuleType("uep_lyra_characters.enhanced_input_mixin")
        self.fallback_parent = type("Fallback", (), {name: lambda *args: None for name in names})
        class Descriptor:
            def __call__(self, *args): pass
            def __get__(self, instance, owner): return lambda *args: None
        values = {name: self.fallback_parent.__dict__[name] for name in names}
        values.update({name: Descriptor() for name in ("PythonQuickSlotZero", "PythonQuickSlotOne", "PythonQuickSlotTwo", "PythonQuickSlotBackward", "PythonQuickSlotForward")})
        self.parent = type("Python", (), values)
        parent.LyraCharacterEnhancedInputPythonProfile, parent.LyraCharacterEnhancedInputBlueprintFallbackProfile = self.parent, self.fallback_parent
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/team_observer_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._team_observer_policy_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {parent.__name__: parent, native.__name__: native}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterTeamObserverPythonProfile, self.module.LyraCharacterTeamObserverBlueprintFallbackProfile
        self.calls = []; self.display = types.SimpleNamespace(get_path_name=lambda: "native-team-display")
        self.actor = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("virtual", *args)), call_mixin_original=lambda *args: self.calls.append(("original", *args)))

    def test_exact_original_generated_async_receiver_and_parameters(self):
        import inspect
        for profile in (self.python, self.fallback):
            self.assertEqual(profile.PythonObservedTeamChanged.override, self.module.BOUND_EVENT)
            self.assertEqual(list(inspect.signature(profile.PythonObservedTeamChanged).parameters), ["self", "bTeamSet", "TeamId", "DisplayAsset"])
    def test_assigned_team_forwards_original_payload_to_virtual_helper(self):
        self.python.PythonObservedTeamChanged(self.actor, True, 7, self.display)
        self.assertEqual(self.calls, [("virtual", "OnTeamOrCosmeticsChanged", 7, self.display)])
    def test_unassigned_team_preserves_noop_even_with_nonnull_display(self):
        self.python.PythonObservedTeamChanged(self.actor, False, -1, self.display)
        self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["no_team_noops"], 1)
    def test_assigned_team_with_null_display_still_forwards(self):
        self.python.PythonObservedTeamChanged(self.actor, True, 0, None)
        self.assertEqual(self.calls, [("virtual", "OnTeamOrCosmeticsChanged", 0, None)])
    def test_no_new_authority_or_local_control_guard(self):
        self.python.PythonObservedTeamChanged(self.actor, True, 0, self.display); self.assertEqual(len(self.calls), 1)
    def test_fallback_preserves_all_three_native_arguments(self):
        self.fallback.PythonObservedTeamChanged(self.actor, True, 2, self.display)
        self.assertEqual(self.calls, [("original", self.module.BOUND_EVENT, True, 2, self.display)])
    def test_fallback_also_forwards_false_instead_of_reimplementing_original_branch(self):
        self.fallback.PythonObservedTeamChanged(self.actor, False, -1, None)
        self.assertEqual(self.calls, [("original", self.module.BOUND_EVENT, False, -1, None)])
    def test_all_seventeen_prior_python_methods_are_explicit_aliases(self):
        for name, value in self.parent.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], value)
    def test_five_input_descriptors_are_not_accidentally_unwrapped_by_aliasing(self):
        for name in ("PythonQuickSlotZero", "PythonQuickSlotOne", "PythonQuickSlotTwo", "PythonQuickSlotBackward", "PythonQuickSlotForward"):
            self.assertIs(self.python.__dict__[name], self.parent.__dict__[name]); self.assertIsNot(self.python.__dict__[name], getattr(self.parent, name))
    def test_fallback_still_omits_five_input_overrides_for_native_original_frames(self):
        self.assertFalse(any(name.startswith("PythonQuickSlot") for name in self.fallback.__dict__))
    def test_evidence_is_per_actor_pod_not_async_proxy_or_actor_roots(self):
        self.python.PythonObservedTeamChanged(self.actor, True, 2, self.display)
        self.assertEqual(self.module.evidence(self.actor)["last_payload"], dict(team_set=True, team_id=2, display_asset="native-team-display"))
        self.assertEqual(self.module.evidence(types.SimpleNamespace())["python_calls"], 0)
    def test_failed_virtual_helper_is_not_counted_as_completed_team_update(self):
        self.actor.call_function = lambda *args: (_ for _ in ()).throw(RuntimeError("native team update refused"))
        with self.assertRaisesRegex(RuntimeError, "native team update refused"): self.python.PythonObservedTeamChanged(self.actor, True, 0, self.display)
        self.assertEqual(self.module.evidence(self.actor)["team_updates"], 0)
