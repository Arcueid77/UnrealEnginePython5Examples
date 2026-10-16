"""Native-wrapper shape and fixture lifetime contracts, not runtime acceptance."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"))
from uep_lyra_combat_hud_protocol import CLICK_EVENT


class Widget:
    def __init__(self):
        self.calls = []
        self.ActionTouchButton = object()
        self.valid = True

    def call_function(self, *arguments):
        self.calls.append(arguments)

    def RemoveFromParent(self):
        self.calls.append(("remove",))

    def remove_from_root(self):
        self.calls.append(("unroot",))


class CombatProbeContracts(unittest.TestCase):
    def setUp(self):
        self.profile_calls = []
        fake_ue = types.ModuleType("unreal_engine")
        fake_ue.set_mixin_profile = lambda *args: self.profile_calls.append(args)
        structs = types.ModuleType("unreal_engine.structs")
        structs.Geometry = structs.Vector2D = object
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None and value.valid
        package = types.ModuleType("uep_lyra_hud")
        package.__path__ = []
        package.weapon_observer = observer
        package.state = types.SimpleNamespace(snapshot=lambda: {"active_widgets": []})
        fire = types.ModuleType("uep_lyra_hud.fire_button_mixin")
        fire.CLICK_EVENT = CLICK_EVENT
        scripts = Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"
        spec = importlib.util.spec_from_file_location("_combat_probe_contract", scripts / "uep_lyra_combat_hud_probe.py")
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": fake_ue, "unreal_engine.structs": structs,
                                     "uep_lyra_hud": package, "uep_lyra_hud.weapon_observer": observer,
                                     "uep_lyra_hud.fire_button_mixin": fire}):
            spec.loader.exec_module(self.module)
        self.probe = self.module.CombatHUDProbe()
        self.probe.button = Widget()

    def test_native_linear_color_wrapper_uses_lowercase_channels(self):
        color = types.SimpleNamespace(r=0.0, g=0.125, b=0.0, a=1.0)
        material = types.SimpleNamespace(call_function=lambda name, key: 49.0 if key == "Segments" else color)
        widget = types.SimpleNamespace(ProgressBorder=types.SimpleNamespace(call_function=lambda name: material))
        self.assertEqual(self.module.material_values(widget), {"segments": 49.0, "range": [0.0, 0.125, 0.0, 1.0]})

    def test_selected_bp_entry_runs_only_on_pressed_frames(self):
        self.probe.select_fire_profile("fire_b")
        self.probe.fire(False)
        self.assertEqual(self.probe.button.calls, [])
        self.probe.fire(True)
        self.assertEqual(self.probe.button.calls, [(CLICK_EVENT, self.probe.button.ActionTouchButton)])
        self.assertEqual(self.probe.fire_clicks, {"Python": 0, "BlueprintFallback": 1})

    def test_python_entry_is_selected_for_other_fire_phases(self):
        self.probe.select_fire_profile("fire_switched_a")
        self.probe.fire(True)
        self.assertEqual(self.probe.fire_clicks, {"Python": 1, "BlueprintFallback": 0})

    def test_expired_button_fails_before_input(self):
        self.probe.button.valid = False
        with self.assertRaisesRegex(RuntimeError, "expired"):
            self.probe.fire(True)
        self.assertEqual(self.probe.button.calls, [])

    def test_close_releases_all_owned_widgets_and_is_idempotent(self):
        self.probe.baseline, self.probe.reticle = Widget(), Widget()
        widgets = (self.probe.baseline, self.probe.reticle, self.probe.button)
        self.probe.close()
        self.probe.close()
        self.assertTrue(all(widget.calls == [("remove",), ("unroot",)] for widget in widgets))
        self.assertIsNone(self.probe.reticle)

    def test_debug_overlay_lifetime_is_owned_and_idempotent(self):
        self.probe.debug, self.probe.debug_baseline = Widget(), Widget()
        widgets = (self.probe.debug, self.probe.debug_baseline)
        self.probe.close()
        self.probe.close()
        self.assertTrue(all(widget.calls == [("remove",), ("unroot",)] for widget in widgets))
        self.assertIsNone(self.probe.debug)
        self.assertIsNone(self.probe.debug_baseline)


if __name__ == "__main__":
    unittest.main()
