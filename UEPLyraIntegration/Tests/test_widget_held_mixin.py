"""Held-widget call/lifetime models; not native UI/input/network acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Native:
    def __init__(self, call):
        self.listeners, self.call_function = {}, call


class Scope:
    def __init__(self):
        self.bindings, self.closed = [], False

    def bind_event(self, source, event, callback):
        if self.closed:
            raise RuntimeError("closed scope")
        source.listeners.setdefault(event, []).append(callback)
        self.bindings.append((source, event, callback))

    def close(self):
        if self.closed:
            return
        self.closed = True
        for source, event, callback in self.bindings:
            source.listeners[event] = [item for item in source.listeners[event] if item is not callback]


class HeldPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.active, self.end_on_ready, self.sync_push = [], True, False, False
        self.class_path = "/Native/UnloadedScoreboard.UnloadedScoreboard_C"
        self.props = {"Widget Class": None, "Layer Name": "original-native-layer", "UEPWidgetHeldTearingDown": False}
        self.controller = object()
        self.foreign = lambda *args: None
        self.widget = Native(lambda name, *args: self.calls.append((name, args)))
        self.state = Native(self.state_call)
        self.release = Native(lambda name, *args: self.calls.append(("release-" + name, args)))
        self.actions = []
        native, runtime, helper = [types.ModuleType(name) for name in
            ("unreal_engine", "uep_runtime", "uep_lyra_world.effect_pad_mixin")]
        runtime.SubscriptionScope, helper.valid = Scope, lambda value: value is not None
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=self.factory))
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_abilities/widget_held_mixin.py"
        spec = importlib.util.spec_from_file_location("widget_held_model", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime,
            "uep_lyra_world.effect_pad_mixin": helper}):
            spec.loader.exec_module(self.module)
        self.profile = self.module.LyraWidgetHeldPythonProfile
        self.ability = types.SimpleNamespace(call_function=self.call,
            get_property=lambda key: self.active if key == "bIsActive" else self.props.get(key),
            set_property=lambda key, value: self.props.__setitem__(key, value),
            get_path_name=lambda: "original-held-native-ability",
            call_mixin_original=lambda name: self.calls.append(("original-" + name, ())))
        self.profile.__init__(self.ability)

    @staticmethod
    def emit(source, event, *args):
        for callback in list(source.listeners.get(event, [])):
            callback(*args)

    def factory(self, name, *args):
        self.calls.append((name, args))
        if name == "StartAbilityState":
            return self.state
        if name == "WaitInputRelease":
            return self.release
        if name == "PushContentToLayerForPlayer":
            action = Native(lambda method, *params: self.action_call(action, method, *params))
            action.listeners["AfterPush"] = [self.foreign]
            self.actions.append(action)
            return action
        raise AssertionError(name)

    def call(self, name, *args):
        self.calls.append((name, args))
        if name == "GetLyraPlayerControllerFromActorInfo":
            return self.controller
        if name == self.module.CLASS_PATH:
            return self.class_path
        if name in ("CreateAndDisplayWidget", "RemoveWidget"):
            return getattr(self.profile, name)(self.ability, *args)
        if name == "K2_EndAbility":
            self.active = False
            if not self.props.get(self.module.GUARD):
                self.profile.NativeEnded(self.ability, False)

    def state_call(self, name, *args):
        self.calls.append(("state-" + name, args))
        if self.end_on_ready:
            self.call("K2_EndAbility")

    def action_call(self, action, name, *args):
        self.calls.append(("push-" + name, args))
        if name == "Activate" and self.sync_push:
            self.emit(action, "AfterPush", self.widget)

    def activate(self):
        self.profile.K2_ActivateAbility(self.ability)

    def assert_closed(self):
        stats = self.module.snapshot()
        self.assertEqual(stats["scopes_created"], stats["scopes_closed"])
        self.assertEqual(stats["active_count"], 0)

    def test_original_native_task_pins_and_order(self):
        self.activate()
        self.assertIn(("StartAbilityState", (self.ability, "ShowWidget_WhenInputHeld", True)), self.calls)
        self.assertIn(("WaitInputRelease", (self.ability, False)), self.calls)
        names = [name for name, args in self.calls]
        self.assertLess(names.index("state-ReadyForActivation"), names.index("CreateAndDisplayWidget"))
        self.assertLess(names.index("push-Activate"), names.index("WaitInputRelease"))

    def test_unloaded_soft_class_uses_original_path_and_native_unsuspended_push(self):
        self.activate()
        self.assertIn(("PushContentToLayerForPlayer", (self.controller, self.class_path, "original-native-layer", False)), self.calls)
        self.assertIsNone(self.props["Widget Class"])

    def test_empty_soft_class_fails_before_native_error_and_cleans(self):
        self.class_path = ""
        with self.assertRaisesRegex(RuntimeError, "configured Widget Class"):
            self.activate()
        self.assertFalse(any(name == "PushContentToLayerForPlayer" for name, args in self.calls))
        self.assertFalse(self.active)
        self.assert_closed()

    def test_after_push_closes_only_completed_push_scope_while_still_held(self):
        self.activate()
        self.emit(self.actions[0], "AfterPush", self.widget)
        self.assertIs(self.props["SpawnedWidget"], self.widget)
        self.assertIsNone(self.props["Async Action"])
        self.assertEqual(self.actions[0].listeners["AfterPush"], [self.foreign])
        self.assertTrue(self.active)
        self.assertEqual(self.module.snapshot()["scopes_closed"], 1)
        self.assertEqual(self.module.snapshot()["active_count"], 1)

    def test_synchronous_native_push_is_already_owned_before_activate(self):
        self.sync_push = True
        self.activate()
        self.assertIs(self.props["SpawnedWidget"], self.widget)
        self.assertIsNone(self.ability._uep_widget_push)
        self.assertIsNone(self.props["Async Action"])
        self.assertTrue(self.release.listeners["OnRelease"])

    def test_cached_widget_does_not_request_another_push(self):
        self.activate()
        self.emit(self.actions[0], "AfterPush", self.widget)
        self.profile.CreateAndDisplayWidget(self.ability)
        self.assertEqual(len(self.actions), 1)
        self.assertEqual(self.module.snapshot()["cached_widget_skips"], 1)

    def test_repeated_pending_request_cancels_only_previous_owned_action(self):
        self.activate()
        self.profile.CreateAndDisplayWidget(self.ability)
        self.assertEqual(len(self.actions), 2)
        self.assertEqual(self.module.snapshot()["pending_cancelled"], 1)
        self.assertIs(self.props["Async Action"], self.actions[1])
        self.assertEqual(self.actions[0].listeners["AfterPush"], [self.foreign])

    def test_stale_completion_cannot_resurrect_removed_widget(self):
        self.activate()
        callback = self.actions[0].listeners["AfterPush"][-1]
        self.profile.RemoveWidget(self.ability)
        callback(self.widget)
        self.assertIsNone(self.props["SpawnedWidget"])
        self.assertEqual(self.module.snapshot()["widgets_pushed"], 0)

    def test_cancel_disarms_owned_completion_before_native_reentry(self):
        self.activate()
        action = self.actions[0]
        action.call_function = lambda name: self.emit(action, "AfterPush", self.widget)
        self.profile.RemoveWidget(self.ability)
        self.assertIsNone(self.props["SpawnedWidget"])
        self.assertIsNone(self.props["Async Action"])
        self.assertEqual(action.listeners["AfterPush"], [self.foreign])

    def test_state_end_removes_widget_but_does_not_end_ability(self):
        self.activate()
        self.emit(self.actions[0], "AfterPush", self.widget)
        self.emit(self.state, "OnStateEnded")
        self.assertTrue(self.active)
        self.assertIsNone(self.props["SpawnedWidget"])
        self.assertIn(("DeactivateWidget", ()), self.calls)
        self.assertEqual(self.module.snapshot()["state_ended"], 1)

    def test_state_interrupt_cancels_pending_without_ending_ability(self):
        self.activate()
        self.emit(self.state, "OnStateInterrupted")
        self.assertTrue(self.active)
        self.assertIsNone(self.props["Async Action"])
        self.assertEqual(self.module.snapshot()["state_interrupted"], 1)

    def test_release_native_end_cleans_both_scopes_and_widget(self):
        self.activate()
        self.emit(self.actions[0], "AfterPush", self.widget)
        self.emit(self.release, "OnRelease", .3)
        self.assertFalse(self.active)
        self.assertIsNone(self.props["SpawnedWidget"])
        self.assertFalse(self.release.listeners["OnRelease"])
        self.assert_closed()

    def test_external_native_end_does_not_fall_through_to_bp(self):
        self.activate()
        self.active = False
        self.assertFalse(self.profile.NativeEnded(self.ability, True))
        self.assertIsNone(self.props["Async Action"])
        self.assert_closed()

    def test_synchronous_state_end_never_creates_widget_or_release_task_after_end(self):
        self.end_on_ready = True
        self.activate()
        self.assertFalse(self.active)
        self.assertFalse(self.actions)
        self.assertFalse(any(name == "WaitInputRelease" for name, args in self.calls))
        self.assert_closed()

    def test_teardown_idempotent_and_only_native_ends_once(self):
        self.activate()
        self.module.teardown(self.ability)
        self.module.teardown(self.ability)
        self.assertEqual(sum(name == "K2_EndAbility" for name, args in self.calls), 1)
        self.assertFalse(self.props[self.module.GUARD])
        self.assert_closed()

    def test_fallback_delegates_to_original_bp_and_allows_original_end(self):
        profile = self.module.LyraWidgetHeldBlueprintFallbackProfile
        profile.K2_ActivateAbility(self.ability)
        profile.CreateAndDisplayWidget(self.ability)
        profile.RemoveWidget(self.ability)
        self.assertTrue(profile.NativeEnded(self.ability, False))
        self.assertEqual([name for name, args in self.calls],
            ["original-K2_ActivateAbility", "original-CreateAndDisplayWidget", "original-RemoveWidget"])


if __name__ == "__main__":
    unittest.main()
