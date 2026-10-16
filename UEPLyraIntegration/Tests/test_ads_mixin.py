"""ADS native-call policy models, not input/camera runtime proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_heal_ability_mixin import Scope


class ADSPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.props, self.active, self.local = [], {}, True, True
        native, structs, runtime, valid_module, fields, widgets = (types.ModuleType(name) for name in
            ("unreal_engine", "unreal_engine.structs", "uep_runtime", "uep_lyra_world.effect_pad_mixin",
             "uep_lyra_hud.message_payload_validation_fields", "uep_lyra_abilities.widget_lifecycle"))
        structs.GameplayTag = structs.ModifyContextOptions = lambda **values: types.SimpleNamespace(**values)
        runtime.SubscriptionScope = Scope; valid_module.valid = lambda value: value is not None
        fields.ON, fields.CONTROLLER = "enabled", "controller"
        widgets.add_many = lambda owner: self.calls.append(("widgets-added", ())) or 2
        widgets.remove_many = lambda owner: self.calls.append(("widgets-removed", ()))
        self.controller = object()
        self.movement = types.SimpleNamespace(MaxWalkSpeed=600., set_property=lambda key, value: setattr(self.movement, key, value))
        self.input = types.SimpleNamespace(call_function=lambda name, *args: self.calls.append((name, args)))
        self.task = types.SimpleNamespace(call_function=lambda name: self.calls.append((name, ())))
        self.helper = types.SimpleNamespace(add_to_root=lambda: self.calls.append(("root", ())),
            remove_from_root=lambda: self.calls.append(("unroot", ())), call_function=lambda name, *args: self.calls.append((name, args)))
        def library_call(name, *args):
            self.calls.append((name, args))
            if name == "GetLocalPlayerSubsystem": return self.input
            if name == "GetGameInstanceSubsystem": return "native-router"
            if name == "WaitInputRelease": return self.task
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=library_call))
        native.load_class = lambda path: path
        native.load_object = lambda cls, path: (lambda: types.SimpleNamespace()) if path.endswith("Struct_UIMessaging.Struct_UIMessaging") else path
        native.new_object = lambda cls: self.helper
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/ads_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_abilities.ads_model", file); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {module.__name__: module for module in (native, structs, runtime, valid_module, fields, widgets)}): spec.loader.exec_module(self.module)
        self.ability = types.SimpleNamespace(ADSMultiplier=.5, call_function=self.call, get_path_name=lambda: "native-ads",
            get_property=lambda key: self.active if key == "bIsActive" else self.props.get(key), set_property=lambda key, value: self.props.__setitem__(key, value))
        self.module.LyraADSPythonProfile.__init__(self.ability)

    def call(self, name, *args):
        self.calls.append((name, args))
        if name == "GetLyraPlayerControllerFromActorInfo": return self.controller
        if name == "GetLyraCharacterFromActorInfo": return types.SimpleNamespace(CharacterMovement=self.movement)
        if name == "IsLocallyControlled": return self.local
        if name == "BroadcastToUI": self.module.broadcast(self.ability, args[0])
        if name == "K2_EndAbility":
            self.active = False
            if not self.props.get(self.module.GUARD): self.module.LyraADSPythonProfile.NativeEnded(self.ability, False)

    def test_native_camera_speed_mapping_message_and_release_restore(self):
        self.module.activate(self.ability); scope = self.ability._uep_ads_scope
        self.assertEqual(self.movement.MaxWalkSpeed, 300.)
        mapping = next(args for name, args in self.calls if name == "AddMappingContext")
        self.assertEqual(mapping[1], 11); self.assertFalse(mapping[2].bIgnoreAllPressedKeysUntilRelease)
        scope.callbacks["OnRelease"](.4)
        self.assertFalse(self.active); self.assertTrue(scope.closed); self.assertEqual(self.movement.MaxWalkSpeed, 600.)
        stats = self.module.snapshot(); self.assertEqual((stats["ui_on"], stats["ui_off"]), (1, 1))
        self.assertEqual(stats["helpers_rooted"], stats["helpers_unrooted"])

    def test_remote_authority_skips_ui_and_sound(self):
        self.local = False; self.module.activate(self.ability); self.call("K2_EndAbility")
        self.assertFalse(any(name in ("BroadcastUI", "PlaySound2D") for name, args in self.calls))

    def test_teardown_does_not_route_mixed_public_message(self):
        self.module.activate(self.ability); self.calls = []
        self.module.teardown(self.ability)
        self.assertFalse(self.active); self.assertFalse(self.props[self.module.GUARD]); self.assertEqual(self.movement.MaxWalkSpeed, 600.)
        self.assertFalse(any(name == "BroadcastToUI" for name, args in self.calls))
        self.assertTrue(any(name == "BroadcastUI" for name, args in self.calls))

    def test_inherited_widget_registration_is_grant_owned(self):
        self.module.LyraADSPythonProfile.K2_OnAbilityAdded(self.ability)
        self.module.teardown(self.ability)
        self.assertFalse(any(name == "widgets-removed" for name, args in self.calls))
        self.module.LyraADSPythonProfile.K2_OnAbilityRemoved(self.ability)
        self.assertEqual(sum(name == "widgets-removed" for name, args in self.calls), 1)
