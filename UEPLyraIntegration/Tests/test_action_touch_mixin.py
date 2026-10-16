"""Isolated policy tests; no UMG/native input acceptance claim."""
import importlib.util
import ast
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_inventory_pad_mixin import Object
from test_launcher_mixin import vector


class Scope:
    def __init__(self):
        self.closed = False
        self.callbacks = []
    def listen_gameplay_message(self, *args):
        self.callbacks.append(args)
    def close(self):
        self.closed = True


class ActionTouchPolicy(unittest.TestCase):
    def setUp(self):
        native = types.ModuleType("unreal_engine"); native.FVector = vector
        native.find_class = native.find_struct = lambda name: name
        runtime = types.ModuleType("uep_runtime"); runtime.SubscriptionScope = Scope
        observer = types.ModuleType("uep_lyra_hud.weapon_observer"); observer.valid = lambda value: value is not None and value.is_valid()
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud/action_touch_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._action_touch_policy", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_runtime": runtime, "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)
        self.widget = Object("widget", self.widget_call)
        self.widget.get_path_name = lambda: "widget-path"
        self.widget.get_property = lambda name: getattr(self.widget, name)
        self.widget.set_property = lambda name, value: setattr(self.widget, name, value)
        self.module.LyraActionTouchPythonProfile.__init__(self.widget)
        self.materials = {name: Object(name+"-mid") for name in ("WeaponCard", "ItemGlow")}
        for name in ("WeaponCard", "ItemGlow"):
            setattr(self.widget, name, Object(name, lambda method, *args, key=name: self.materials[key] if method == "GetDynamicMaterial" else None))
        for name in ("MainSBWithPadding", "BackingBorder", "Shadow", "BackgroundBlur", "DisableGlowBoostOvr", "ItemGlow_Boost"):
            setattr(self.widget, name, Object(name))
        for name in ("CooldownInactiveToActive", "CooldownActiveToInactive", "OnClickedTouchInput", "AssociatedAction",
                     "HitTestPadding", "ButtonBrush", "ButtonGlowBrush", "GlowOverdraw", "BlurPadding"):
            setattr(self.widget, name, name)
        for name in ("HasCooldown", "UseBacking", "UseShadow", "UseBlur", "UseGlow", "UseGlowBoost"):
            setattr(self.widget, name, True)
        self.widget.IsToggleButton, self.widget.isDisabled, self.widget.Charging = False, False, False
        self.widget.BlurCornerRadius = 12.
        self.widget.DurationMessageTag = types.SimpleNamespace(TagName="Ability.Interaction.Duration.Message")
        self.widget.Duration, self.widget.StartTime = 2., 4.
        self.now, self.channel, self.animation = 5., True, False
        self.pawn, self.subsystem = Object("pawn"), Object("input")
        self.library_calls = []
        self.slot = Object("slot")
        self.module.library = lambda cls: Object(cls, lambda name, *args: self.library_call(cls, name, *args))

    def library_call(self, cls, name, *args):
        self.library_calls.append((name, *args))
        return {"GetTimeSeconds": self.now, "IsGameplayTagValid": self.channel, "SlotAsOverlaySlot": self.slot,
                "GetLocalPlayerSubsystem": self.subsystem, "MakeVector4": "corners"}.get(name,
                    args[0]/args[1] if name == "Divide_DoubleDouble" else None)

    def widget_call(self, name, *args):
        if name == "GetOwningPlayerPawn":
            return self.pawn
        if name in ("IsAnimationPlaying", "IsAnimationPlayingForward"):
            return self.animation
        if name == "UpdateCoolDownPercent":
            return self.module.update_percent(self.widget, args[0])
        if name == "ResetMaterials":
            return self.module.reset_materials(self.widget)

    def test_style_preserves_native_visibility_brush_padding_and_corner(self):
        self.widget.UseShadow = False
        self.module.style(self.widget)
        self.assertEqual(self.widget.Shadow.calls, [("SetVisibility", 1)])
        self.assertEqual(self.widget.BackingBorder.calls, [("SetVisibility", 3)])
        self.assertIn(("SetBrush", "ButtonBrush"), self.widget.WeaponCard.calls)
        self.assertEqual(self.widget.BackgroundBlur.calls[-1], ("SetCornerRadius", "corners"))
        self.assertEqual(len(self.slot.calls), 4)

    def test_cooldown_percent_native_materials(self):
        self.module.update_percent(self.widget, .25)
        for mid in self.materials.values():
            self.assertEqual(mid.calls, [("SetScalarParameterValue", "Animate_Cooldown", .25)])

    def test_owner_message_restarts_and_foreign_is_ignored(self):
        self.module.received(self.widget, types.SimpleNamespace(Instigator=Object("foreign"), Duration=10.))
        self.assertFalse(self.widget.Charging)
        self.animation = True
        self.module.received(self.widget, types.SimpleNamespace(Instigator=self.pawn, Duration=3.))
        self.assertEqual((self.widget.Duration, self.widget.StartTime, self.widget.Charging), (3., 5., True))
        self.assertIn(("StopAnimation", "CooldownInactiveToActive"), self.widget.calls)
        self.assertEqual(self.module.snapshot()["foreign_messages"], 1)
        self.assertEqual(self.widget._uep_action_messages, 1)

    def test_native_game_time_progress_and_completion(self):
        self.widget.Charging = True
        self.module.LyraActionTouchPythonProfile.Tick(self.widget, None, .016)
        self.assertEqual(self.materials["ItemGlow"].calls[-1][-1], .5)
        self.now = 7.
        self.module.LyraActionTouchPythonProfile.Tick(self.widget, None, .016)
        self.assertFalse(self.widget.Charging)
        self.assertEqual(self.materials["ItemGlow"].calls[-1][-1], 1.)
        self.assertEqual(self.widget._uep_action_ticks, 2)

    def test_click_injects_original_vector_and_animation_is_conditional(self):
        self.module.LyraActionTouchPythonProfile.BP_OnClicked(self.widget)
        call = self.subsystem.calls[-1]
        self.assertEqual(call[0:2], ("InjectInputVectorForAction", "AssociatedAction"))
        self.assertEqual((call[2].x, call[2].y, call[2].z), (1., 0., 0.))
        self.assertFalse(any(c[0] == "PlayAnimationForward" for c in self.widget.calls))
        self.widget.HasCooldown = False
        self.module.LyraActionTouchPythonProfile.BP_OnClicked(self.widget)
        self.assertEqual(self.widget.calls[-1], ("PlayAnimationForward", "OnClickedTouchInput", 1., False))

    def test_disabled_selection_has_no_animation_and_enable_restores(self):
        self.module.LyraActionTouchPythonProfile.BP_OnDisabled(self.widget)
        self.widget.calls.clear()
        self.module.LyraActionTouchPythonProfile.BP_OnSelected(self.widget)
        self.module.LyraActionTouchPythonProfile.BP_OnDeselected(self.widget)
        self.assertEqual(self.widget.calls, [])
        self.module.LyraActionTouchPythonProfile.BP_OnEnabled(self.widget)
        self.assertFalse(self.widget.isDisabled)
        self.module.LyraActionTouchPythonProfile.BP_OnSelected(self.widget)
        self.assertEqual(self.widget.calls[-1], ("PlayAnimationForward", "CooldownInactiveToActive", 1., False))

    def test_scope_invalid_channel_noop_and_valid_idempotent_cleanup(self):
        self.channel = False
        self.module.start(self.widget)
        self.assertIsNone(self.widget._uep_action_scope)
        self.channel = True
        self.module.start(self.widget); self.module.start(self.widget)
        scope = self.widget._uep_action_scope
        self.assertEqual(len(scope.callbacks), 1)
        self.assertEqual(self.module.snapshot()["active_count"], 1)
        self.module.close(self.widget); self.module.close(self.widget)
        self.assertTrue(scope.closed)
        self.assertEqual(self.module.snapshot()["scopes_created"], self.module.snapshot()["scopes_closed"])
        self.assertEqual(self.module.snapshot()["active_count"], 0)

    def test_runtime_reflected_writes_do_not_emit_editor_property_notifications(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud/action_touch_mixin.py"
        tree = ast.parse(file.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    for nested in ast.walk(target):
                        if isinstance(nested, ast.Attribute) and isinstance(nested.value, ast.Name) and nested.value.id in ("self", "widget"):
                            self.assertTrue(nested.attr.startswith("_uep_"), "reflected runtime assignment must use set_property: "+nested.attr)
