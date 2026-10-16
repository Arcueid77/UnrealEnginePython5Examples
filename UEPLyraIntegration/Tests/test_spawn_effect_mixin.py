"""Spawn policy call/lifetime models, not native animation or GAS proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Scope:
    def __init__(self): self.callbacks, self.closed = [], False
    def bind_event(self, task, event, callback): self.callbacks.append((task, event, callback))
    def close(self): self.closed = True


class SpawnEffectPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.tasks, self.active, self.props = [], [], True, {}
        native, runtime, helper = (types.ModuleType(name) for name in ("unreal_engine", "uep_runtime", "uep_lyra_world.effect_pad_mixin"))
        runtime.SubscriptionScope = Scope; helper.valid = lambda value: value is not None
        native.load_class = lambda name: name
        def factory(name, *args, **kwargs):
            self.calls.append((name, args, kwargs))
            task = types.SimpleNamespace(call_function=lambda name: self.calls.append((name, (), {})))
            self.tasks.append(task); return task
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=factory))
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/spawn_effect_mixin.py"
        spec = importlib.util.spec_from_file_location("spawn_effect_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime, "uep_lyra_world.effect_pad_mixin": helper}): spec.loader.exec_module(self.module)
        self.controller = types.SimpleNamespace(call_function=lambda name, *args: self.calls.append((name, args, {})))
        self.asc = types.SimpleNamespace(call_function=self.asc_call)
        self.ability = types.SimpleNamespace(EnableInputAfterTimeFraction=.75,
            SpawnMontage=types.SimpleNamespace(call_function=lambda name: 2.75), call_function=self.call,
            get_path_name=lambda: "native-spawn", get_property=lambda key: self.active if key == "bIsActive" else self.props.get(key),
            set_property=self.set_property, call_mixin_original=lambda *args: self.calls.append(("original", args, {})))
        self.module.LyraSpawnEffectPythonProfile.__init__(self.ability)

    def set_property(self, key, value): self.props[key] = value; setattr(self.ability, key, value)

    def asc_call(self, name, *args):
        self.calls.append((name, args, {}))
        return "original-context" if name == "MakeEffectContext" else "own-native-effect-handle"

    def call(self, name, *args):
        self.calls.append((name, args, {}))
        if name == "GetControllerFromActorInfo": return self.controller
        if name == "GetAbilitySystemComponentFromActorInfo": return self.asc
        if name in ("DisableInput", "EnableInputAgain"): return getattr(self.module.LyraSpawnEffectPythonProfile, name)(self.ability)
        if name == "K2_EndAbility":
            self.active = False
            if not self.props.get(self.module.GUARD): self.module.LyraSpawnEffectPythonProfile.NativeEnded(self.ability, False)

    def test_exact_original_level_context_timer_and_montage_pins(self):
        self.module.activate(self.ability)
        apply = next(args for name, args, kw in self.calls if name == "BP_ApplyGameplayEffectToSelf")
        self.assertEqual(apply, (self.module.EFFECT, 0., "original-context"))
        self.assertEqual([args[1] for name, args, kw in self.calls if name == "WaitDelay"], [2.75, 2.0625])
        montage = next(kw for name, args, kw in self.calls if name == "CreatePlayMontageAndWaitProxy")
        self.assertFalse(montage["bStopWhenAbilityEnds"]); self.assertEqual(montage["Rate"], 1.)
        self.assertEqual(len(self.tasks), 3)

    def test_input_delay_unlocks_once_while_effect_and_ability_stay_active(self):
        self.module.activate(self.ability)
        self.ability._uep_spawn_scope.callbacks[1][2]()
        self.module.enable_input(self.ability); self.module.enable_input(self.ability)
        self.assertTrue(self.active); self.assertTrue(self.ability._uep_spawn_effect_live)
        self.assertEqual((self.module.snapshot()["movement_locks"], self.module.snapshot()["movement_unlocks"]), (1, 1))

    def test_duration_or_montage_end_closes_scope_and_removes_only_own_handle(self):
        self.module.activate(self.ability); scope = self.ability._uep_spawn_scope
        scope.callbacks[0][2]()
        self.assertTrue(scope.closed); self.assertFalse(self.active)
        self.module.LyraSpawnEffectPythonProfile.NativeEnded(self.ability, False)
        removes = [args for name, args, kw in self.calls if name == "BP_RemoveGameplayEffectFromOwnerWithHandle"]
        self.assertEqual(removes, [("own-native-effect-handle", -1)])
        self.assertEqual(self.module.snapshot()["movement_unlocks"], 1)

    def test_interrupt_cancel_outputs_remain_disconnected(self):
        self.module.activate(self.ability)
        self.assertEqual([event for task, event, callback in self.ability._uep_spawn_scope.callbacks], ["OnFinish", "OnFinish", "OnCompleted"])

    def test_teardown_is_guarded_and_balanced(self):
        self.module.activate(self.ability); scope = self.ability._uep_spawn_scope
        self.module.teardown(self.ability)
        self.assertTrue(scope.closed); self.assertFalse(self.active); self.assertFalse(self.props[self.module.GUARD])
        stats = self.module.snapshot()
        self.assertEqual((stats["scopes_created"], stats["scopes_closed"], stats["active_count"]), (1, 1, 0))
        self.assertEqual((stats["effects_removed"], stats["movement_unlocks"], stats["native_ends"]), (1, 1, 0))

    def test_normal_python_activation_has_exactly_two_idempotent_enable_entries(self):
        self.module.activate(self.ability)
        self.ability._uep_spawn_scope.callbacks[1][2]()
        self.assertTrue(self.active)
        self.call("K2_EndAbility")
        self.assertEqual(self.module.instance_snapshot(self.ability)["enable_requests"], 2)
        self.assertEqual(self.module.snapshot()["movement_unlocks"], 1)
