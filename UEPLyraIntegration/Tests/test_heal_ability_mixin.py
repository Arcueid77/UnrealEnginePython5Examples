"""Isolated ordering/cleanup models; native GAS/Montage still need runtime proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_inventory_pad_mixin import Object


class Scope:
    def __init__(self):
        self.closed, self.callbacks = False, {}
    def bind_event(self, task, event, callback):
        self.callbacks[event] = callback
    def close(self):
        self.closed = True


class Timer:
    def __init__(self, callback):
        self.callback, self.cleared = callback, False
    def clear(self):
        self.cleared = True


class HealAbilityPolicy(unittest.TestCase):
    def setUp(self):
        native = types.ModuleType("unreal_engine")
        runtime = types.ModuleType("uep_runtime"); runtime.SubscriptionScope = Scope
        dependency = types.ModuleType("uep_lyra_world.effect_pad_mixin"); dependency.valid = lambda value: value is not None and value.is_valid()
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_world/heal_ability_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_world._heal_ability_policy", file)
        self.module = importlib.util.module_from_spec(spec)
        self.order, self.cost, self.commit = [], True, True
        self.task = Object("task", lambda name, *args: self.order.append(name))
        factory = Object("factory", lambda name, *args, **kwargs: self.create_task(name, kwargs))
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: factory)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime, "uep_lyra_world.effect_pad_mixin": dependency}):
            spec.loader.exec_module(self.module)
        self.ability = Object("ability", self.call)
        self.props = {"Heal Montage": "montage", "Heal Effect": "effect", "bIsActive": True}
        self.ability.get_property = self.props.get
        self.ability.set_property = lambda name, value: self.props.__setitem__(name, value)
        self.ability.get_path_name = lambda: "ability-path"
        self.ability.call_mixin_original = lambda *args: None
        self.ability.set_timer = self.set_timer
        self.avatar = Object("avatar")
        self.avatar.set_timer = self.set_timer
        self.module.LyraHealAbilityPythonProfile.__init__(self.ability)

    def create_task(self, name, kwargs):
        self.order.append(name); self.factory_kwargs = kwargs
        return self.task

    def set_timer(self, seconds, callback, loop):
        self.order.append("set_timer"); self.timer_args = seconds, loop
        self.timer = Timer(callback)
        return self.timer

    def call(self, name, *args):
        self.order.append(name)
        if name == "K2_CheckAbilityCost":
            return self.cost
        if name == "K2_CommitAbility":
            return self.commit
        if name == "GetAvatarActorFromActorInfo":
            return self.avatar
        if name in ("K2_EndAbility", "K2_CancelAbility"):
            self.props["bIsActive"] = False
            if not self.props.get(self.module.TEARING_DOWN):
                self.module.LyraHealAbilityPythonProfile.NativeEnded(self.ability, name == "K2_CancelAbility")

    def test_native_order_immediate_heal_and_exact_original_task_parameters(self):
        self.module.activate(self.ability)
        self.assertEqual(self.order, ["K2_CheckAbilityCost", "K2_CommitAbility", "CreatePlayMontageAndWaitProxy",
                                     "ReadyForActivation", "BP_ApplyGameplayEffectToOwner", "GetAvatarActorFromActorInfo", "set_timer"])
        self.assertEqual(self.factory_kwargs["bStopWhenAbilityEnds"], False)
        self.assertEqual(self.factory_kwargs["Rate"], 1.)
        self.assertEqual(self.timer_args, (1., False))
        self.assertEqual(set(self.ability._uep_heal_scope.callbacks), {"OnCompleted", "OnInterrupted", "OnCancelled"})
        self.assertEqual(self.module.snapshot()["heals"], 1)

    def test_failed_cost_or_commit_never_starts_montage_heal_or_timer(self):
        self.cost = False
        self.module.activate(self.ability)
        self.assertEqual(self.order, ["K2_CheckAbilityCost", "K2_EndAbility"])
        self.order.clear(); self.cost, self.commit = True, False
        self.module.activate(self.ability)
        self.assertEqual(self.order, ["K2_CheckAbilityCost", "K2_CommitAbility", "K2_EndAbility"])

    def test_native_montage_completion_closes_callbacks_and_cancels_timer(self):
        self.module.activate(self.ability)
        scope, timer = self.ability._uep_heal_scope, self.timer
        scope.callbacks["OnCompleted"]()
        self.assertTrue(scope.closed and timer.cleared)
        self.assertIsNone(self.ability._uep_heal_scope)
        self.assertEqual(self.module.snapshot()["completed"], 1)
        self.assertEqual(self.module.snapshot()["end_requests"], 1)
        self.assertEqual(self.module.snapshot()["active_count"], 0)

    def test_native_timer_callback_ends_and_clears_ownership(self):
        self.module.activate(self.ability)
        self.timer.callback()
        self.assertTrue(self.timer.cleared)
        self.assertEqual(self.module.snapshot()["timer_callbacks"], 1)
        self.assertEqual(self.module.snapshot()["timers_created"], self.module.snapshot()["timers_cleared"])

    def test_external_native_end_closes_scope_and_timer_idempotently(self):
        self.module.activate(self.ability)
        self.module.LyraHealAbilityPythonProfile.NativeEnded(self.ability, True)
        self.module.close(self.ability)
        self.assertTrue(self.timer.cleared)
        self.assertEqual(self.module.snapshot()["scopes_created"], self.module.snapshot()["scopes_closed"])

    def test_interrupted_and_cancelled_are_not_blend_out_completion(self):
        for event, reason in (("OnInterrupted", "interrupted"), ("OnCancelled", "cancelled")):
            self.props["bIsActive"] = True
            self.module.activate(self.ability)
            self.ability._uep_heal_scope.callbacks[event]()
            self.assertEqual(self.module.snapshot()[reason], 1)
        self.assertEqual(self.module.snapshot()["completed"], 0)

    def test_inactive_teardown_never_replays_native_cancel(self):
        self.props["bIsActive"] = False
        self.module.LyraHealAbilityPythonProfile.__uep_mixin_teardown__(self.ability)
        self.assertEqual(self.order, [])

    def test_active_teardown_cancels_native_ability_without_router_reentry(self):
        self.module.activate(self.ability)
        self.module.LyraHealAbilityPythonProfile.__uep_mixin_teardown__(self.ability)
        self.assertFalse(self.props[self.module.TEARING_DOWN])
        self.assertFalse(self.props["bIsActive"])
        self.assertTrue(self.timer.cleared)
        self.assertEqual(self.module.snapshot()["native_ends"], 0)
