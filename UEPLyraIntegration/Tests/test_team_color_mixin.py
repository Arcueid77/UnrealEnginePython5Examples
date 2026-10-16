"""Device policy branch/typed-output models; no native scheduler/hardware proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class DeviceColorPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.props, self.user_valid, self.lyra = [], {}, True, True
        self.controller = types.SimpleNamespace(is_a=lambda cls: self.lyra, get_controlled_pawn=lambda: "native-pawn")
        native, structs, helpers = (types.ModuleType(name) for name in ("unreal_engine", "unreal_engine.structs", "uep_lyra_world.effect_pad_mixin"))
        helpers.valid = lambda value: value is not None
        structs.DeviceColorData = lambda **kwargs: kwargs
        native.FLinearColor = lambda *values: values
        def call(name, *args):
            self.calls.append((name, args))
            if name == "GetPlayerControllerFromPlatformUser": return self.controller if self.user_valid else None
            if name == "FindTeamFromObject": return True, 3, "native-display"
            if name == "GetTeamColorWithFallback": return "native-linear"
            if name == "Conv_LinearColorToColor": return "native-srgb-color"
            raise AssertionError("unexpected native call "+name)
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=call))
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_devices/team_color_mixin.py"
        spec = importlib.util.spec_from_file_location("device_color_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs, "uep_lyra_world.effect_pad_mixin": helpers}): spec.loader.exec_module(self.module)
        self.instance = types.SimpleNamespace(get_path_name=lambda: "native-device-property", set_property=lambda name, value: self.props.__setitem__(name, value))

    def test_valid_user_preserves_original_color_conversion_and_native_parent_branch(self):
        result = self.module.LyraDeviceColorPythonProfile.Route(self.instance, "actual-user", "actual-device", .125, .75)
        self.assertEqual(result, dict(ReturnValue=False, bCallNativeParent=True))
        self.assertEqual(self.calls, [("GetPlayerControllerFromPlatformUser", ("actual-user",)), ("FindTeamFromObject", ("native-pawn", False)),
            ("GetTeamColorWithFallback", ("native-display", "TeamColor", (0., 0., 0., 0.))), ("Conv_LinearColorToColor", ("native-linear", True))])
        self.assertEqual(self.props["ColorData"], dict(bEnable=True, bResetAfterCompletion=False, LightColor="native-srgb-color"))

    def test_invalid_user_and_non_lyra_controller_never_mutate_or_call_native_parent(self):
        for valid_user, lyra in ((False, True), (True, False)):
            self.user_valid, self.lyra = valid_user, lyra
            result = self.module.LyraDeviceColorPythonProfile.Route(self.instance, "user", "device", 0., 0.)
            self.assertEqual(result, dict(ReturnValue=False, bCallNativeParent=False)); self.assertEqual(self.props, {})
        self.assertEqual(self.module.snapshot()["colors_written"], 0)

    def test_original_bp_fallback_selects_original_path_only(self):
        self.assertEqual(self.module.LyraDeviceColorBlueprintFallbackProfile.Route(self.instance, "user", "device", 0., 0.),
            dict(ReturnValue=True, bCallNativeParent=False))
        self.assertEqual(self.calls, []); self.assertEqual(self.props, {})

    def test_named_output_protocol_is_explicit_for_both_profiles(self):
        for cls in (self.module.LyraDeviceColorPythonProfile, self.module.LyraDeviceColorBlueprintFallbackProfile):
            self.assertEqual(cls.Route.override, "UEPDeviceColorRoute"); self.assertTrue(cls.Route.uep_named_outputs)

    def test_metadata_is_bounded_without_uobject_retention_or_subscriptions(self):
        self.user_valid = False
        for index in range(300):
            value = types.SimpleNamespace(get_path_name=lambda index=index: "native-"+str(index))
            self.module.choose(value, "invalid")
        self.assertEqual(len(self.module._counts), 256)
        self.assertTrue(all(type(key) is str and all(type(count) is int for count in counts.values()) for key, counts in self.module._counts.items()))
        self.assertEqual((self.module.snapshot()["active_count"], self.module.snapshot()["script_subscriptions_created"]), (0, 0))
