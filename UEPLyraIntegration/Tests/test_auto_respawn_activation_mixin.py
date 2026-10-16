"""Ability-owned reset/UI/cancellation policy models; not native acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class AutoRespawnActivationModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.owner, self.avatar = [], object(), object()
        self.authority, self.dead, self.has_ui = True, False, True
        self.proxy = types.SimpleNamespace(call_function=lambda name: self.calls.append(("proxy", name)))
        self.values = dict(UEPAutoRespawnResetProxy=self.proxy, UEPAutoRespawnRuntimeEnded=False,
            IsListeningForReset=False, ShouldFinishRestart=True, Extension="handle")
        ue, structs = types.ModuleType("unreal_engine"), types.ModuleType("unreal_engine.structs")
        ue.find_class = lambda name: types.SimpleNamespace(name=name, get_cdo=lambda: types.SimpleNamespace(
            call_function=lambda method, *args: self.native(name, method, args)))
        ue.load_class = lambda path: path
        structs.GameplayTag = structs.UIExtensionHandle = types.SimpleNamespace
        parent = types.ModuleType("uep_lyra_abilities.auto_respawn_events_mixin")
        class Base:
            def GetOwningPlayerState(self): pass
            def IsAvatarDeadOrDying(self): pass
            IsAvatarDeadOrDying.override = "Is Avatar Dead or Dying"
            IsAvatarDeadOrDying.uep_named_outputs = True
            def EndDeathAbilities(self, AbilitySystem): pass
            def BindDeathListener(self): pass
            def ClearDeathListener(self): pass
            def OnDeathStarted(self, DyingActor): pass
            def OnAvatarEndPlay(self, Actor, EndPlayReason): pass
            def AfterDeathDelay(self): return "base-long"
            def AfterRestartDelay(self): return "base-short"
        parent.LyraAutoRespawnEventsPythonProfile = parent.LyraAutoRespawnEventsBlueprintFallbackProfile = Base
        parent.AFTER_LONG, parent.AFTER_SHORT = "UEPAutoRespawnAfterDeathDelay", "UEPAutoRespawnAfterRestartDelay"
        parent.end_death_and_wait = lambda ability: self.calls.append(("end-death-and-wait",))
        valid = types.ModuleType("uep_lyra_world.effect_pad_mixin"); valid.valid = lambda obj: obj is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_activation_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_abilities._activation_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": ue, structs.__name__: structs, parent.__name__: parent, valid.__name__: valid}):
            spec.loader.exec_module(self.module)
        self.ability = types.SimpleNamespace(call_function=self.call, get_property=self.get, set_property=self.set,
            call_mixin_original=lambda *args: self.calls.append(("original", *args)), Extension="handle", IsListeningForReset=False)
        self.profile = self.module.LyraAutoRespawnActivationPythonProfile

    def get(self, name): return self.values[name]
    def set(self, name, value):
        self.calls.append(("set", name, value)); self.values[name] = value; setattr(self.ability, name, value)
    def call(self, name, *args):
        self.calls.append((name, *args))
        if name in ("GetOwningPlayerState", "GetOwningActorFromActorInfo"): return self.owner
        if name == "GetAvatarActorFromActorInfo": return self.avatar
        if name == "Is Avatar Dead or Dying": return (self.dead,)
        if name == "K2_HasAuthority": return self.authority
        if name == "GetControllerFromActorInfo": return "controller"
    def native(self, cls, method, args):
        self.calls.append((cls, method, *args))
        if method == "GetWorldSubsystem":
            return types.SimpleNamespace(call_function=lambda name, *args: self.calls.append(("ui", name, *args)) or "new-handle") if self.has_ui else None

    def test_added_registers_original_ui_class_slot_owner_priority(self):
        self.profile.K2_OnAbilityAdded(self.ability)
        call = next(row for row in self.calls if row[0] == "ui")
        self.assertEqual(call[1], "K2_RegisterExtensionAsWidgetForContext")
        self.assertEqual(call[2].TagName, "HUD.Slot.Reticle"); self.assertEqual(call[3], self.module.WIDGET)
        self.assertEqual(call[4:], (self.owner, -1)); self.assertEqual(self.values["Extension"], "new-handle")

    def test_absent_ui_subsystem_does_not_register(self):
        self.has_ui = False; self.profile.K2_OnAbilityAdded(self.ability)
        self.assertFalse(any(row[0] == "ui" for row in self.calls))

    def test_activation_and_avatar_set_share_one_native_reset_registration(self):
        self.profile.K2_ActivateAbility(self.ability); self.profile.K2_OnPawnAvatarSet(self.ability)
        self.assertEqual(self.calls.count((self.module.START_RESET,)), 1)
        self.assertEqual(self.calls.count(("BindDeathListener",)), 2)
        self.assertTrue(self.values["IsListeningForReset"])

    def test_native_dead_avatar_uses_actual_death_entry(self):
        self.dead = True; self.profile.K2_OnPawnAvatarSet(self.ability)
        self.assertIn(("OnDeathStarted", self.avatar), self.calls); self.assertNotIn(("BindDeathListener",), self.calls)

    def test_foreign_reset_cannot_clear_listeners_or_restart(self):
        self.assertIs(self.profile.ResetMessage(self.ability, object()), False)
        self.assertNotIn(("ClearDeathListener",), self.calls); self.assertNotIn(("end-death-and-wait",), self.calls)
        self.assertEqual(self.module.snapshot()["foreign_resets"], 1)

    def test_owner_reset_requires_native_ability_authority(self):
        self.authority = False; self.profile.ResetMessage(self.ability, self.owner)
        self.assertNotIn(("end-death-and-wait",), self.calls)

    def test_owner_reset_uses_native_controller_and_short_restart_path(self):
        self.assertIs(self.profile.ResetMessage(self.ability, self.owner), False)
        self.assertEqual(self.values["ControllerToReset"], "controller"); self.assertFalse(self.values["ShouldFinishRestart"])
        self.assertLess(self.calls.index(("ClearDeathListener",)), self.calls.index(("end-death-and-wait",)))

    def test_end_disarms_before_cancel_and_forwards_parent_only(self):
        self.assertIs(self.profile.EndGate(self.ability), False)
        self.assertTrue(self.values[self.module.ENDED]); self.assertFalse(self.values["ShouldFinishRestart"])
        self.assertLess(self.calls.index(("set", self.module.PROXY, None)), self.calls.index(("proxy", "Cancel")))
        self.assertFalse(self.values["IsListeningForReset"]); self.assertIn(("ClearDeathListener",), self.calls)
        self.assertNotIn(("K2_EndAbility",), self.calls)

    def test_removed_disarms_even_an_inactive_ability_ui_and_listener(self):
        self.profile.K2_OnAbilityRemoved(self.ability)
        self.assertTrue(self.values[self.module.ENDED]); self.assertIsNone(self.values[self.module.PROXY])
        self.assertIn(("ClearDeathListener",), self.calls)
        self.assertTrue(any(row[:2] == ("UIExtensionHandleFunctions", "Unregister") for row in self.calls))

    def test_repeated_cleanup_cannot_cancel_the_old_proxy_twice(self):
        self.module.cleanup(self.ability); self.module.cleanup(self.ability)
        self.assertEqual(self.calls.count(("proxy", "Cancel")), 1)

    def test_ended_long_and_short_continuations_cannot_restart(self):
        for profile in (self.profile, self.module.LyraAutoRespawnActivationBlueprintFallbackProfile):
            self.values[self.module.ENDED] = True
            self.assertIs(profile.AfterDeathDelay(self.ability), False); self.assertIs(profile.AfterRestartDelay(self.ability), False)

    def test_live_continuations_keep_existing_event_policy(self):
        self.assertEqual(self.profile.AfterDeathDelay(self.ability), "base-long")
        self.assertEqual(self.profile.AfterRestartDelay(self.ability), "base-short")

    def test_profile_handoff_does_not_own_teardown_or_cancel_the_listener(self):
        for profile in (self.profile, self.module.LyraAutoRespawnActivationBlueprintFallbackProfile):
            self.assertNotIn("__uep_mixin_teardown__", vars(profile))
            self.assertEqual(len([name for name in vars(profile) if not name.startswith("__")]), 16)
            self.assertIs(vars(profile)["IsAvatarDeadOrDying"].uep_named_outputs, True)

    def test_fallback_keeps_original_registration_but_shared_safe_removal(self):
        profile = self.module.LyraAutoRespawnActivationBlueprintFallbackProfile
        profile.K2_OnAbilityAdded(self.ability); profile.K2_ActivateAbility(self.ability); profile.K2_OnPawnAvatarSet(self.ability)
        self.assertIs(profile.ResetSubscribed(self.ability), True); self.assertIs(profile.ResetMessage(self.ability, self.owner), True)
        self.assertIs(profile.EndGate(self.ability), True)
        profile.K2_OnAbilityRemoved(self.ability)
        self.assertIn(("original", "K2_OnAbilityRemoved"), self.calls)

    def test_ended_profile_rejects_reset_callback(self):
        self.values[self.module.ENDED] = True
        self.assertIs(self.profile.ResetMessage(self.ability, self.owner), False)
        self.assertIs(self.module.LyraAutoRespawnActivationBlueprintFallbackProfile.ResetMessage(self.ability, self.owner), False)
        self.assertNotIn(("end-death-and-wait",), self.calls)

    def test_optional_invalid_native_proxy_does_not_hide_other_errors(self):
        self.ability.get_property = lambda name: (_ for _ in ()).throw(RuntimeError("uobject is in invalid state"))
        self.module.cancel_reset(self.ability)
        self.assertFalse(self.values["IsListeningForReset"])
        self.ability.get_property = lambda name: (_ for _ in ()).throw(RuntimeError("different failure"))
        with self.assertRaisesRegex(RuntimeError, "different failure"): self.module.cancel_reset(self.ability)
