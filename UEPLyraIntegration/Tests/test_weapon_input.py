"""UPython FRotator order must not silently roll the test camera."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class WeaponInputContracts(unittest.TestCase):
    def setUp(self):
        native = types.ModuleType("unreal_engine")
        native.FRotator = lambda: types.SimpleNamespace(pitch=0.0, yaw=0.0, roll=0.0)
        scripts = Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"
        spec = importlib.util.spec_from_file_location("_weapon_input_contract", scripts / "uep_lyra_weapon_input.py")
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native}):
            spec.loader.exec_module(self.module)

    def test_upward_aim_sets_explicit_pitch_not_roll(self):
        calls = []
        controller = types.SimpleNamespace(call_function=lambda *values: calls.append(values))
        self.module.aim_above_players(controller)
        self.assertEqual(calls[0][0], "SetControlRotation")
        self.assertEqual(vars(calls[0][1]), {"pitch": 80.0, "yaw": 0.0, "roll": 0.0})

    def test_native_rotation_is_reported_without_axis_permutation(self):
        native = types.SimpleNamespace(pitch=80.0, yaw=4.0, roll=0.0)
        controller = types.SimpleNamespace(call_function=lambda name: native)
        self.assertEqual(self.module.aim_snapshot(controller), {"pitch": 80.0, "yaw": 4.0, "roll": 0.0})


if __name__ == "__main__":
    unittest.main()
