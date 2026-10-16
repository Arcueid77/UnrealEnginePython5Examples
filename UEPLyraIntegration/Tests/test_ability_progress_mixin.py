import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class AbilityProgressContracts(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.clock = 100.5
        native = types.ModuleType("unreal_engine")
        native.FLinearColor = lambda *args: args

        def call(name, *args):
            self.calls.append((name,) + args)
            if name == "GetTimeSeconds":
                return self.clock
            if name == "Divide_DoubleDouble":
                return args[0] / args[1] if args[1] else 0.0
            if name == "Conv_DoubleToText":
                return "native-formatted-text"

        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=call))
        runtime = types.ModuleType("uep_runtime")
        runtime.SubscriptionScope = object
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/ability_progress_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._progress_contract", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime, "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)
        self.widget = self.module.LyraAbilityProgressPythonProfile()
        self.widget.Duration, self.widget.StartTime = 2.0, 100.0
        self.pawn = object()
        self.widget.call_function = lambda name, *args: self.pawn if name == "GetOwningPlayerPawn" else self.calls.append((name,) + args)
        self.material = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        self.widget.ProgressBorder = types.SimpleNamespace(call_function=lambda name: self.material)
        self.widget.ProgressText = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))

    def test_owner_message_updates_native_model_and_material(self):
        self.module.received(self.widget, types.SimpleNamespace(Instigator=self.pawn, Duration=3.0))
        self.assertEqual((self.widget.Duration, self.widget.StartTime), (3.0, 100.5))
        self.assertIn(("SetVisibility", 0), self.calls)
        self.assertIn(("SetVectorParameterValue", "ActiveRange", (0.0, 0.0, 0.0, 0.0)), self.calls)

    def test_foreign_message_does_not_change_model(self):
        self.module.received(self.widget, types.SimpleNamespace(Instigator=object(), Duration=3.0))
        self.assertEqual((self.widget.Duration, self.widget.StartTime), (2.0, 100.0))
        self.assertEqual(self.calls, [])

    def test_authored_null_equality_is_preserved(self):
        self.pawn = None
        self.module.received(self.widget, types.SimpleNamespace(Instigator=None, Duration=3.0))
        self.assertEqual(self.widget.Duration, 3.0)

    def test_tick_uses_native_clock_formatting_and_division(self):
        self.module.start = lambda widget: None
        self.widget.Tick(None, 99.0)
        self.assertIn(("Divide_DoubleDouble", 0.5, 2.0), self.calls)
        self.assertIn(("Conv_DoubleToText", 1.5, 0, False, False, 1, 324, 0, 0), self.calls)
        self.assertIn(("SetScalarParameterValue", "Percent", 0.25), self.calls)
        self.assertNotIn(("SetVisibility", 1), self.calls)

    def test_last_second_uses_one_fraction_and_expiry_collapses(self):
        self.module.start = lambda widget: None
        self.clock = 101.5
        self.widget.Tick(None, 0.0)
        self.assertIn(("Conv_DoubleToText", 0.5, 0, False, False, 1, 324, 0, 1), self.calls)
        self.clock = 102.0
        self.widget.Tick(None, 0.0)
        self.assertIn(("SetVisibility", 1), self.calls)

    def test_pause_and_zero_duration_delegate_to_native_semantics(self):
        self.module.start = lambda widget: None
        for delta in (0.0, 50.0):
            self.widget.Tick(None, delta)
        self.assertEqual(self.calls.count(("SetScalarParameterValue", "Percent", 0.25)), 2)
        self.widget.Duration = 0.0
        self.widget.Tick(None, 0.0)
        self.assertIn(("Divide_DoubleDouble", 0.5, 0.0), self.calls)
        self.assertIn(("SetScalarParameterValue", "Percent", 0.0), self.calls)

    def test_resume_does_not_replay_or_reset_ui(self):
        self.module.start = lambda widget: self.calls.append(("start",))
        self.widget.ResumeObservation()
        self.assertEqual(self.calls, [("start",)])
        self.assertEqual((self.widget.Duration, self.widget.StartTime), (2.0, 100.0))

    def test_construct_rearms_without_replaying_initialization_or_resetting_model(self):
        self.module.start = lambda widget: self.calls.append(("start",))
        self.widget.Construct()
        self.assertEqual(self.calls, [("start",), ("SetVisibility", 1)])
        self.assertEqual((self.widget.Duration, self.widget.StartTime), (2.0, 100.0))

    def test_fallback_construct_rearms_the_cancelled_original_proxy(self):
        widget = self.module.LyraAbilityProgressBlueprintFallbackProfile()
        widget.call_mixin_original = lambda *args: self.calls.append(("original",) + args)
        widget.call_function = lambda *args: self.calls.append(("call",) + args)
        widget.Construct()
        self.assertEqual(self.calls, [("original", "Construct"), ("call", self.module.RESUME_EVENT)])

    def test_teardown_cancels_and_unroots_once(self):
        self.widget._uep_progress_scope = types.SimpleNamespace(close=lambda: self.calls.append(("close",)))
        self.widget._uep_progress_reader = types.SimpleNamespace(remove_from_root=lambda: self.calls.append(("unroot",)))
        self.widget.__uep_mixin_teardown__()
        self.widget.__uep_mixin_teardown__()
        self.assertEqual(self.calls, [("close",), ("unroot",)])

    def test_fallback_teardown_only_cancels_its_saved_proxy(self):
        widget = self.module.LyraAbilityProgressBlueprintFallbackProfile()
        widget.UEPOriginalDurationProxy = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        widget.__uep_mixin_teardown__()
        widget.__uep_mixin_teardown__()
        self.assertEqual(self.calls, [("Cancel",)])
        self.assertIsNone(widget.UEPOriginalDurationProxy)


if __name__ == "__main__":
    unittest.main()
