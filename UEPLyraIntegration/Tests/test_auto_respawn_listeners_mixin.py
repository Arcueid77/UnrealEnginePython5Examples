"""Listener policy models; native delegates/lifetimes need separate UE evidence."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class AutoRespawnListenerModels(unittest.TestCase):
    def setUp(self):
        self.avatar, self.health, self.old_avatar, self.old_health = (object() for _ in range(4))
        self.values = dict(LastBoundAvatarActor=self.old_avatar, LastBoundHealthComponent=self.old_health)
        self.calls = []
        ue = types.ModuleType("unreal_engine")
        ue.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=self.lookup))
        helpers = types.ModuleType("uep_lyra_abilities.auto_respawn_helpers_mixin")
        class HelperBase:
            def GetOwningPlayerState(self): pass
            def IsAvatarDeadOrDying(self): pass
            IsAvatarDeadOrDying.override = "Is Avatar Dead or Dying"
            IsAvatarDeadOrDying.uep_named_outputs = True
            def EndDeathAbilities(self, AbilitySystem): pass
        helpers.LyraAutoRespawnHelpersPythonProfile = helpers.LyraAutoRespawnHelpersBlueprintFallbackProfile = HelperBase
        self.helper_base = HelperBase
        valid = types.ModuleType("uep_lyra_world.effect_pad_mixin"); valid.valid = lambda value: value is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_listeners_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_abilities._listener_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": ue, helpers.__name__: helpers, valid.__name__: valid}):
            spec.loader.exec_module(self.module)
        self.profile = self.module.LyraAutoRespawnListenersPythonProfile
        self.ability = types.SimpleNamespace(call_function=self.call, get_property=self.values.get, set_property=self.set,
            call_mixin_original=lambda name: self.calls.append(("original", name)))

    def lookup(self, method, avatar):
        self.calls.append((method, avatar)); return self.health

    def set(self, name, value):
        self.calls.append(("set", name, value)); self.values[name] = value

    def call(self, method, *args):
        self.calls.append((method, *args))
        if method == "ClearDeathListener": self.profile.ClearDeathListener(self.ability)
        elif method == "GetAvatarActorFromActorInfo": return self.avatar

    def test_clear_removes_only_exact_old_targets_before_clearing_health(self):
        self.profile.ClearDeathListener(self.ability)
        self.assertEqual(self.calls, [(self.module.UNBIND_END, self.old_avatar),
            (self.module.UNBIND_DEATH, self.old_health), ("set", "LastBoundHealthComponent", None)])
        self.assertIs(self.values["LastBoundAvatarActor"], self.old_avatar)

    def test_bind_clears_old_before_looking_up_and_binding_new_targets(self):
        self.profile.BindDeathListener(self.ability)
        self.assertLess(self.calls.index((self.module.UNBIND_DEATH, self.old_health)), self.calls.index(("GetAvatarActorFromActorInfo",)))
        self.assertLess(self.calls.index(("set", "LastBoundAvatarActor", self.avatar)), self.calls.index((self.module.BIND_END, self.avatar)))
        self.assertLess(self.calls.index(("set", "LastBoundHealthComponent", self.health)), self.calls.index((self.module.BIND_DEATH, self.health)))
        self.assertIs(self.values["LastBoundAvatarActor"], self.avatar)
        self.assertIs(self.values["LastBoundHealthComponent"], self.health)

    def test_missing_avatar_still_clears_previous_listener_and_keeps_old_avatar_cache(self):
        self.avatar = None; self.profile.BindDeathListener(self.ability)
        self.assertIsNone(self.values["LastBoundHealthComponent"])
        self.assertIs(self.values["LastBoundAvatarActor"], self.old_avatar)
        self.assertFalse(any(row[0] in (self.module.BIND_END, self.module.BIND_DEATH, "FindHealthComponent") for row in self.calls))

    def test_missing_health_still_binds_actual_avatar_endplay(self):
        self.health = None; self.profile.BindDeathListener(self.ability)
        self.assertIn((self.module.BIND_END, self.avatar), self.calls)
        self.assertNotIn((self.module.BIND_DEATH, None), self.calls)
        self.assertIsNone(self.values["LastBoundHealthComponent"])

    def test_invalid_old_targets_are_not_passed_to_native_transport(self):
        self.values.update(LastBoundAvatarActor=None, LastBoundHealthComponent=None)
        self.profile.ClearDeathListener(self.ability)
        self.assertEqual(self.calls, [("set", "LastBoundHealthComponent", None)])

    def test_repeated_bind_clears_the_immediately_previous_targets(self):
        self.profile.BindDeathListener(self.ability); self.calls.clear()
        self.profile.BindDeathListener(self.ability)
        self.assertIn((self.module.UNBIND_END, self.avatar), self.calls)
        self.assertIn((self.module.UNBIND_DEATH, self.health), self.calls)
        self.assertEqual(self.module.instance_snapshot(self.ability)["bind_calls"], 2)

    def test_fallback_invokes_the_real_original_bind_and_clear(self):
        profile = self.module.LyraAutoRespawnListenersBlueprintFallbackProfile
        profile.BindDeathListener(self.ability); profile.ClearDeathListener(self.ability)
        self.assertEqual(self.calls, [("original", "BindDeathListener"), ("original", "ClearDeathListener")])

    def test_other_instance_counters_are_isolated(self):
        self.profile.BindDeathListener(self.ability)
        self.assertEqual(self.module.instance_snapshot(types.SimpleNamespace()), {})
        snapshot = self.module.instance_snapshot(self.ability); snapshot["bind_calls"] = 99
        self.assertEqual(self.module.instance_snapshot(self.ability)["bind_calls"], 1)

    def test_profile_has_no_listener_or_ability_teardown_override(self):
        # Native named delegates keep targeting the same ability across Profiles.
        self.assertEqual({name for name in vars(self.profile) if not name.startswith("__")},
            {"BindDeathListener", "ClearDeathListener", "GetOwningPlayerState", "IsAvatarDeadOrDying", "EndDeathAbilities"})
        self.assertNotIn("__uep_mixin_teardown__", vars(self.profile))

    def test_reused_helpers_are_locally_registered_with_original_output_metadata(self):
        for profile in (self.profile, self.module.LyraAutoRespawnListenersBlueprintFallbackProfile):
            for method in ("GetOwningPlayerState", "IsAvatarDeadOrDying", "EndDeathAbilities"):
                self.assertIs(vars(profile)[method], getattr(self.helper_base, method))
            self.assertEqual(vars(profile)["IsAvatarDeadOrDying"].override, "Is Avatar Dead or Dying")
            self.assertIs(vars(profile)["IsAvatarDeadOrDying"].uep_named_outputs, True)
