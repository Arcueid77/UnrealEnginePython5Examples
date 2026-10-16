import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class DebugSpreadContracts(unittest.TestCase):
    def setUp(self):
        self.formats = []
        library = types.SimpleNamespace(call_function=lambda *args: self.formats.append(args) or "native text")
        native = types.ModuleType("unreal_engine")
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: library)
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/debug_spread_mixin.py"
        spec = importlib.util.spec_from_file_location("_debug_spread_contract", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native}):
            spec.loader.exec_module(self.module)

    def test_exact_native_text_defaults_are_preserved(self):
        self.module.format_angle(1.23456)
        self.assertEqual(self.formats, [("Conv_DoubleToText", 1.23456, 0, False, True, 1, 324, 0, 3)])

    def test_tick_reads_native_spread_and_only_updates_authored_text(self):
        widget = self.module.LyraDebugSpreadPythonProfile()
        calls = []
        widget.call_function = lambda name: calls.append(name) or 2.5
        widget.CommonTextBlock_52 = types.SimpleNamespace(call_function=lambda *args: calls.append(args))
        widget.Tick(None, 0.016)
        self.assertEqual(calls, ["ComputeSpreadAngle", ("SetText", "native text")])
        self.assertEqual((widget._uep_debug_spread_ticks, widget._uep_debug_spread_last), (1, 2.5))

    def test_fallback_executes_only_saved_tick(self):
        widget = self.module.LyraDebugSpreadBlueprintFallbackProfile()
        calls = []
        widget.call_mixin_original = lambda *args: calls.append(args)
        widget.Tick("geometry", 0.05)
        self.assertEqual(calls, [("Tick", "geometry", 0.05)])


if __name__ == "__main__":
    unittest.main()
