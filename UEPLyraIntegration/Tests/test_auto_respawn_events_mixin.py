"""Death/restart policy models; native latent/RPC acceptance is separate."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class AutoRespawnEventModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.messages, self.authority, self.dedicated = [], [], True, False
        self.player_state, self.asc = object(), object()
        self.controller = types.SimpleNamespace(PlayerState=self.player_state)
        self.mode = types.SimpleNamespace(is_a=lambda cls: cls.name == "LyraGameMode",
            call_function=lambda name, *args: self.calls.append(("mode", name, *args)))
        self.state = types.SimpleNamespace(is_a=lambda cls: cls.name == "LyraGameState",
            call_function=lambda name, *args: self.calls.append(("state", name, *args)))
        self.values = dict(ControllerToReset=self.controller, ShouldFinishRestart=False)
        ue, structs = types.ModuleType("unreal_engine"), types.ModuleType("unreal_engine.structs")
        ue.find_class = lambda name: types.SimpleNamespace(name=name, get_cdo=lambda: types.SimpleNamespace(
            call_function=lambda method, *args: self.native(name, method, args)))
        ue.load_class = lambda path: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(
            call_function=lambda method, *args: self.messages.append((method, args))))
        structs.GameplayTag = structs.LyraInteractionDurationMessage = structs.LyraVerbMessage = types.SimpleNamespace
        parent = types.ModuleType("uep_lyra_abilities.auto_respawn_listeners_mixin")
        class Base:
            def GetOwningPlayerState(self): pass
            def IsAvatarDeadOrDying(self): pass
            IsAvatarDeadOrDying.override = "Is Avatar Dead or Dying"
            IsAvatarDeadOrDying.uep_named_outputs = True
            def EndDeathAbilities(self, AbilitySystem): pass
            def BindDeathListener(self): pass
            def ClearDeathListener(self): pass
        parent.LyraAutoRespawnListenersPythonProfile = parent.LyraAutoRespawnListenersBlueprintFallbackProfile = Base
        valid = types.ModuleType("uep_lyra_world.effect_pad_mixin"); valid.valid = lambda value: value is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_events_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_abilities._event_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": ue, structs.__name__: structs, parent.__name__: parent, valid.__name__: valid}):
            spec.loader.exec_module(self.module)
        self.ability = types.SimpleNamespace(call_function=self.call, set_property=self.set, get_property=self.values.get,
            RespawnDelayDuration=5., ShouldFinishRestart=False, call_mixin_original=lambda *args: self.calls.append(("original", *args)))
        self.profile = self.module.LyraAutoRespawnEventsPythonProfile

    def set(self, name, value):
        self.calls.append(("set", name, value)); self.values[name] = value; setattr(self.ability, name, value)

    def call(self, name, *args):
        self.calls.append((name, *args))
        if name == "GetControllerFromActorInfo": return self.controller
        if name == "GetOwningPlayerState": return self.player_state
        if name == "K2_HasAuthority": return self.authority

    def native(self, cls, method, args):
        self.calls.append((cls, method, *args))
        if method == "GetGameMode": return self.mode
        if method == "GetGameState": return self.state
        if method == "GetAbilitySystemComponent": return self.asc
        if method == "IsDedicatedServer": return self.dedicated
        if method == "GetGameInstanceSubsystem": return "router"
        raise AssertionError((cls, method))

    def test_death_clears_then_caches_and_broadcasts_exact_native_duration(self):
        self.profile.OnDeathStarted(self.ability, object())
        self.assertEqual(self.calls[:3], [("ClearDeathListener",), ("GetControllerFromActorInfo",), ("set", "ControllerToReset", self.controller)])
        method, args = self.messages[0]
        self.assertEqual(method, "BroadcastDuration"); self.assertEqual(args[1].TagName, self.module.DURATION)
        self.assertIs(args[2].Instigator, self.player_state); self.assertEqual(args[2].Duration, 5.)
        self.assertTrue(self.values["ShouldFinishRestart"]); self.assertIn((self.module.START_LONG,), self.calls)

    def test_missing_controller_has_no_duration_or_delay(self):
        self.controller = None; self.profile.OnDeathStarted(self.ability, None)
        self.assertEqual(self.messages, []); self.assertNotIn((self.module.START_LONG,), self.calls)

    def test_actual_ability_guard_not_actor_role_controls_long_delay(self):
        self.authority = False; self.profile.OnDeathStarted(self.ability, object())
        self.assertEqual(len(self.messages), 1); self.assertNotIn((self.module.START_LONG,), self.calls)

    def test_long_continuation_consumes_flag_before_death_end_and_native_short_delay(self):
        self.ability.ShouldFinishRestart = True
        self.assertIs(self.profile.AfterDeathDelay(self.ability), False)
        self.assertLess(self.calls.index(("set", "ShouldFinishRestart", False)), self.calls.index(("EndDeathAbilities", self.asc)))
        self.assertLess(self.calls.index(("EndDeathAbilities", self.asc)), self.calls.index((self.module.START_SHORT,)))

    def test_canceled_long_continuation_cannot_restart_again(self):
        self.assertIs(self.profile.AfterDeathDelay(self.ability), False)
        self.assertFalse(any(row[0] in ("EndDeathAbilities", self.module.START_SHORT) for row in self.calls))

    def test_short_continuation_restarts_then_reliably_sends_exact_completion(self):
        self.assertIs(self.profile.AfterRestartDelay(self.ability), False)
        restart = next(row for row in self.calls if row[:2] == ("mode", "RequestPlayerRestartNextFrame"))
        rpc = next(row for row in self.calls if row[:2] == ("state", "MulticastReliableMessageToClients"))
        self.assertEqual(restart[2:], (self.controller, True)); self.assertLess(self.calls.index(restart), self.calls.index(rpc))
        self.assertEqual(rpc[2].Verb.TagName, self.module.COMPLETED); self.assertEqual(rpc[2].Magnitude, 1.)
        self.assertIs(rpc[2].Instigator, self.player_state); self.assertEqual(self.messages[0][0], "BroadcastVerb")

    def test_dedicated_server_sends_rpc_but_no_cosmetic_local_completion(self):
        self.dedicated = True; self.profile.AfterRestartDelay(self.ability)
        self.assertEqual(self.messages, []); self.assertEqual(self.module.snapshot()["native_completion_rpcs"], 1)

    def test_client_without_gamemode_cannot_restart_or_send_rpc(self):
        self.mode = None; self.profile.AfterRestartDelay(self.ability)
        self.assertEqual(self.messages, []); self.assertEqual(self.module.snapshot()["native_restarts"], 0)
        self.assertFalse(any(row[0] == "state" for row in self.calls))

    def test_missing_gamestate_retains_original_cosmetic_fallback(self):
        self.state = None; self.profile.AfterRestartDelay(self.ability)
        self.assertEqual(self.messages[0][0], "BroadcastVerb"); self.assertEqual(self.module.snapshot()["native_completion_rpcs"], 0)

    def test_avatar_end_uses_short_path_without_death_duration(self):
        self.profile.OnAvatarEndPlay(self.ability, object(), 0)
        self.assertEqual(self.messages, []); self.assertIn((self.module.START_SHORT,), self.calls)
        self.assertNotIn((self.module.START_LONG,), self.calls); self.assertFalse(self.values["ShouldFinishRestart"])

    def test_avatar_end_requires_original_native_ability_authority(self):
        self.authority = False; self.profile.OnAvatarEndPlay(self.ability, object(), 0)
        self.assertEqual(self.calls, [("K2_HasAuthority",)])

    def test_bp_fallback_keeps_original_events_and_continuations(self):
        profile = self.module.LyraAutoRespawnEventsBlueprintFallbackProfile
        profile.OnDeathStarted(self.ability, "actor"); profile.OnAvatarEndPlay(self.ability, "actor", 2)
        self.assertEqual(self.calls, [("original", "OnDeathStarted", "actor"), ("original", "OnAvatarEndPlay", "actor", 2)])
        self.assertIs(profile.AfterDeathDelay(self.ability), True); self.assertIs(profile.AfterRestartDelay(self.ability), True)

    def test_nine_local_reflected_methods_keep_metadata_without_python_timer_ownership(self):
        for profile in (self.profile, self.module.LyraAutoRespawnEventsBlueprintFallbackProfile):
            methods = {name for name in vars(profile) if not name.startswith("__")}
            self.assertEqual(len(methods), 9); self.assertIn("BindDeathListener", methods); self.assertIn("GetOwningPlayerState", methods)
            self.assertIs(vars(profile)["IsAvatarDeadOrDying"].uep_named_outputs, True)
            self.assertEqual(profile.AfterDeathDelay.override, self.module.AFTER_LONG)
            self.assertEqual(profile.AfterRestartDelay.override, self.module.AFTER_SHORT)
            self.assertNotIn("__uep_mixin_teardown__", vars(profile))
