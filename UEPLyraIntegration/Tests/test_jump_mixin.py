"""Ordering/cleanup models only; native jump/GAS proof is a separate gate."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_inventory_pad_mixin import Object
from test_heal_ability_mixin import Scope


class JumpPolicy(unittest.TestCase):
    def setUp(self):
        self.order = []
        native = types.ModuleType("unreal_engine")
        runtime = types.ModuleType("uep_runtime"); runtime.SubscriptionScope = Scope
        widgets = types.ModuleType("uep_lyra_abilities.widget_lifecycle")
        widgets.add_single = lambda ability: self.order.append("widget-add") or True
        widgets.remove_single = lambda ability: self.order.append("widget-remove")
        self.tasks = []
        def task_factory(name, *args):
            self.order.append((name, args[1:]))
            task = Object(name, lambda method, *values: self.order.append(method)); self.tasks.append(task)
            return task
        factory = Object("factory", task_factory)
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: factory)
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/jump_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_abilities._jump_test", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime,
                                     "uep_lyra_abilities.widget_lifecycle": widgets}):
            spec.loader.exec_module(self.module)
        self.props = {"bIsActive": True}
        self.ability = Object("ability", self.call)
        self.ability.get_path_name = lambda: "jump-ability"
        self.ability.get_property = self.props.get
        self.ability.set_property = lambda key, value: self.props.__setitem__(key, value)
        self.module.LyraJumpPythonProfile.__init__(self.ability)

    def call(self, name, *args):
        self.order.append(name)
        if name in ("K2_EndAbility", "K2_CancelAbility"):
            self.props["bIsActive"] = False
            if not self.props.get(self.module.TEARING_DOWN):
                self.module.LyraJumpPythonProfile.NativeEnded(self.ability, name == "K2_CancelAbility")

    def test_start_state_and_wait_input_use_original_native_order(self):
        self.module.activate(self.ability)
        self.assertEqual(self.order, ["CharacterJumpStart", ("StartAbilityState", ("Jumping", True)),
            "ReadyForActivation", ("WaitInputRelease", (True,)), "ReadyForActivation"])
        self.assertEqual(set(self.ability._uep_jump_scope.callbacks), {"OnStateEnded", "OnStateInterrupted", "OnRelease"})

    def test_input_release_native_end_closes_owned_scope(self):
        self.module.activate(self.ability); scope = self.ability._uep_jump_scope
        scope.callbacks["OnRelease"](.25)
        self.assertTrue(scope.closed)
        self.assertFalse(self.props["bIsActive"])
        self.assertEqual(self.module.snapshot()["active_count"], 0)
        self.assertEqual(self.module.snapshot()["native_ends"], 1)

    def test_state_completion_and_interruption_call_native_stop(self):
        self.module.activate(self.ability)
        self.ability._uep_jump_scope.callbacks["OnStateEnded"]()
        self.ability._uep_jump_scope.callbacks["OnStateInterrupted"]()
        self.assertEqual(self.order.count("CharacterJumpStop"), 2)

    def test_profile_teardown_cancels_without_reentering_router_or_ui(self):
        self.module.activate(self.ability); scope = self.ability._uep_jump_scope
        self.module.LyraJumpPythonProfile.__uep_mixin_teardown__(self.ability)
        self.assertTrue(scope.closed)
        self.assertFalse(self.props[self.module.TEARING_DOWN])
        self.assertNotIn("widget-remove", self.order)
        self.assertEqual(self.module.snapshot()["native_ends"], 0)

    def test_ui_lifetime_is_grant_remove_not_jump_end(self):
        self.module.LyraJumpPythonProfile.K2_OnAbilityAdded(self.ability)
        self.module.activate(self.ability); self.module.LyraJumpPythonProfile.NativeEnded(self.ability, False)
        self.assertNotIn("widget-remove", self.order)
        self.module.LyraJumpPythonProfile.K2_OnAbilityRemoved(self.ability)
        self.assertEqual(self.order.count("widget-remove"), 1)

    def test_inactive_teardown_does_not_synthesize_cancel(self):
        self.props["bIsActive"] = False
        self.module.LyraJumpPythonProfile.__uep_mixin_teardown__(self.ability)
        self.assertEqual(self.order, [])
