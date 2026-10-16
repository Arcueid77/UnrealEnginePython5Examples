"""Native operation ordering/authority/nullable policy models, not UE proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Item:
    def __init__(self, name): self.name, self.definition = name, types.SimpleNamespace(get_path_name=lambda: "definition-"+name)
    def get_path_name(self): return self.name
    def get_property(self, name):
        if name != "ItemDef": raise AssertionError(name)
        return self.definition


class CharacterInventoryModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.authority, self.original_calls = [], True, []
        self.items = [Item("pistol"), Item("rifle")]
        self.slots, self.active = [self.items[0], None, self.items[1]], 0
        self.quick = types.SimpleNamespace(call_function=self.quick_call)
        self.inventory = types.SimpleNamespace(call_function=self.inventory_call)
        self.controller = types.SimpleNamespace(call_function=self.controller_call)
        self.actor = types.SimpleNamespace(call_function=self.actor_call, get_path_name=lambda: "original-actor",
            call_mixin_original=lambda method: self.original_calls.append(method))
        ue = types.ModuleType("unreal_engine"); ue.find_class = lambda name: name
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda obj: obj is not None
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/inventory_clear_mixin.py"
        spec = importlib.util.spec_from_file_location("character_inventory_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": ue, native.__name__: native}): spec.loader.exec_module(self.module)
        self.python = self.module.LyraCharacterInventoryPythonProfile

    def actor_call(self, method):
        return {"GetController": self.controller, "HasAuthority": self.authority, "GetLocalRole": 3 if self.authority else 2}[method]
    def controller_call(self, method, cls):
        if method != "GetComponentByClass": raise AssertionError(method)
        return {"LyraQuickBarComponent": self.quick, "LyraInventoryManagerComponent": self.inventory}[cls]
    def quick_call(self, method, *args):
        if method == "GetSlots": return list(self.slots)
        if method == "GetActiveSlotIndex": return self.active
        if method == "RemoveItemFromSlot":
            index, = args; self.calls.append(("slot", index)); self.slots[index] = None
            if self.active == index: self.active = -1
            return
        raise AssertionError(method)
    def inventory_call(self, method, *args):
        if method == "GetAllItems": return list(self.items)
        if method == "RemoveItemInstance":
            item, = args; self.calls.append(("item", item.name)); self.items.remove(item); return
        raise AssertionError(method)

    def test_native_slots_then_copied_items_and_empty_slots_are_preserved(self):
        self.python.ClearInventory(self.actor)
        self.assertEqual(self.calls, [("slot", 0), ("slot", 1), ("slot", 2), ("item", "pistol"), ("item", "rifle")])
        self.assertEqual(self.slots, [None]*3); self.assertEqual(self.items, []); self.assertEqual(self.active, -1)
        self.assertEqual(self.original_calls, [])
        state = self.module.evidence(self.actor)
        self.assertEqual((state["python_calls"], state["slots_removed"], state["items_removed"]), (1, 3, 2))

    def test_real_authority_guard_does_not_mutate_client_inventory(self):
        self.authority = False; before = self.module.inventory_state(self.controller)
        self.python.ClearInventory(self.actor)
        self.assertEqual(self.calls, []); self.assertEqual(self.module.inventory_state(self.controller), before)
        self.assertEqual(self.module.evidence(self.actor)["authority_noops"], 1)

    def test_missing_controller_is_safe_explicit_noop(self):
        self.controller = None; self.python.ClearInventory(self.actor)
        self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["missing_controller_noops"], 1)

    def test_missing_quickbar_keeps_inventory_as_original_guard_does(self):
        self.quick = None; self.python.ClearInventory(self.actor)
        self.assertEqual(self.calls, []); self.assertEqual(len(self.items), 2)

    def test_missing_inventory_still_clears_quickbar_before_safe_noop(self):
        self.inventory = None; self.python.ClearInventory(self.actor)
        self.assertEqual(self.calls, [("slot", 0), ("slot", 1), ("slot", 2)])
        self.assertEqual(self.module.evidence(self.actor)["missing_inventory_noops"], 1)

    def test_zero_slots_does_not_skip_inventory_sequence(self):
        self.slots = []; self.python.ClearInventory(self.actor)
        self.assertEqual(self.calls, [("item", "pistol"), ("item", "rifle")])

    def test_repeat_is_idempotent_but_native_slot_iteration_is_not_silently_omitted(self):
        self.python.ClearInventory(self.actor); self.calls = []; self.python.ClearInventory(self.actor)
        self.assertEqual(self.calls, [("slot", 0), ("slot", 1), ("slot", 2)])
        self.assertEqual(self.module.evidence(self.actor)["items_removed"], 2)

    def test_fallback_calls_only_original_helper(self):
        self.module.LyraCharacterInventoryBlueprintFallbackProfile.ClearInventory(self.actor)
        self.assertEqual(self.original_calls, ["ClearInventory"]); self.assertEqual(self.calls, [])
        self.assertEqual(self.module.evidence(self.actor)["fallback_calls"], 1)

    def test_evidence_dict_identity_survives_for_readonly_fixture_after_native_gc(self):
        handle = self.module.evidence(self.actor)
        self.python.ClearInventory(self.actor)
        self.assertIs(handle, self.module.evidence(self.actor))
        self.assertEqual(handle["python_calls"], 1)
        self.assertEqual(handle["last_call"]["after"]["items"], [])
        self.assertIsInstance(handle["last_call"]["actor"], str)

    def test_replicated_item_definition_can_temporarily_be_null(self):
        self.items[0].definition = None
        self.assertIsNone(self.module.inventory_state(self.controller)["items"][0]["definition"])

    def test_no_global_actor_registry_or_direct_property_inventory_writes(self):
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/inventory_clear_mixin.py"
        source = path.read_text(encoding="utf-8")
        for forbidden in ("set_property(", "add_to_root(", "call_mixin_original(\"K2_OnDeathFinished", "_actors =", "_history ="):
            self.assertNotIn(forbidden, source)

    def test_authoring_adds_only_interface_declarations_not_business_graphs(self):
        path = Path(__file__).resolve().parents[1]/"Tools/generate_character_inventory_assets.py"
        source = path.read_text(encoding="utf-8")
        for forbidden in ("make_gate(", "insert_gate(", "graph_add_node", "blueprint_add_member_variable"):
            self.assertNotIn(forbidden, source)
        self.assertIn('implemented_methods=["ClearInventory"]', source)
