"""Native-entry forwarding, no duplicate BP body, no fake death or Reset."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterLifecyclePolicyModels(unittest.TestCase):
    def setUp(self):
        self.calls = []
        parent = types.ModuleType("uep_lyra_characters.stencil_mixin")
        class Stencil:
            def ClearInventory(self): pass
            def GetEmoteAudioComponent(self): pass
            def SetEmoteAudioComponent(self, AudioComponent): pass
            def ChangeQuickbarSlot(self, NewSlotIndex, SlotActionTag): pass
            def AddInitialInventory(self): pass
            def CreateOrUpdateOutlineIfNeeded(self, TeamID, OutlineColor): pass
            def OnTeamOrCosmeticsChanged(self, TeamID, TeamDisplayAsset): pass
            def UpdateCustomStencilFromTeamID(self, TeamId): pass
        parent.LyraCharacterStencilPythonProfile = parent.LyraCharacterStencilBlueprintFallbackProfile = Stencil
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/lifecycle_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._lifecycle_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {parent.__name__: parent}): spec.loader.exec_module(self.module)
        self.parent, self.python, self.fallback = Stencil, self.module.LyraCharacterLifecyclePythonProfile, self.module.LyraCharacterLifecycleBlueprintFallbackProfile
        self.actor = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("helper", *args)), call_mixin_original=lambda *args: self.calls.append(("original", *args)))

    def test_python_death_finished_calls_selected_clear_helper_once(self):
        self.python.K2_OnDeathFinished(self.actor); self.assertEqual(self.calls, [("helper", "ClearInventory")])
        self.assertEqual(self.module.evidence(self.actor), dict(death_python=1, death_fallback=0, reset_python=0, reset_fallback=0, clear_forwards=1, last_event="K2_OnDeathFinished"))

    def test_python_reset_calls_selected_clear_helper_once(self):
        self.python.K2_OnReset(self.actor); self.assertEqual(self.calls, [("helper", "ClearInventory")])
        self.assertEqual(self.module.evidence(self.actor), dict(death_python=0, death_fallback=0, reset_python=1, reset_fallback=0, clear_forwards=1, last_event="K2_OnReset"))

    def test_fallback_death_only_invokes_saved_bp_event(self):
        self.fallback.K2_OnDeathFinished(self.actor); self.assertEqual(self.calls, [("original", "K2_OnDeathFinished")])
        self.assertEqual(self.module.evidence(self.actor)["clear_forwards"], 0)

    def test_fallback_reset_only_invokes_saved_bp_event(self):
        self.fallback.K2_OnReset(self.actor); self.assertEqual(self.calls, [("original", "K2_OnReset")])
        self.assertEqual(self.module.evidence(self.actor)["reset_fallback"], 1)

    def test_no_authority_guard_or_actor_death_reset_destruction_is_invented(self):
        self.python.K2_OnDeathFinished(self.actor); self.python.K2_OnReset(self.actor)
        self.assertEqual(self.calls, [("helper", "ClearInventory")]*2)

    def test_eight_prior_functions_are_explicit_aliases(self):
        for name in ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent", "ChangeQuickbarSlot", "AddInitialInventory", "CreateOrUpdateOutlineIfNeeded", "OnTeamOrCosmeticsChanged", "UpdateCustomStencilFromTeamID"):
            with self.subTest(name=name): self.assertIs(self.python.__dict__[name], self.parent.__dict__[name])

    def test_event_state_is_per_actor_pod_not_a_global_actor_reference(self):
        self.python.K2_OnDeathFinished(self.actor)
        other = types.SimpleNamespace(call_function=self.actor.call_function)
        self.python.K2_OnReset(other)
        self.assertEqual(self.module.evidence(self.actor)["reset_python"], 0); self.assertEqual(self.module.evidence(other)["death_python"], 0)
        self.assertTrue(all(type(value) in (int, str) for value in self.module.evidence(self.actor).values()))

    def test_helper_failure_propagates_without_recording_a_completed_forward(self):
        def fail(*args): raise RuntimeError("native clear failed")
        self.actor.call_function = fail
        with self.assertRaisesRegex(RuntimeError, "native clear failed"): self.python.K2_OnReset(self.actor)
        self.assertEqual(self.module.evidence(self.actor)["clear_forwards"], 0)
