"""Original loadout decisions and ordered native calls; not runtime proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterLoadoutModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.authority, self.role = [], True, 3
        self.definitions = [types.SimpleNamespace(get_path_name=lambda: "Pistol")]
        self.inventory = types.SimpleNamespace(call_function=self.inventory_call)
        self.quickbar = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        self.controller = object()
        engine = types.ModuleType("unreal_engine")
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        clear = types.ModuleType("uep_lyra_characters.inventory_clear_mixin")
        clear.components = lambda controller: (self.quickbar, self.inventory)
        clear.inventory_state = lambda controller: dict(controller_valid=controller is not None)
        inputs = types.ModuleType("uep_lyra_characters.quickbar_input_mixin")
        class Parent:
            def ClearInventory(self): pass
            def GetEmoteAudioComponent(self): pass
            def SetEmoteAudioComponent(self, AudioComponent): pass
            def ChangeQuickbarSlot(self, NewSlotIndex, SlotActionTag): pass
        inputs.LyraCharacterQuickbarPythonProfile = inputs.LyraCharacterQuickbarBlueprintFallbackProfile = Parent
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/initial_inventory_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._initial_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": engine, native.__name__: native, clear.__name__: clear, inputs.__name__: inputs}):
            spec.loader.exec_module(self.module)
        self.parent, self.python = Parent, self.module.LyraCharacterLoadoutPythonProfile
        self.actor = types.SimpleNamespace(call_function=self.actor_call, get_property=lambda name: self.definitions,
            get_path_name=lambda: "Actor", call_mixin_original=lambda *args: self.calls.append(("original", *args)))

    def actor_call(self, name):
        if name == "HasAuthority": return self.authority
        if name == "GetLocalRole": return self.role
        if name == "GetController": self.calls.append(("GetController",)); return self.controller
        raise AssertionError(name)

    def inventory_call(self, name, definition, count):
        self.calls.append((name, definition, count)); return definition

    def invoke(self): self.python.AddInitialInventory(self.actor)

    def test_remote_guard_precedes_controller_and_all_native_mutations(self):
        self.authority, self.role = False, 2; self.invoke()
        self.assertEqual(self.calls, []); self.assertEqual(self.module.evidence(self.actor)["authority_noops"], 1)

    def test_missing_controller_is_original_guarded_noop(self):
        self.controller = None; self.invoke()
        self.assertEqual(self.calls, [("GetController",)]); self.assertEqual(self.module.evidence(self.actor)["missing_controller_noops"], 1)

    def test_missing_inventory_is_original_guarded_noop(self):
        self.inventory = None; self.invoke()
        self.assertEqual(self.calls, [("GetController",)]); self.assertEqual(self.module.evidence(self.actor)["missing_inventory_noops"], 1)

    def test_missing_quickbar_is_deliberately_safe_without_orphan_grant(self):
        self.quickbar = None; self.invoke()
        self.assertEqual(self.calls, [("GetController",)]); self.assertEqual(self.module.evidence(self.actor)["missing_quickbar_noops"], 1)

    def test_empty_configuration_does_not_activate_an_empty_slot(self):
        self.definitions = []; self.invoke()
        self.assertEqual(self.calls, [("GetController",)]); self.assertEqual(self.module.evidence(self.actor)["slot_zero_requests"], 0)

    def test_native_grant_then_slot_is_interleaved_in_original_array_order(self):
        first, second = self.definitions[0], types.SimpleNamespace(get_path_name=lambda: "Rifle")
        self.definitions = [first, second]; self.invoke()
        self.assertEqual(self.calls, [("GetController",), ("AddItemDefinition", first, 1), ("AddItemToSlot", 0, first),
            ("AddItemDefinition", second, 1), ("AddItemToSlot", 1, second), ("SetActiveSlotIndex", 0)])

    def test_duplicate_definition_is_not_deduplicated(self):
        self.definitions *= 2; self.invoke()
        self.assertEqual(sum(call[0] == "AddItemDefinition" for call in self.calls), 2)

    def test_more_items_than_slots_still_reach_original_native_calls(self):
        self.definitions *= 4; self.invoke()
        self.assertIn(("AddItemToSlot", 3, self.definitions[3]), self.calls)
        self.assertEqual(self.module.evidence(self.actor)["grant_calls"], 4)

    def test_occupied_slots_are_left_to_native_add_not_preemptively_filtered(self):
        self.invoke(); self.assertIn(("AddItemDefinition", self.definitions[0], 1), self.calls)
        self.assertFalse(any(call[0] in ("GetSlots", "GetNextFreeItemSlot") for call in self.calls))

    def test_activation_is_once_after_all_grants_not_once_per_item(self):
        self.definitions *= 3; self.invoke()
        self.assertEqual(self.calls[-1], ("SetActiveSlotIndex", 0)); self.assertEqual(self.calls.count(("SetActiveSlotIndex", 0)), 1)

    def test_every_native_grant_keeps_original_stack_count_one(self):
        self.definitions *= 3; self.invoke()
        self.assertTrue(all(call[2] == 1 for call in self.calls if call[0] == "AddItemDefinition"))

    def test_fallback_calls_only_original_once(self):
        self.module.LyraCharacterLoadoutBlueprintFallbackProfile.AddInitialInventory(self.actor)
        self.assertEqual([call for call in self.calls if call[0] != "GetController"], [("original", "AddInitialInventory")])

    def test_all_four_accepted_helpers_are_explicit_local_aliases(self):
        for profile in (self.python, self.module.LyraCharacterLoadoutBlueprintFallbackProfile):
            for name in ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent", "ChangeQuickbarSlot"):
                self.assertIs(profile.__dict__[name], getattr(self.parent, name))

    def test_evidence_is_per_actor_pod_without_retained_uobjects(self):
        value = self.module.evidence(self.actor); self.invoke()
        self.assertIs(value, self.module.evidence(self.actor)); self.assertEqual(value["last_call"]["configured_definitions"], ["Pistol"])
        self.assertEqual(self.module.evidence(types.SimpleNamespace())["grant_calls"], 0)

    def test_same_actor_profile_calls_do_not_cache_or_replace_configuration(self):
        self.invoke(); self.definitions = []; self.invoke()
        self.assertEqual(self.module.evidence(self.actor)["last_call"]["configured_definitions"], [])
        self.assertEqual(self.module.evidence(self.actor)["grant_calls"], 1)
