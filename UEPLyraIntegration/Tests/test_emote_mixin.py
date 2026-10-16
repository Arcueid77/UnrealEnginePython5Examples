"""Bounded Emote call/lifetime models, not native montage/network acceptance."""
import importlib.util
import math
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


class EmotePolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.active, self.crouched, self.fail_ready = [], True, False, False
        self.props = {"Montage to Play": "original-native-montage"}
        native, runtime, helper = [types.ModuleType(name) for name in ("unreal_engine", "uep_runtime", "uep_lyra_world.effect_pad_mixin")]
        runtime.SubscriptionScope, helper.valid = Scope, lambda value: value is not None
        widgets, package = types.ModuleType("emote_model.widget_lifecycle"), types.ModuleType("emote_model")
        package.__path__ = []
        widgets.add_many = lambda value: self.calls.append(("add_many", (), {}))
        widgets.remove_many = lambda value: self.calls.append(("remove_many", (), {}))
        self.character = Native(self.character_call)
        self.character.get_property = lambda name: self.crouched
        self.task = Native(self.task_call)
        self.foreign = lambda *args: None
        self.character.listeners["OnCharacterMovementUpdated"] = [self.foreign]
        def factory(name, *args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "VSize":
                return math.sqrt(sum(value * value for value in args[0]))
            return self.task
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=factory))
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_abilities/emote_mixin.py"
        spec = importlib.util.spec_from_file_location("emote_model.policy", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime,
            "uep_lyra_world.effect_pad_mixin": helper, "emote_model": package, "emote_model.widget_lifecycle": widgets}):
            spec.loader.exec_module(self.module)
        self.ability = types.SimpleNamespace(call_function=self.call, get_property=self.get_property,
            set_property=lambda key, value: self.props.__setitem__(key, value), get_path_name=lambda: "native-emote")
        self.module.LyraEmotePythonProfile.__init__(self.ability)

    def get_property(self, name):
        return self.active if name == "bIsActive" else self.props.get(name)

    def call(self, name, *args):
        self.calls.append((name, args, {}))
        if name == "GetLyraCharacterFromActorInfo":
            return self.character
        if name == "CheckForMovement":
            return self.module.LyraEmotePythonProfile.CheckForMovement(self.ability, *args)
        if name == "K2_EndAbility":
            self.active = False
            if not self.props.get(self.module.GUARD):
                self.module.LyraEmotePythonProfile.NativeEnded(self.ability, False)

    def character_call(self, name, *args):
        self.calls.append((name, args, {}))
        if name == "UnCrouch":
            self.crouched = False
        elif name == "StopAnimMontage":
            self.emit(self.task, "OnInterrupted")

    def task_call(self, name):
        self.calls.append((name, (), {}))
        if self.fail_ready:
            self.emit(self.task, "OnCancelled")

    @staticmethod
    def emit(source, event, *args):
        for callback in list(source.listeners.get(event, [])):
            callback(*args)

    def test_original_native_montage_pins_and_three_end_outputs(self):
        self.module.activate(self.ability)
        row = next(kwargs for name, args, kwargs in self.calls if name == "CreatePlayMontageAndWaitProxy")
        self.assertEqual(row["MontageToPlay"], "original-native-montage")
        self.assertEqual((row["Rate"], row["bStopWhenAbilityEnds"], row["bAllowInterruptAfterBlendOut"]), (1., True, False))
        self.assertEqual(set(self.task.listeners), {"OnCompleted", "OnInterrupted", "OnCancelled"})

    def test_crouched_activation_only_native_uncrouch(self):
        self.crouched = True
        self.module.activate(self.ability)
        self.assertIn(("UnCrouch", (False,), {}), self.calls)
        self.assertEqual(self.module.snapshot()["uncrouches"], 1)

    def test_zero_old_velocity_keeps_emote_and_foreign_listener(self):
        self.module.activate(self.ability)
        self.emit(self.character, "OnCharacterMovementUpdated", .016, (1, 2, 3), (0, 0, 0))
        self.assertTrue(self.active)
        self.assertEqual(self.module.snapshot()["movement_stops"], 0)
        self.assertIn(self.foreign, self.character.listeners["OnCharacterMovementUpdated"])

    def test_actual_old_velocity_path_unbinds_only_own_movement_before_native_stop(self):
        self.module.activate(self.ability)
        self.emit(self.character, "OnCharacterMovementUpdated", .016, (1, 2, 3), (1, 0, 0))
        self.assertFalse(self.active)
        self.assertEqual(self.module.snapshot()["montage_interrupted"], 1)
        self.assertEqual(self.character.listeners["OnCharacterMovementUpdated"], [self.foreign])
        self.assertEqual((self.module.snapshot()["scopes_created"], self.module.snapshot()["scopes_closed"]), (2, 2))

    def test_crouch_alone_interrupts_at_zero_old_velocity(self):
        self.module.activate(self.ability); self.crouched = True
        self.emit(self.character, "OnCharacterMovementUpdated", .016, (0, 0, 0), (0, 0, 0))
        self.assertFalse(self.active)
        self.assertEqual(self.module.snapshot()["movement_stops"], 1)

    def test_natural_native_end_and_repeated_cleanup_leave_foreign_callbacks(self):
        self.module.activate(self.ability)
        self.emit(self.task, "OnCompleted")
        self.module.close(self.ability); self.module.close(self.ability)
        self.assertEqual(self.module.snapshot()["scopes_closed"], 2)
        self.assertEqual(self.character.listeners["OnCharacterMovementUpdated"], [self.foreign])

    def test_native_synchronous_task_failure_never_binds_after_end(self):
        self.fail_ready = True
        self.module.activate(self.ability)
        self.assertFalse(self.active)
        self.assertEqual(self.module.snapshot()["scopes_created"], 1)
        self.assertEqual(self.module.snapshot()["scopes_closed"], 1)
        self.assertEqual(self.character.listeners["OnCharacterMovementUpdated"], [self.foreign])

    def test_teardown_precisely_removes_original_binding_and_native_ends_once(self):
        self.module.activate(self.ability)
        self.module.teardown(self.ability); self.module.teardown(self.ability)
        self.assertFalse(self.active)
        self.assertEqual(sum(name == "K2_EndAbility" for name, args, kwargs in self.calls), 1)
        self.assertIn((self.module.REMOVE, (self.character,), {}), self.calls)
        self.assertEqual(self.character.listeners["OnCharacterMovementUpdated"], [self.foreign])
        self.assertFalse(self.props[self.module.GUARD])

    def test_fallback_requests_only_retained_bp_and_preserves_natural_end_behavior(self):
        profile = self.module.LyraEmoteBlueprintFallbackProfile
        self.assertTrue(profile.K2_ActivateAbility(self.ability))
        self.assertTrue(profile.CheckForMovement(self.ability, .016, (0, 0, 0), (2, 0, 0)))
        self.assertTrue(profile.NativeEnded(self.ability, False))
        self.assertFalse(self.calls)

    def test_explicit_local_widget_forwarders_keep_parent_native_registration(self):
        profile = self.module.LyraEmotePythonProfile
        profile.K2_OnAbilityAdded(self.ability); profile.K2_OnAbilityRemoved(self.ability)
        self.assertEqual([name for name, args, kwargs in self.calls], ["add_many", "remove_many"])


if __name__ == "__main__":
    unittest.main()
