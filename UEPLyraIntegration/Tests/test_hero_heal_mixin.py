"""Hero Heal native-call/scope models, not in-engine acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_heal_ability_mixin import Scope


class HeroHealPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.tasks, self.active, self.props = [], [], True, {}
        native, runtime, helpers = (types.ModuleType(name) for name in ("unreal_engine", "uep_runtime", "uep_lyra_world.effect_pad_mixin"))
        runtime.SubscriptionScope = Scope; helpers.valid = lambda value: value is not None
        native.FLinearColor = lambda *values: values
        def factory(name, *args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "PrintString": return
            value = types.SimpleNamespace(call_function=lambda name: self.calls.append((name, (), {})))
            self.tasks.append(value); return value
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=factory))
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/hero_heal_mixin.py"
        spec = importlib.util.spec_from_file_location("hero_heal_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime, "uep_lyra_world.effect_pad_mixin": helpers}): spec.loader.exec_module(self.module)
        self.controller = types.SimpleNamespace(call_function=lambda name, *args: self.calls.append((name, args, {})))
        self.asc = types.SimpleNamespace(call_function=lambda name, *args: self.calls.append((name, args, {})))
        self.ability = types.SimpleNamespace(GE_Heal="original-ge", HealMontage="original-montage", call_function=self.call,
            get_path_name=lambda: "native-hero-heal", get_property=lambda key: self.active if key == "bIsActive" else self.props.get(key),
            set_property=lambda key, value: self.props.__setitem__(key, value), call_mixin_original=lambda *args: True)
        self.module.LyraHeroHealPythonProfile.__init__(self.ability)

    def call(self, name, *args):
        self.calls.append((name, args, {}))
        if name == "GetControllerFromActorInfo": return self.controller
        if name == "GetLyraAbilitySystemComponentFromActorInfo": return self.asc
        if name == "K2_EndAbility":
            self.active = False
            if not self.props.get(self.module.GUARD): self.module.LyraHeroHealPythonProfile.NativeEnded(self.ability, False)

    def test_native_task_pins_and_original_effect_apply(self):
        self.module.activate(self.ability)
        self.assertEqual(len(self.tasks), 3)
        factories = {name: (args, kwargs) for name, args, kwargs in self.calls}
        self.assertEqual(factories["StartAbilityState"][0], (self.ability, "HealAbility", True))
        self.assertTrue(factories["CreatePlayMontageAndWaitProxy"][1]["bStopWhenAbilityEnds"])
        self.assertEqual(factories["CreatePlayMontageAndWaitProxy"][1]["MontageToPlay"], "original-montage")
        self.assertEqual(factories["WaitInputPress"][0], (self.ability, False))
        self.assertEqual(factories["BP_ApplyGameplayEffectToOwner"][0], ("original-ge", 1, 1))

    def test_native_montage_blend_closes_all_and_skips_bp_cleanup(self):
        self.module.activate(self.ability); scope = self.ability._uep_hero_heal_scope
        scope.callbacks["OnBlendOut"]()
        self.assertFalse(self.active); self.assertTrue(scope.closed)
        self.assertFalse(self.module.LyraHeroHealPythonProfile.NativeEnded(self.ability, False))
        stats = self.module.snapshot()
        self.assertEqual((stats["movement_locks"], stats["movement_unlocks"]), (1, 1))
        removes = [args for name, args, kw in self.calls if name == "RemoveActiveGameplayEffectBySourceEffect"]
        self.assertEqual(removes, [("original-ge", None, -1)])

    def test_state_end_releases_effects_without_ending_ability(self):
        self.module.activate(self.ability)
        self.ability._uep_hero_heal_scope.callbacks["OnStateEnded"]()
        self.assertTrue(self.active); self.assertEqual(self.module.snapshot()["movement_unlocks"], 1)
        self.call("K2_EndAbility")
        self.assertEqual(self.module.snapshot()["movement_unlocks"], 1)

    def test_next_native_input_press_ends(self):
        self.module.activate(self.ability)
        self.ability._uep_hero_heal_scope.callbacks["OnPress"](.2)
        self.assertFalse(self.active); self.assertEqual(self.module.snapshot()["input_presses"], 1)

    def test_active_profile_teardown_native_end_is_guarded_and_balanced(self):
        self.module.activate(self.ability); scope = self.ability._uep_hero_heal_scope
        self.module.teardown(self.ability)
        self.assertTrue(scope.closed); self.assertFalse(self.active); self.assertFalse(self.props[self.module.GUARD])
        stats = self.module.snapshot(); self.assertEqual(stats["native_ends"], 0)
        self.assertEqual((stats["scopes_created"], stats["scopes_closed"], stats["active_count"]), (1, 1, 0))

    def test_fallback_native_end_runs_retained_bp_once(self):
        self.ability._uep_hero_heal_effects_live = True
        self.assertTrue(self.module.LyraHeroHealBlueprintFallbackProfile.NativeEnded(self.ability, False))
        self.module.teardown(self.ability)
        self.assertFalse(any(name == "SetIgnoreMoveInput" for name, args, kw in self.calls))
