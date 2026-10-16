"""Pressed-widget policy/lifetime models; not native UI or input evidence."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_widget_held_mixin import Native, Scope


class PressedPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.active, self.widget_active, self.sync = [], True, True, False
        self.props, self.path = {}, "/Native/UnloadedMenu.UnloadedMenu_C"
        self.controller, self.foreign_calls = object(), 0
        self.action = Native(self.action_call)
        self.widget = Native(self.widget_call)
        self.foreign = lambda: setattr(self, "foreign_calls", self.foreign_calls + 1)
        self.original = lambda: self.call("OnWidgetDeactivated")
        self.widget.listeners["BP_OnWidgetDeactivated"] = [self.foreign]
        native, structs, runtime, helper = [types.ModuleType(name) for name in
            ("unreal_engine", "unreal_engine.structs", "uep_runtime", "uep_lyra_world.effect_pad_mixin")]
        structs.GameplayTag = lambda **kwargs: types.SimpleNamespace(**kwargs)
        runtime.SubscriptionScope, helper.valid = Scope, lambda value: value is not None
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=self.factory))
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_abilities/widget_pressed_mixin.py"
        spec = importlib.util.spec_from_file_location("pressed_model", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs,
            "uep_runtime": runtime, "uep_lyra_world.effect_pad_mixin": helper}):
            spec.loader.exec_module(self.module)
        self.props[self.module.GUARD] = False
        self.profile = self.module.LyraWidgetPressedPythonProfile
        self.ability = types.SimpleNamespace(call_function=self.call,
            get_property=lambda key: self.active if key == "bIsActive" else self.props.get(key),
            set_property=lambda key, value: self.props.__setitem__(key, value), get_path_name=lambda: "original-pressed-ability",
            call_mixin_original=lambda name: self.calls.append(("original-" + name, ())))
        self.profile.__init__(self.ability)

    @staticmethod
    def emit(source, event, *args):
        for callback in list(source.listeners.get(event, [])): callback(*args)

    def factory(self, name, *args):
        self.calls.append((name, args)); return self.action

    def call(self, name, *args):
        self.calls.append((name, args))
        if name == self.module.CLASS_PATH: return self.path
        if name == "GetLyraPlayerControllerFromActorInfo": return self.controller
        if name == "OnWidgetDeactivated":
            if self.props[self.module.GUARD]: raise RuntimeError("teardown router reentry")
            return self.profile.OnWidgetDeactivated(self.ability)
        if name == self.module.REMOVE:
            args[0].listeners["BP_OnWidgetDeactivated"] = [value for value in args[0].listeners["BP_OnWidgetDeactivated"] if value is not self.original]
        if name == "K2_EndAbility":
            self.active = False
            if not self.props[self.module.GUARD]: self.profile.NativeEnded(self.ability, False)

    def action_call(self, name, *args):
        self.calls.append(("action-" + name, args))
        if name == "Activate" and self.sync: self.emit(self.action, "AfterPush", self.widget)

    def widget_call(self, name, *args):
        self.calls.append((name, args))
        if name == "IsActivated": return self.widget_active
        if name == "DeactivateWidget":
            self.widget_active = False; self.emit(self.widget, "BP_OnWidgetDeactivated")

    def pushed(self):
        self.profile.K2_ActivateAbility(self.ability); self.emit(self.action, "AfterPush", self.widget)

    def assert_closed(self):
        value = self.module.snapshot()
        self.assertEqual(value["scopes_created"], value["scopes_closed"])
        self.assertEqual(value["active_count"], 0)

    def test_original_lazy_path_game_menu_and_suspend_true(self):
        self.profile.K2_ActivateAbility(self.ability)
        name, args = next(row for row in self.calls if row[0] == "PushContentToLayerForPlayer")
        self.assertEqual(args[:2], (self.controller, self.path))
        self.assertEqual(args[2].TagName, "UI.Layer.GameMenu")
        self.assertIs(args[3], True)
        self.assertFalse(any("AbilityTask" in name for name, args in self.calls))

    def test_empty_root_configuration_fails_before_native_push(self):
        self.path = ""
        with self.assertRaisesRegex(RuntimeError, "configured WidgetToSpawn"): self.profile.K2_ActivateAbility(self.ability)
        self.assertFalse(any(name == "PushContentToLayerForPlayer" for name, args in self.calls))
        self.assert_closed()

    def test_sync_push_is_owned_before_native_activate(self):
        self.sync = True; self.profile.K2_ActivateAbility(self.ability)
        self.assertIs(self.props[self.module.WIDGET], self.widget)
        self.assertIsNone(self.props[self.module.PENDING])
        self.assertIsNone(self.ability._uep_pressed_push)

    def test_completion_releases_proxy_scope_but_retains_widget_observation(self):
        self.pushed()
        self.assertEqual(self.module.snapshot()["scopes_created"], 2)
        self.assertEqual(self.module.snapshot()["scopes_closed"], 1)
        self.assertEqual(len(self.widget.listeners["BP_OnWidgetDeactivated"]), 2)
        self.assertTrue(self.active)

    def test_actual_widget_delegate_routes_virtual_method_to_native_end(self):
        self.pushed(); self.widget.call_function("DeactivateWidget")
        self.assertIn(("OnWidgetDeactivated", ()), self.calls)
        self.assertFalse(self.active)
        self.assertEqual(self.module.snapshot()["widget_deactivated"], 1)
        self.assert_closed()

    def test_ordinary_native_end_keeps_native_ui_and_removes_only_own_callback(self):
        self.pushed(); self.call("K2_EndAbility")
        self.assertTrue(self.widget_active)
        self.assertEqual(self.widget.listeners["BP_OnWidgetDeactivated"], [self.foreign])
        self.assertIsNone(self.props[self.module.WIDGET])
        self.assert_closed()

    def test_later_native_ui_close_cannot_end_ability_again(self):
        self.pushed(); self.call("K2_EndAbility")
        before = self.module.snapshot(); self.widget.call_function("DeactivateWidget")
        self.assertEqual(self.module.snapshot(), before)
        self.assertEqual(self.foreign_calls, 1)

    def test_end_pending_cancels_before_stale_completion_can_resurrect(self):
        self.profile.K2_ActivateAbility(self.ability)
        callback = self.action.listeners["AfterPush"][0]
        self.call("K2_EndAbility"); callback(self.widget)
        self.assertIsNone(self.props[self.module.WIDGET])
        self.assertEqual(self.module.snapshot()["pending_cancelled"], 1)
        self.assert_closed()

    def test_pending_teardown_ends_and_cancels_without_router_callback(self):
        self.profile.K2_ActivateAbility(self.ability); self.module.teardown(self.ability)
        self.assertFalse(self.active)
        self.assertIn(("action-Cancel", ()), self.calls)
        self.assertFalse(self.props[self.module.GUARD])
        self.assert_closed()

    def test_active_teardown_disarms_python_and_exact_original_binding_before_ui_close(self):
        self.pushed(); self.widget.listeners["BP_OnWidgetDeactivated"].append(self.original)
        self.module.teardown(self.ability)
        self.assertFalse(self.active); self.assertFalse(self.widget_active)
        self.assertEqual(self.widget.listeners["BP_OnWidgetDeactivated"], [self.foreign])
        self.assertEqual(self.foreign_calls, 1)
        self.assert_closed()

    def test_repeated_teardown_native_ends_once(self):
        self.pushed(); self.module.teardown(self.ability); self.module.teardown(self.ability)
        self.assertEqual(sum(name == "K2_EndAbility" for name, args in self.calls), 1)
        self.assert_closed()

    def test_inactive_teardown_never_deactivates_native_ui_after_pool_reuse(self):
        self.pushed(); self.call("K2_EndAbility"); self.module.teardown(self.ability)
        self.assertTrue(self.widget_active)
        self.assertFalse(any(name == "DeactivateWidget" for name, args in self.calls))

    def test_fallback_uses_original_activation_and_deactivation_business(self):
        profile = self.module.LyraWidgetPressedBlueprintFallbackProfile
        profile.K2_ActivateAbility(self.ability); profile.OnWidgetDeactivated(self.ability)
        profile.NativeEnded(self.ability, False)
        self.assertEqual([name for name, args in self.calls], ["original-K2_ActivateAbility", "original-OnWidgetDeactivated"])
        self.assertEqual(self.module.snapshot()["fallback_native_ends"], 1)

    def test_fallback_inactive_cleanup_only_unbinds_its_own_original_delegate(self):
        self.active = False; self.props[self.module.WIDGET] = self.widget
        self.widget.listeners["BP_OnWidgetDeactivated"].append(self.original)
        self.module.teardown(self.ability)
        self.assertTrue(self.widget_active)
        self.assertEqual(self.widget.listeners["BP_OnWidgetDeactivated"], [self.foreign])
        self.assertIsNone(self.props[self.module.WIDGET])


if __name__ == "__main__": unittest.main()
