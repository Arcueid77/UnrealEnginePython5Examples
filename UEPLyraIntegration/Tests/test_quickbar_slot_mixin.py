import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class QuickBarSlotPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        native = types.ModuleType("unreal_engine")
        structs = types.ModuleType("unreal_engine.structs")
        structs.GameplayTag = structs.LinearColor = lambda **kwargs: types.SimpleNamespace(**kwargs)
        self.controller, self.handled = object(), object()
        self.subsystem = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("input",)+args))

        def invoke(cls, name, *args):
            self.calls.append((cls, name)+args)
            if name == "Add_IntInt":
                value = (int(args[0])+int(args[1])) & 0xffffffff
                return value-0x100000000 if value & 0x80000000 else value
            if name == "GetLocalPlayerSubsystem":
                return self.subsystem
            if name == "MakeInputActionValueOfType":
                return "Axis1D(1)"
            if name == "Handled":
                return self.handled
        native.find_class = lambda name: types.SimpleNamespace(name=name, get_cdo=lambda: types.SimpleNamespace(
            call_function=lambda method, *args: invoke(name, method, *args)))
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda value: value is not None
        runtime = types.ModuleType("uep_runtime")
        runtime.SubscriptionScope = object
        pools = types.ModuleType("uep_lyra_hud.pooled_widget_lifetime")
        pools.unwatch = lambda widget: None
        pools.snapshot = lambda: {}
        source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/quickbar_slot_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._quickbar_policy_tests", source)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs, "uep_runtime": runtime,
                                     "uep_lyra_hud.weapon_observer": observer, "uep_lyra_hud.pooled_widget_lifetime": pools}):
            spec.loader.exec_module(self.module)
        self.widget = self.module.LyraQuickBarSlotPythonProfile()
        self.widget.SlotIndex, self.widget.QuickBarComponent = 0, None
        self.widget.IsEmpty, self.widget.IsSelected = False, False
        self.widget.ToEmpty, self.widget.InactiveToActive, self.widget.ActiveToInactive = "empty", "activate", "deactivate"
        self.widget.SlotInputAction = "slot-action"
        self.widget._uep_slot_reader = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("transport",)+args))
        self.widget.WeaponCard, self.widget.AmmoIcon = self.image("weapon"), self.image("ammo")
        self.widget.WeaponAmmoCount = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("numeric",)+args))
        self.playing = False

        def call(name, *args):
            self.calls.append((name,)+args)
            if name == "GetOwningPlayer":
                return self.controller
            if name == "IsAnimationPlaying":
                return self.playing
            if name == "IsThisTheActiveQuickbarSlot":
                return (self.widget.IsThisTheActiveQuickbarSlot()["IsActive"],)
            if hasattr(self.widget, name):
                return getattr(self.widget, name)(*args)
        self.widget.call_function = call
        self.widget.call_mixin_original = lambda *args: self.calls.append(("original",)+args)

    def image(self, name):
        material = types.SimpleNamespace(call_function=lambda *args: self.calls.append((name,)+args))
        return types.SimpleNamespace(call_function=lambda *args: material)

    def item(self, fragment=None, spare=48, magazine=12):
        def call(name, *args):
            if name == "FindFragmentByClass":
                return fragment
            if name == "GetStatTagStackCount":
                return spare if args[0].TagName.endswith("SpareAmmo") else magazine
        return types.SimpleNamespace(call_function=call)

    def fragment(self, weapon_texture=True, ammo_texture=True):
        def texture(accepted):
            return types.SimpleNamespace(is_a=lambda cls: accepted and cls.name == "Texture")
        return types.SimpleNamespace(Brush=types.SimpleNamespace(ResourceObject=texture(weapon_texture)),
                                     AmmoBrush=types.SimpleNamespace(ResourceObject=texture(ammo_texture)))

    def component(self, slots, active=0):
        return types.SimpleNamespace(call_function=lambda name: slots if name == "GetSlots" else active)

    def test_empty_transition_is_not_repeated(self):
        self.widget.UpdateSlot(None)
        self.widget.UpdateSlot(None)
        self.assertTrue(self.widget.IsEmpty)
        self.assertEqual(self.calls.count(("PlayAnimationForward", "empty", 1.0, False)), 1)

    def test_populated_materials_and_inactive_animation_only_on_empty_transition(self):
        fragment = self.fragment()
        item = self.item(fragment)
        self.widget.IsEmpty = True
        self.widget.QuickBarComponent = self.component([item], active=1)
        self.widget.UpdateSlot(item)
        self.widget.UpdateSlot(item)
        self.assertFalse(self.widget.IsEmpty)
        self.assertIn(("weapon", "SetTextureParameterValue", "IconTexture", fragment.Brush.ResourceObject), self.calls)
        self.assertIn(("ammo", "SetTextureParameterValue", "TextureMask", fragment.AmmoBrush.ResourceObject), self.calls)
        self.assertEqual(self.calls.count(("PlayAnimationReverse", "empty", 1.0, False)), 1)
        self.assertEqual(self.calls.count(("PlayAnimationForward", "deactivate", 1.0, False)), 1)

    def test_failed_first_texture_cast_leaves_all_presentation(self):
        self.widget.IsEmpty = True
        self.widget.UpdateSlot(self.item(self.fragment(weapon_texture=False)))
        self.assertTrue(self.widget.IsEmpty)
        self.assertEqual(self.calls, [])

    def test_failed_second_texture_cast_preserves_authored_partial_material_update(self):
        self.widget.IsEmpty = True
        self.widget.UpdateSlot(self.item(self.fragment(ammo_texture=False)))
        self.assertTrue(self.widget.IsEmpty)
        self.assertEqual([value[0] for value in self.calls], ["weapon"])

    def test_same_component_reference_does_not_refresh_slot_or_selection(self):
        component = self.component([])
        self.widget.QuickBarComponent = component
        self.widget.UpdateComponentRef(component)
        self.assertEqual(self.calls, [])

    def test_invalid_component_keeps_display_while_index_out_of_range_clears_slot(self):
        self.widget.QuickBarComponent = self.component([])
        self.widget.UpdateComponentRef(None)
        self.assertFalse(self.widget.IsEmpty)
        self.widget.SlotIndex = 9
        self.widget.UpdateComponentRef(self.component([self.item(self.fragment())]))
        self.assertTrue(self.widget.IsEmpty)

    def test_selection_uses_native_index_and_stops_owned_active_transition(self):
        self.widget.QuickBarComponent = self.component([], active=0)
        self.widget.UpdateIsSelected()
        self.assertTrue(self.widget.IsSelected)
        self.widget.QuickBarComponent = self.component([], active=1)
        self.playing = True
        self.widget.UpdateIsSelected()
        self.assertFalse(self.widget.IsSelected)
        self.assertIn(("StopAnimation", "activate"), self.calls)
        self.assertIn(("PlayAnimationForward", "deactivate", 1.0, False), self.calls)

    def test_total_ammo_uses_native_int_add_and_preserves_invalid_index(self):
        component = self.component([self.item(spare=48, magazine=9)])
        self.widget.UpdateTotalAmmoLeft(component)
        self.assertIn(("numeric", "SetCurrentValue", 57.0), self.calls)
        self.calls.clear()
        self.widget.SlotIndex = 9
        self.widget.UpdateTotalAmmoLeft(component)
        self.assertEqual(self.calls, [])

    def test_owner_slots_array_and_foreign_payload_filtering(self):
        item = self.item(self.fragment())
        self.module.receive(self.widget, types.SimpleNamespace(Owner=self.controller, Slots=[item]), True)
        self.assertEqual(self.widget._uep_slot_messages, 1)
        before = list(self.calls)
        self.module.receive(self.widget, types.SimpleNamespace(Owner=object(), Slots=[None]), True)
        self.assertEqual(self.calls, before + [("GetOwningPlayer",)])
        self.assertEqual(self.widget._uep_slot_foreign, 1)

    def test_active_message_ignores_payload_index_like_original(self):
        self.widget.QuickBarComponent = self.component([], active=0)
        self.module.receive(self.widget, types.SimpleNamespace(Owner=self.controller, ActiveIndex=77), False)
        self.assertTrue(self.widget.IsSelected)
        self.assertEqual(self.widget._uep_slot_active_messages, 1)

    def test_mouse_passes_native_axis_value_and_handled_reply(self):
        reply = self.widget.MouseDown(None, None)
        self.assertIs(reply, self.handled)
        self.assertIn(("transport", "InjectAxis1DForAction", self.subsystem, "slot-action", 1.0), self.calls)
        self.assertEqual(self.widget._uep_slot_mouse_calls, 1)

    def test_named_query_explicitly_opts_in_and_returns_named_dictionary(self):
        self.widget.QuickBarComponent = self.component([], active=0)
        self.assertEqual(self.widget.IsThisTheActiveQuickbarSlot(), {"IsActive": True})
        self.assertTrue(self.module.LyraQuickBarSlotPythonProfile.IsThisTheActiveQuickbarSlot.uep_named_outputs)
        self.assertEqual(self.module.snapshot()["named_query_calls"], 1)

    def test_named_query_false_and_invalid_native_output_shape(self):
        self.assertEqual(self.widget.IsThisTheActiveQuickbarSlot(), {"IsActive": False})
        self.widget.call_function = lambda *args: False
        with self.assertRaisesRegex(RuntimeError, "named output shape"):
            self.module.active_query(self.widget)


if __name__ == "__main__":
    unittest.main()
