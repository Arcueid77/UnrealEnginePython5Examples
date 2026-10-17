"""Exact fixture restoration despite native Controller's tiny-change suppression."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


def rot(roll=0., pitch=0., yaw=0.): return SimpleNamespace(roll=roll, pitch=pitch, yaw=yaw)


class Controller:
    def __init__(self, value): self.value, self.sets = value, []
    def call_function(self, name, *args):
        if name == "GetControlRotation": return self.value
        assert name == "SetControlRotation"
        value, = args; self.sets.append(value)
        if any(abs((getattr(value, key)-getattr(self.value, key)+180.)%360.-180.) > .001 for key in ("roll", "pitch", "yaw")):
            self.value = value


class ControlRestorationModels(unittest.TestCase):
    def setUp(self):
        source = (Path(__file__).parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/dash_local_direction_validation.py").read_text(encoding="utf-8")
        tree = ast.parse(source); tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ("rotation", "restore_control")]
        namespace = dict(ue=SimpleNamespace(FRotator=rot)); exec(compile(tree, "fixture-only", "exec"), namespace)
        self.restore = namespace["restore_control"]
    def test_native_small_delta_is_not_silently_left_unrestored(self):
        controller = Controller(rot()); expected = rot(yaw=.000229)
        result = self.restore(controller, expected); self.assertTrue(result["control_rotation"]); self.assertTrue(result["native_control_reset_forced"])
        self.assertEqual(result["control_after"], [0., 0., .000229]); self.assertEqual(len(controller.sets), 3)
    def test_already_exact_native_angle_does_not_force_extra_calls(self):
        controller = Controller(rot(yaw=20.)); result = self.restore(controller, rot(yaw=20.))
        self.assertTrue(result["control_rotation"]); self.assertFalse(result["native_control_reset_forced"]); self.assertEqual(len(controller.sets), 1)
    def test_large_native_rotation_restores_directly(self):
        controller = Controller(rot(pitch=20.)); result = self.restore(controller, rot())
        self.assertTrue(result["control_rotation"]); self.assertFalse(result["native_control_reset_forced"]); self.assertEqual(len(controller.sets), 1)
    def test_equal_orientation_but_wrapped_values_are_exactly_restored(self):
        controller = Controller(rot()); result = self.restore(controller, rot(yaw=360.))
        self.assertTrue(result["control_rotation"]); self.assertEqual(result["control_after"], [0., 0., 360.])
