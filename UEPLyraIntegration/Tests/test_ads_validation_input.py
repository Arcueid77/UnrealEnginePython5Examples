"""Unit-model the native input probe, not the engine's EnhancedInput behavior."""
import ast
from pathlib import Path
import time
import types
import unittest


class ADSProbeInputModel(unittest.TestCase):
    def hold(self, name, injections):
        source = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/ads_validation.py"
        cls = next(node for node in ast.parse(source.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef))
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "hold")
        def require(value, message):
            if not value: raise RuntimeError(message)
        calls = []
        native = types.SimpleNamespace(load_class=lambda path: "camera", set_mixin_profile=lambda *args: calls.append(("profile", args)))
        policy = types.SimpleNamespace(CAMERA="camera-path", snapshot=lambda: dict(activations=1))
        namespace = dict(time=time, ue=native, policy=policy, require=require)
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), namespace)
        fixture = types.SimpleNamespace(name=name, phase_started=time.monotonic(), original_speed=600., profile="ADSPython",
            before=dict(activations=0), row=dict(input_injections=injections, native_camera_while_held=False, native_speed_while_held=False,
                native_mapping_priority_11=False, actual_reticle_ads_on=False),
            ability=types.SimpleNamespace(ADSMultiplier=.5, get_property=lambda key: True, call_function=lambda name: calls.append((name, ()))),
            hero=types.SimpleNamespace(get_property=lambda key: "camera"), movement=types.SimpleNamespace(MaxWalkSpeed=300.),
            mapping=lambda: dict(active=True, priority=11), reticle=types.SimpleNamespace(_uep_reticle_ads=True),
            inject=lambda pressed: calls.append(("inject", pressed)), tasks=lambda: 1, may_finish_hold=lambda: True,
            enter=lambda phase: calls.append(("phase", phase)))
        namespace["hold"](fixture)
        return calls

    def test_end_frame_never_queues_both_held_and_released_input(self):
        for name in ("native-cancel", "external-native-end", "active-profile-switch", "release-held"):
            with self.subTest(name=name):
                calls = self.hold(name, 4)
                self.assertEqual([value for key, value in calls if key == "inject"], [False])
                self.assertIn(("phase", "ended"), calls)

    def test_hold_frame_injects_only_held_input(self):
        calls = self.hold("release-held", 2)
        self.assertEqual(calls, [("inject", True)])
