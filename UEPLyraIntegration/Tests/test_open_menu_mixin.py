import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class OpenMenuContracts(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.proxy = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        library = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args) or self.proxy)
        native = types.ModuleType("unreal_engine")
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: library)
        native.load_class = lambda *args: self.fail("menu must not be preloaded")
        structs = types.ModuleType("unreal_engine.structs")
        structs.GameplayTag = lambda **args: args
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/open_menu_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._open_menu_contract", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs,
                                     "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)

    def test_click_preserves_lazy_class_layer_and_input_suspension(self):
        widget = self.module.LyraOpenMenuPythonProfile()
        controller = object()
        widget.call_function = lambda name: controller
        widget.Clicked(object())
        self.assertEqual(self.calls, [("PushContentToLayerForPlayer", controller, self.module.MENU_CLASS,
                                       {"TagName": "UI.Layer.Menu"}, True), ("Activate",)])
        self.assertEqual(widget._uep_open_menu_clicks, 1)

    def test_fallback_calls_only_saved_event(self):
        widget = self.module.LyraOpenMenuBlueprintFallbackProfile()
        widget.call_mixin_original = lambda *args: self.calls.append(args)
        button = object()
        widget.Clicked(button)
        self.assertEqual(self.calls, [(self.module.CLICK_EVENT, button)])


if __name__ == "__main__":
    unittest.main()
