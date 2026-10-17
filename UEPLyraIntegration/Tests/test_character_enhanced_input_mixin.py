"""Five original generated receivers, exact constants and opaque native payloads."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from uep_lyra_characters.enhanced_input_contract import ACTIONS, SELECT, BACK, FORWARD


class CharacterEnhancedInputPolicyModels(unittest.TestCase):
    def setUp(self):
        self.calls = []
        engine = types.ModuleType("unreal_engine"); structs = types.ModuleType("unreal_engine.structs"); structs.GameplayTag = lambda **args: args
        parent = types.ModuleType("uep_lyra_characters.health_changed_mixin")
        names = ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent", "ChangeQuickbarSlot", "AddInitialInventory", "CreateOrUpdateOutlineIfNeeded", "OnTeamOrCosmeticsChanged", "UpdateCustomStencilFromTeamID", "K2_OnDeathFinished", "K2_OnReset", "PythonCharacterPartsChanged", "PythonHealthChanged")
        self.prior = type("Prior", (), {name: lambda *args: None for name in names})
        parent.LyraCharacterHealthChangedPythonProfile = parent.LyraCharacterHealthChangedBlueprintFallbackProfile = self.prior
        native_names = {key: value[1] for key, value in ACTIONS.items()}; self.native_names = native_names
        binding_file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/enhanced_input_bindings.py"
        binding_spec = importlib.util.spec_from_file_location("uep_lyra_characters._input_bindings_model", binding_file); bindings = importlib.util.module_from_spec(binding_spec)
        with patch.dict(sys.modules, {"unreal_engine": engine}): binding_spec.loader.exec_module(bindings)
        bindings.function_names = lambda: dict(native_names)
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/enhanced_input_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._input_policy_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": engine, structs.__name__: structs, parent.__name__: parent, "uep_lyra_characters.enhanced_input_bindings": bindings}): spec.loader.exec_module(self.module)
        self.python, self.fallback = self.module.LyraCharacterEnhancedInputPythonProfile, self.module.LyraCharacterEnhancedInputBlueprintFallbackProfile
        self.actor = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("virtual", *args)), call_mixin_original=lambda *args: self.calls.append(("original", *args)))

    def function(self, profile, action): return next(value for value in profile.__dict__.values() if getattr(value, "override", None) == ACTIONS[action][1])
    def invoke(self, action): self.function(self.python, action)(self.actor, object(), .2, .1, object())
    def test_select_zero_preserves_index_and_tag(self): self.invoke("slot-0"); self.assertEqual(self.calls, [("virtual", "ChangeQuickbarSlot", 0, dict(TagName=SELECT))])
    def test_select_one_preserves_index_and_tag(self): self.invoke("slot-1"); self.assertEqual(self.calls[0][2:], (1, dict(TagName=SELECT)))
    def test_select_two_preserves_index_and_tag(self): self.invoke("slot-2"); self.assertEqual(self.calls[0][2:], (2, dict(TagName=SELECT)))
    def test_cycle_backward_really_keeps_original_default_zero_index(self): self.invoke("back"); self.assertEqual(self.calls[0][2:], (0, dict(TagName=BACK)))
    def test_cycle_forward_really_keeps_original_default_zero_index(self): self.invoke("forward"); self.assertEqual(self.calls[0][2:], (0, dict(TagName=FORWARD)))
    def test_all_five_original_generated_names_and_four_parameters(self):
        import inspect
        for key in ACTIONS:
            fn = self.function(self.python, key)
            self.assertEqual(list(inspect.signature(fn).parameters), ["self", "ActionValue", "ElapsedTime", "TriggeredTime", "SourceAction"])
    def test_input_data_unused_by_original_remains_opaque(self):
        class Opaque:
            def __getattribute__(self, name): raise AssertionError("unused native action payload was read")
        for action in ACTIONS: self.function(self.python, action)(self.actor, Opaque(), Opaque(), Opaque(), Opaque())
        self.assertEqual(len(self.calls), 5)
    def test_fallback_omits_all_input_overrides_for_native_original_frame_dispatch(self):
        self.assertFalse(any(getattr(value, "override", None) in self.native_names.values() for value in self.fallback.__dict__.values()))
        self.assertEqual(len([value for name, value in self.fallback.__dict__.items() if not name.startswith("__") and callable(value)]), 12)
    def test_no_extra_authority_or_controller_guard_on_input_receiver(self): self.invoke("slot-0"); self.assertEqual(len(self.calls), 1)
    def test_each_action_is_counted_once_and_evidence_is_per_actor(self):
        for action in ACTIONS: self.invoke(action)
        self.assertEqual(self.module.evidence(self.actor), dict(python_calls=5, fallback_calls=0, **dict.fromkeys(ACTIONS, 1)))
        self.assertEqual(self.module.evidence(types.SimpleNamespace())["python_calls"], 0)
    def test_twelve_previously_accepted_methods_are_explicit_aliases(self):
        for name, value in self.prior.__dict__.items():
            if not name.startswith("__"): self.assertIs(self.python.__dict__[name], value); self.assertIs(self.fallback.__dict__[name], value)
    def test_receiver_override_follows_native_compiler_renumbering_without_reload(self):
        receiver = self.function(self.python, "slot-0"); self.native_names["slot-0"] = "InpActEvt_IA_QuickSlot1_K2Node_EnhancedInputActionEvent_99"
        self.assertEqual(receiver.override, self.native_names["slot-0"])
    def test_descriptor_preserves_direct_class_function_access_and_signature(self):
        self.python.PythonQuickSlotZero(self.actor, object(), .2, .1, object())
        self.assertEqual(self.calls, [("virtual", "ChangeQuickbarSlot", 0, dict(TagName=SELECT))])
