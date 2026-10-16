import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class DashCooldownContracts(unittest.TestCase):
    def setUp(self):
        self.calls, self.clock = [], 100.5
        native = types.ModuleType("unreal_engine")
        self.native_call = lambda name, *args: args[0] / args[1] if name == "Divide_DoubleDouble" and args[1] else 0.0
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=self.native_call))
        runtime = types.ModuleType("uep_runtime")
        self.scopes = []
        owner = self

        class Scope:
            def __init__(self):
                self.closed, self.bindings = False, []
                owner.scopes.append(self)

            def bind_event(self, source, event, callback):
                self.bindings.append((source, event, callback))

            def close(self):
                self.closed = True

        runtime.SubscriptionScope = Scope
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None
        progress = types.ModuleType("uep_lyra_hud.ability_progress_mixin")
        progress.game_time = lambda widget: self.clock
        pools = types.ModuleType("uep_lyra_hud.pooled_widget_lifetime")
        pools.refresh = lambda: None
        pools.unwatch = lambda widget: None
        pools.may_activate = lambda widget: True
        pools.watch = lambda widget, callback: None
        pools.snapshot = lambda: {}
        source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/dash_cooldown_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._dash_contract", source)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime,
                                     "uep_lyra_hud.weapon_observer": observer,
                                     "uep_lyra_hud.pooled_widget_lifetime": pools,
                                     "uep_lyra_hud.ability_progress_mixin": progress}):
            spec.loader.exec_module(self.module)
        self.widget = self.module.LyraDashCooldownPythonProfile()
        self.pawn = types.SimpleNamespace(call_function=lambda *args: self.health)
        self.controller = types.SimpleNamespace(call_function=lambda *args: self.pawn)
        self.dead = False
        self.health = types.SimpleNamespace(get_path_name=lambda: "health", call_function=lambda *args: self.dead)
        self.widget.CurrentHealthComponent, self.widget.NewHealthComponent = None, None
        self.widget.Duration, self.widget.StartTime, self.widget.Charging = 2.0, 100.0, True
        self.widget.InactiveToActive, self.widget.ActiveToInactive = "active", "inactive"
        self.playing = False

        def call(name, *args):
            self.calls.append((name,) + args)
            if name == "GetOwningPlayerPawn":
                return self.pawn
            if name == "GetOwningPlayer":
                return self.controller
            if name == "IsAnimationPlaying":
                return self.playing
            if hasattr(self.widget, name):
                return getattr(self.widget, name)(*args)

        self.widget.call_function = call
        material = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        self.widget.BarGlow = self.widget.BarFill = types.SimpleNamespace(call_function=lambda *args: material)
        self.widget.CenteringOvr = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        self.module.start = lambda widget: setattr(widget, "_uep_dash_scope", object())

    def test_owner_duration_has_authored_order(self):
        self.playing = True
        self.module.received(self.widget, types.SimpleNamespace(Instigator=self.pawn, Duration=3.0))
        self.assertEqual((self.widget.Duration, self.widget.StartTime, self.widget.Charging), (3.0, 100.5, True))
        self.assertLess(self.calls.index(("StopAnimation", "active")), self.calls.index(("UpdateCooldownPercent", 0.0)))
        self.assertLess(self.calls.index(("UpdateCooldownPercent", 0.0)), self.calls.index(("PlayAnimationForward", "inactive", 1.0, False)))

    def test_foreign_is_ignored_and_null_equality_retained(self):
        self.module.received(self.widget, types.SimpleNamespace(Instigator=object(), Duration=3.0))
        self.assertEqual(self.widget.Duration, 2.0)

        self.assertEqual(self.widget._uep_dash_foreign, 1)
        self.pawn = None
        self.module.received(self.widget, types.SimpleNamespace(Instigator=None, Duration=3.0))
        self.assertEqual(self.widget.Duration, 3.0)

    def test_live_profile_teardown_keeps_unowned_native_animation_playing(self):
        self.widget.__uep_mixin_teardown__()
        self.assertFalse(any(call[0] in ("PauseAnimation", "StopAnimation", "StopAllAnimations") for call in self.calls))

    def test_inactive_pool_tick_never_rebinds_health(self):
        self.module.start = lambda widget: None
        self.widget.Tick(None, 0.1)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.scopes, [])

    def test_both_materials_and_completion(self):
        self.widget.Tick(None, 99.0)
        self.assertEqual(self.calls.count(("SetScalarParameterValue", "AnimateArcFill", 0.25)), 2)
        self.clock = 102.0
        self.widget.Tick(None, 0.0)
        self.assertFalse(self.widget.Charging)
        self.assertIn(("PlayAnimationForward", "active", 1.0, False), self.calls)

    def test_pause_uses_native_game_time_not_delta(self):
        self.widget.Tick(None, 0.0)
        self.widget.Tick(None, 80.0)
        self.assertEqual(self.calls.count(("SetScalarParameterValue", "AnimateArcFill", 0.25)), 4)

    def test_invalid_pawn_does_not_clear_current_or_update_visibility(self):
        self.widget.CurrentHealthComponent = self.health
        self.pawn = None
        self.widget.OnCheckForDeath()
        self.assertIs(self.widget.CurrentHealthComponent, self.health)
        self.assertIsNone(self.widget.NewHealthComponent)
        self.assertNotIn(("UpdateVisibility",), self.calls)

    def test_native_health_binding_is_one_shot_until_new_component(self):
        self.widget.OnCheckForDeath()
        self.widget.OnCheckForDeath()
        self.assertEqual(len(self.scopes), 1)
        self.dead = True
        self.widget.OnDeathStarted(self.pawn)
        self.assertTrue(self.scopes[0].closed)
        self.assertIn(("SetVisibility", 1), self.calls)
        self.widget.OnCheckForDeath()
        self.assertEqual(len(self.scopes), 1)

    def test_new_component_does_not_silently_change_original_old_binding_policy(self):
        self.widget.OnCheckForDeath()
        self.health = types.SimpleNamespace(get_path_name=lambda: "new", call_function=lambda *args: False)
        self.widget.OnCheckForDeath()
        self.assertEqual(len(self.scopes), 2)
        self.assertFalse(self.scopes[0].closed)
        self.assertEqual(set(self.widget._uep_dash_health), {"health", "new"})

    def test_visibility_exact_native_enum(self):
        self.widget.UpdateVisibility()
        self.assertIn(("SetVisibility", 1), self.calls)
        self.widget.CurrentHealthComponent = self.health
        self.widget.UpdateVisibility()
        self.assertIn(("SetVisibility", 3), self.calls)

    def test_resume_does_not_replay_or_change_model(self):
        self.module.start = lambda widget: self.calls.append(("start",))
        self.widget.ResumeObservation()
        self.assertEqual(self.calls, [("start",)])
        self.assertEqual((self.widget.Duration, self.widget.StartTime), (2.0, 100.0))

    def test_teardown_disarms_all_scopes_without_resetting_native_model(self):
        self.widget.OnCheckForDeath()
        helper = types.SimpleNamespace(remove_from_root=lambda: self.calls.append(("unroot",)))
        self.widget._uep_dash_reader = helper
        self.widget._uep_dash_scope = self.module.SubscriptionScope()
        self.module._stats["scopes_created"] += 1
        self.widget.__uep_mixin_teardown__()
        self.widget.__uep_mixin_teardown__()
        self.assertTrue(all(scope.closed for scope in self.scopes))
        self.assertEqual(self.calls.count(("unroot",)), 1)
        self.assertEqual(self.module._stats["scopes_created"], self.module._stats["scopes_closed"])
        self.assertEqual(self.widget.Duration, 2.0)


if __name__ == "__main__":
    unittest.main()
