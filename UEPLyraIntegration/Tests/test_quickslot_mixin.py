"""Task/dispatch ownership models; native GAS/RPC comparison runs separately."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_inventory_pad_mixin import Object


class Scope:
    def __init__(self): self.callbacks, self.closed = [], False
    def bind_event(self, source, name, callback): self.callbacks.append((source, name, callback))
    def close(self): self.closed = True; self.callbacks = []


class QuickslotPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.factories = [], []
        native, runtime, structs = types.ModuleType("unreal_engine"), types.ModuleType("uep_runtime"), types.ModuleType("unreal_engine.structs")
        runtime.SubscriptionScope = Scope; structs.GameplayTag = lambda **values: types.SimpleNamespace(**values)
        self.quickbar = Object("quickbar", lambda name, *args: self.calls.append((name, args)))
        self.controller = Object("controller", lambda name, *args: self.quickbar)
        self.props = {"bIsActive": True}
        def factory(name, *args):
            if name == "FTrunc": return int(args[0])
            self.factories.append((name, args))
            return Object("task", lambda name, *args: self.calls.append((name, args)))
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: Object("factory", factory))
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/quickslot_mixin.py"
        spec = importlib.util.spec_from_file_location("quickslot_policy_test", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs, "uep_runtime": runtime}):
            spec.loader.exec_module(self.module)
        self.ability = Object("ability", self.call)
        self.ability.get_path_name = lambda: "ability"
        self.ability.set_property = lambda key, value: (self.props.__setitem__(key, value), setattr(self.ability, key, value))
        self.ability.get_property = self.props.get
        self.module.LyraQuickslotPythonProfile.__init__(self.ability)

    def call(self, name, *args):
        if name == "GetControllerFromActorInfo": return self.controller
        if name == "K2_EndAbility": self.props["bIsActive"] = False
        self.calls.append((name, args))

    def activate(self): self.module.activate(self.ability)

    def test_three_original_tags_and_native_repeat_exact_flags(self):
        self.activate()
        self.assertEqual([args[1].TagName for _, args in self.factories], [tag for _, tag in self.module.TAGS])
        self.assertTrue(all(args[2:] == (None, False, True) for _, args in self.factories))
        self.assertEqual([name for name, _ in self.calls], ["ReadyForActivation"]*3)

    def test_select_truncates_toward_zero_and_forwards_native_rpc(self):
        self.activate(); callback = self.ability._uep_quickslot_scope.callbacks[0][2]
        for value in (1.9, -.9): callback(types.SimpleNamespace(EventMagnitude=value))
        self.assertIn(("SetActiveSlotIndex", (1,)), self.calls)
        self.assertIn(("SetActiveSlotIndex", (0,)), self.calls)
        self.assertEqual(self.module.snapshot()["selects"], 2)

    def test_callbacks_keep_distinct_backward_forward_intent(self):
        self.activate()
        for _, _, callback in self.ability._uep_quickslot_scope.callbacks[1:]: callback(types.SimpleNamespace(EventMagnitude=0.))
        self.assertEqual([name for name, _ in self.calls][-2:], ["CycleActiveSlotBackward", "CycleActiveSlotForward"])

    def test_native_end_closes_owned_scope_once(self):
        self.activate(); scope = self.ability._uep_quickslot_scope
        self.module.LyraQuickslotPythonProfile.NativeEnded(self.ability, False)
        self.module.close(self.ability)
        self.assertTrue(scope.closed); self.assertEqual(self.module.snapshot()["scopes_closed"], 1)
        self.assertEqual(self.module.snapshot()["active_count"], 0)

    def test_profile_teardown_ends_native_ability_without_reentrant_end(self):
        self.activate(); scope = self.ability._uep_quickslot_scope
        self.module.LyraQuickslotPythonProfile.__uep_mixin_teardown__(self.ability)
        self.assertTrue(scope.closed); self.assertFalse(self.props["bIsActive"])
        self.assertFalse(self.props[self.module.GUARD]); self.assertEqual(self.module.snapshot()["native_ends"], 0)

    def test_inactive_teardown_does_not_end_again(self):
        self.props["bIsActive"] = False
        self.module.LyraQuickslotPythonProfile.__uep_mixin_teardown__(self.ability)
        self.assertFalse(self.calls)
