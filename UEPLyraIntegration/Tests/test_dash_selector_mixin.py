"""Native math is mocked here; real BP output equivalence needs UE evidence."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class DashSelectorPolicyModels(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def native_math(name, *args):
            self.calls.append(name)
            if name == "Conv_VectorToRotator": return types.SimpleNamespace(yaw=args[0])
            if name == "NormalizedDeltaRotator": return types.SimpleNamespace(yaw=args[0].yaw-args[1].yaw)
            if name == "Abs": return abs(args[0])
            raise AssertionError(name)
        native = types.ModuleType("unreal_engine")
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=native_math))
        file = Path(__file__).parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/dash_selector_mixin.py"
        spec = importlib.util.spec_from_file_location("dash_selector_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native}): spec.loader.exec_module(self.module)
        self.ability = types.SimpleNamespace(get_property=lambda name: name)

    def check(self, yaw, field, bias):
        value = self.module.LyraDashSelectorPythonProfile.SelectDirectionalMontage(self.ability, 0., yaw)
        self.assertEqual(value, dict(DirectionalMontage=field, BiasForwardMovement=bias))
        self.assertEqual(self.calls, ["Conv_VectorToRotator", "Conv_VectorToRotator", "NormalizedDeltaRotator", "Abs"])
    def test_forward(self): self.check(0., "Dash_Fwd Montage", True)
    def test_forward_before_positive_boundary(self): self.check(44.999, "Dash_Fwd Montage", True)
    def test_forward_before_negative_boundary(self): self.check(-44.999, "Dash_Fwd Montage", True)
    def test_positive_45_is_right_not_forward(self): self.check(45., "Dash_Right Montage", False)
    def test_negative_45_is_left_not_forward(self): self.check(-45., "Dash_Left Montage", False)
    def test_positive_135_is_right_not_backward(self): self.check(135., "Dash_Right Montage", False)
    def test_negative_135_is_left_not_backward(self): self.check(-135., "Dash_Left Montage", False)
    def test_positive_backward(self): self.check(135.001, "Dash_Bwd Montage", False)
    def test_negative_backward(self): self.check(-135.001, "Dash_Bwd Montage", False)
    def test_null_selected_montage_is_preserved(self):
        self.ability.get_property = lambda name: None
        self.assertEqual(self.module.choose(self.ability, 0., 90.), dict(DirectionalMontage=None, BiasForwardMovement=False))
    def test_named_output_protocol_declared_on_both_profiles(self):
        for name in ("LyraDashSelectorPythonProfile", "LyraDashSelectorBlueprintFallbackProfile"):
            self.assertTrue(getattr(self.module, name).__dict__["SelectDirectionalMontage"].uep_named_outputs)
    def test_original_fallback_passes_exact_inputs_and_outputs(self):
        self.ability.call_mixin_original = lambda name, a, b: ("native-montage", True)
        result = self.module.LyraDashSelectorBlueprintFallbackProfile.SelectDirectionalMontage(self.ability, 20., 21.)
        self.assertEqual(result, dict(DirectionalMontage="native-montage", BiasForwardMovement=True))
        self.assertEqual(self.module.evidence(self.ability)["fallback_calls"], 1)
        self.assertEqual(self.calls, [])
    def test_original_output_shape_cannot_be_silently_truncated(self):
        self.ability.call_mixin_original = lambda *args: (True,)
        with self.assertRaises(RuntimeError): self.module.LyraDashSelectorBlueprintFallbackProfile.SelectDirectionalMontage(self.ability, 0., 0.)
