import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch, PropertyMock
import math


class RespawnTimerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls, self.clock = [], 100.5
        native = types.ModuleType("unreal_engine")
        def invoke(name, *args):
            self.calls.append((name,)+args)
            if name == "Divide_DoubleDouble":
                return args[0]/args[1]
            if name == "FCeil":
                return math.ceil(args[0])
            if name == "SpawnSound2D":
                return self.audio
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=invoke))
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None
        progress = types.ModuleType("uep_lyra_hud.ability_progress_mixin")
        progress.game_time = lambda widget: self.clock
        runtime = types.ModuleType("uep_runtime")
        runtime.SubscriptionScope = object
        pools = types.ModuleType("uep_lyra_hud.pooled_widget_lifetime")
        pools.unwatch = lambda widget: None
        pools.snapshot = lambda: {}
        source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/respawn_timer_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._respawn_contract", source)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime,
                                     "uep_lyra_hud.weapon_observer": observer, "uep_lyra_hud.ability_progress_mixin": progress,
                                     "uep_lyra_hud.pooled_widget_lifetime": pools}):
            spec.loader.exec_module(self.module)
        self.widget = self.module.LyraRespawnTimerPythonProfile()
        self.widget.Duration, self.widget.StartTime, self.widget.Respawning = 2.5, 100.0, True
        self.widget._uep_respawn_scope = types.SimpleNamespace(close=lambda: self.calls.append(("close",)))
        self.widget.Intro, self.widget.Outro, self.widget.PythonCountdownSound = "intro", "outro", "sound"
        self.owner_state = object()
        self.controller = types.SimpleNamespace(PlayerState=self.owner_state)
        self.audio = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        self.widget.CountdownAudio = None
        for name in ("FillGlow", "Fill"):
            material = types.SimpleNamespace(call_function=lambda *args, label=name: self.calls.append((label,)+args))
            setattr(self.widget, name, types.SimpleNamespace(call_function=lambda *args, result=material: result))
        self.widget.Time = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        def call(name, *args):
            self.calls.append((name,)+args)
            if name == "GetOwningPlayer":
                return self.controller
            if hasattr(self.widget, name):
                return getattr(self.widget, name)(*args)
        self.widget.call_function = call
        self.widget.call_mixin_original = lambda *args: self.calls.append(("original",)+args)

    def test_duration_uses_playerstate_and_native_quarter_second_timer(self):
        self.widget.Respawning = False
        self.module.duration_received(self.widget, types.SimpleNamespace(Instigator=self.owner_state, Duration=3.0))
        self.assertEqual((self.widget.Duration, self.widget.StartTime, self.widget.Respawning), (3.0, 100.5, True))
        self.assertIn(("PlayAnimation", "intro", 0.0, 1, 0, 1.0, False), self.calls)
        self.assertIn(("K2_SetTimer", self.widget, "UpdateRespawnText", 0.25, True, False, 0.0, 0.0), self.calls)

    def test_foreign_playerstate_does_not_update(self):
        self.module.duration_received(self.widget, types.SimpleNamespace(Instigator=self.controller, Duration=9.0))
        self.assertEqual(self.widget.Duration, 2.5)
        self.assertEqual(self.module._stats["foreign_messages"], 1)

    def test_repeat_skips_intro_and_updates_both_actual_baseline_materials(self):
        self.module.duration_received(self.widget, types.SimpleNamespace(Instigator=self.owner_state, Duration=2.0))
        self.assertFalse(any(call[0] == "PlayAnimation" for call in self.calls))
        self.assertIn(("FillGlow", "SetScalarParameterValue", "AnimateArcFill", 1.0), self.calls)
        self.assertIn(("Fill", "SetScalarParameterValue", "AnimateArcFill", 1.0), self.calls)

    def test_numeric_ceil_native_audio_and_parameter(self):
        self.widget.UpdateRespawnText()
        self.assertEqual(self.widget._uep_respawn_remaining, 2.0)
        self.assertIn(("SetCurrentValue", 2.0), self.calls)
        self.assertIn(("SetFloatParameter", "Progress", 0.8), self.calls)
        self.assertIs(self.widget.CountdownAudio, self.audio)

    def test_expiry_and_persistent_animation_callback(self):
        self.clock = 103.0
        self.widget.UpdateRespawnText()
        self.assertFalse(self.widget.Respawning)
        self.assertIn(("PlayAnimationForward", "outro", 1.0, False), self.calls)
        self.widget.OnAnimationFinished("outro")
        self.widget.OnAnimationFinished("outro")
        self.assertEqual(self.calls.count(("OnTimerFinished",)), 2)

    def test_completion_preserves_authored_respawning_flag(self):
        self.widget.CountdownAudio = self.audio
        self.module.completed_received(self.widget, types.SimpleNamespace(Instigator=self.owner_state))
        self.assertTrue(self.widget.Respawning)
        self.assertIn(("SetVisibility", 1), self.calls)
        self.assertIn(("StopDelayed", 0.5), self.calls)

    def test_closed_timer_cannot_revive_widget(self):
        self.widget._uep_respawn_scope = None
        self.widget.UpdateRespawnText()
        self.assertEqual(self.calls, [])

    def test_completed_true_flag_alone_does_not_restart_cleared_timer(self):
        self.module.start = lambda widget: None
        self.widget._uep_respawn_resume_timer = False
        self.widget.ResumeObservation()
        self.assertFalse(any(call[0] == "K2_SetTimer" for call in self.calls))

    def test_cleanup_disarms_then_clears_timer_audio(self):
        self.widget.CountdownAudio = self.audio
        self.widget.__uep_mixin_teardown__()
        self.assertIsNone(self.widget._uep_respawn_scope)
        self.assertEqual(self.widget._uep_respawn_outro_callbacks, 0)
        self.assertIn(("K2_ClearTimer", self.widget, "UpdateRespawnText"), self.calls)
        self.assertIn(("Stop",), self.calls)

    def test_stale_native_audio_reference_does_not_abort_python_cleanup(self):
        with patch.object(type(self.widget), "CountdownAudio", create=True,
                          new_callable=PropertyMock, side_effect=Exception("uobject is in invalid state")):
            self.widget.__uep_mixin_teardown__()
        self.assertIsNone(self.widget._uep_respawn_scope)
        self.assertIn(("close",), self.calls)
        self.assertIn(("K2_ClearTimer", self.widget, "UpdateRespawnText"), self.calls)
        self.assertEqual(self.module._stats["errors"], [])

    def test_stale_audio_does_not_abort_original_proxy_delegate_cleanup(self):
        self.widget.RespawnDurationAsyncAction = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        self.widget.RespawnCompletedAsyncAction = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        with patch.object(type(self.widget), "CountdownAudio", create=True,
                          new_callable=PropertyMock, side_effect=Exception("uobject is in invalid state")):
            self.module.close_original(self.widget)
        self.assertEqual(self.calls.count(("Cancel",)), 2)
        self.assertIsNone(self.widget.RespawnDurationAsyncAction)
        self.assertIsNone(self.widget.RespawnCompletedAsyncAction)
        self.assertIn((self.module.CLEANUP,), self.calls)

    def test_optional_audio_does_not_hide_other_errors_or_invalid_widget(self):
        with patch.object(type(self.widget), "CountdownAudio", create=True,
                          new_callable=PropertyMock, side_effect=Exception("unexpected property error")):
            with self.assertRaisesRegex(Exception, "unexpected property error"):
                self.module.countdown_audio(self.widget)
        self.module.valid = lambda value: False
        with patch.object(type(self.widget), "CountdownAudio", create=True,
                          new_callable=PropertyMock, side_effect=Exception("uobject is in invalid state")):
            with self.assertRaisesRegex(Exception, "uobject is in invalid state"):
                self.module.countdown_audio(self.widget)


if __name__ == "__main__":
    unittest.main()
