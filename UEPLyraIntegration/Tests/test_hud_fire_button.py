"""Touch fire intent contracts; these mocks are not native gameplay proof."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"
sys.path.insert(0, str(SCRIPTS))


class Subsystem:
    def __init__(self, valid=True):
        self.valid = valid
        self.calls = []

    def is_valid(self):
        return self.valid

    def call_function(self, name, *arguments):
        self.calls.append((name, arguments))


class FireButtonContracts(unittest.TestCase):
    def setUp(self):
        self.subsystem = Subsystem()
        self.library_calls = []
        library = types.SimpleNamespace(get_cdo=lambda: self)
        self.native_subsystem_class = object()
        fake_ue = types.ModuleType("unreal_engine")
        fake_ue.find_class = lambda name: {"SubsystemBlueprintLibrary": library,
                                          "EnhancedInputLocalPlayerSubsystem": self.native_subsystem_class}[name]
        fake_ue.FVector = lambda *values: values
        fake_observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        fake_observer.valid = lambda value: value is not None and value.is_valid()
        spec = importlib.util.spec_from_file_location(
            "uep_lyra_hud._fire_button_contract", SCRIPTS / "uep_lyra_hud" / "fire_button_mixin.py")
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": fake_ue,
                                     "uep_lyra_hud.weapon_observer": fake_observer}):
            spec.loader.exec_module(self.module)

    def call_function(self, name, *arguments):
        self.library_calls.append((name, arguments))
        return self.subsystem

    def widget(self):
        obj = self.module.LyraFireButtonPythonProfile()
        obj.get_property = lambda name: {"Associated Action": "fire", "Hold Action": "auto"}[name]
        return obj

    def test_two_authored_actions_in_order_with_exact_vector(self):
        widget = self.widget()
        widget.Clicked(object())
        self.assertEqual(self.library_calls, [("GetLocalPlayerSubsystem", (widget, self.native_subsystem_class))])
        self.assertEqual(self.subsystem.calls, [
            ("InjectInputVectorForAction", ("fire", (1.0, 1.0, 1.0))),
            ("InjectInputVectorForAction", ("auto", (1.0, 1.0, 1.0)))])
        self.assertEqual(widget._uep_fire_button_clicks, 1)

    def test_absent_local_subsystem_does_not_inject(self):
        self.subsystem = None
        widget = self.widget()
        widget.Clicked(None)
        self.assertEqual(widget._uep_fire_button_clicks, 0)

    def test_invalid_local_subsystem_does_not_inject(self):
        self.subsystem.valid = False
        widget = self.widget()
        widget.Clicked(None)
        self.assertEqual(self.subsystem.calls, [])
        self.assertEqual(widget._uep_fire_button_clicks, 0)

    def test_null_authored_action_is_forwarded_like_original_bp(self):
        widget = self.widget()
        widget.get_property = lambda name: None
        widget.Clicked(None)
        self.assertEqual(len(self.subsystem.calls), 2)
        self.assertTrue(all(arguments == (None, (1.0, 1.0, 1.0)) for _, arguments in self.subsystem.calls))

    def test_fallback_calls_only_saved_bp_entry(self):
        calls = []
        widget = self.module.LyraFireButtonBlueprintFallbackProfile()
        widget.call_mixin_original = lambda *arguments: calls.append(arguments)
        button = object()
        widget.Clicked(button)
        self.assertEqual(calls, [(self.module.CLICK_EVENT, button)])
        self.assertEqual(widget.Clicked.override, self.module.CLICK_EVENT)


if __name__ == "__main__":
    unittest.main()
