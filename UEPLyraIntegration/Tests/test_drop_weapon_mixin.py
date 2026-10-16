"""Native inventory/cycle call-order models, not runtime equipment proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class DropWeaponPolicy(unittest.TestCase):
    def setUp(self):
        self.calls, self.authority, self.active, self.props = [], True, True, {}
        native, helpers = types.ModuleType("unreal_engine"), types.ModuleType("uep_lyra_world.effect_pad_mixin")
        helpers.valid = lambda value: value is not None; native.find_class = lambda name: name
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/drop_weapon_mixin.py"
        spec = importlib.util.spec_from_file_location("drop_weapon_model", path); self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, helpers.__name__: helpers}): spec.loader.exec_module(self.module)
        self.item = object()
        def quickbar(name, *args):
            self.calls.append((name, args))
            return 1 if name == "GetActiveSlotIndex" else (self.item if name == "RemoveItemFromSlot" else None)
        self.quickbar = types.SimpleNamespace(call_function=quickbar)
        self.inventory = types.SimpleNamespace(call_function=lambda name, *args: self.calls.append((name, args)))
        self.controller = types.SimpleNamespace(get_component_by_type=lambda cls: self.quickbar if cls == "LyraQuickBarComponent" else self.inventory)
        self.ability = types.SimpleNamespace(call_function=self.call, get_path_name=lambda: "native-drop", get_property=lambda key: self.active if key == "bIsActive" else self.props.get(key),
            set_property=lambda key, value: self.props.__setitem__(key, value))

    def call(self, name, *args):
        self.calls.append((name, args))
        if name == "K2_HasAuthority": return self.authority
        if name == "GetControllerFromActorInfo": return self.controller
        if name == "K2_EndAbility":
            self.active = False
            if not self.props.get(self.module.GUARD): self.module.LyraDropWeaponPythonProfile.NativeEnded(self.ability, False)

    def test_authority_uses_native_remove_inventory_then_cycle_and_end(self):
        self.module.activate(self.ability)
        names = [name for name, args in self.calls]
        self.assertLess(names.index("RemoveItemFromSlot"), names.index("RemoveItemInstance"))
        self.assertLess(names.index("RemoveItemInstance"), names.index("CycleActiveSlotForward"))
        self.assertEqual(self.module.snapshot()["items_removed"], 1); self.assertFalse(self.active)
        self.assertEqual(self.module.snapshot()["active_count"], 0)

    def test_non_authority_does_not_touch_inventory_or_quickbar(self):
        self.authority = False; self.module.activate(self.ability)
        self.assertEqual([name for name, args in self.calls], ["K2_HasAuthority", "K2_EndAbility"])

    def test_invalid_quickbar_still_ends_native_ability(self):
        self.quickbar = None; self.module.activate(self.ability)
        self.assertFalse(self.active); self.assertEqual(self.module.snapshot()["invalid_quickbar"], 1)

    def test_empty_slot_preserves_native_null_item_call_and_cycles(self):
        self.item = None; self.module.activate(self.ability)
        self.assertIn(("RemoveItemInstance", (None,)), self.calls)
        self.assertEqual(self.module.snapshot()["items_removed"], 0)
