"""Reject missing, replayed and identical-but-wrong Character input evidence."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_characters import quickbar_input_contract as gate
from uep_lyra_hud.startup import validation_module


def report():
    rows = []
    for name, profile, initial, slot, tag, expected, empty in gate.PLAN:
        sent = not empty and 0 <= slot < 3
        counters = dict(python_calls=int(profile == "Python"), fallback_calls=int(profile == "BlueprintFallback"),
            events_sent=int(profile == "Python" and sent), empty_slot_noops=int(profile == "Python" and empty),
            invalid_index_noops=int(profile == "Python" and not 0 <= slot < 3), missing_controller_noops=0, missing_quickbar_noops=0)
        model = dict(items=sorted(gate.DEFINITIONS), slots=gate.DEFINITIONS[:2]+[None if empty else gate.DEFINITIONS[2]],
            active=expected, definition=gate.DEFINITIONS[expected], equipment_instigator_matches=True,
            equipment_class=gate.DEFINITIONS[expected].replace("/ID_", "/B_WeaponInstance_").replace(".ID_", ".B_WeaponInstance_"))
        rows.append(dict(name=name, profile=profile, initial=initial, slot=slot, tag=tag, empty_slot=empty,
            native_character_class=gate.CLASS, bp_reference_call=True, inventory=model, inventory_items_unchanged=True, counters=counters,
            events=[dict(tag=tag, magnitude=float(slot), instigator_null=True, target_null=True, optional_objects_null=True)] if sent else [],
            callback_errors=[], native_tasks_before=3, native_tasks_after=3, task_scope_closed=True))
    return dict(status="passed", cases=rows, scopes_created=14, scopes_closed=14, active_observation_scopes=0,
        original_fields_profile_cdo_restored=True, original_inventory_restored=True, native_quickslot_ability_active_with_three_tasks=True,
        **{key: False for key in ("physical_keyboard_tested", "python_handler_replayed", "inventory_properties_written", "native_rpc_bypassed",
            "gameplay_event_replication_claimed", "whole_character_migrated", "full_acceptance")})


class CharacterSlotReportModels(unittest.TestCase):
    def test_bounded_plan_has_six_native_pairs_and_two_python_only_safety_cases(self):
        result = gate.validate(report()); self.assertEqual((result["cases"], result["original_python_pairs"], result["python_only_invalid_index_cases"]), (14, 6, 2))

    def test_missing_reordered_or_failed_cases_rejected(self):
        for mutate in (lambda r: r["cases"].pop(), lambda r: r["cases"].reverse(), lambda r: r.update(status="failed")):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_wrong_native_active_slot_rejected_even_if_pair_is_identically_wrong(self):
        value = report()
        for row in value["cases"][:2]: row["inventory"]["active"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_identically_wrong_native_item_definition_rejected(self):
        value = report()
        for row in value["cases"][:2]: row["inventory"]["definition"] = "wrong"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_payload_tag_magnitude_and_original_default_objects_required(self):
        for fields in (dict(tag="wrong"), dict(magnitude=99.), dict(instigator_null=False), dict(target_null=False), dict(optional_objects_null=False)):
            value = report(); value["cases"][0]["events"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_missing_native_event_and_empty_slot_accidental_send_rejected(self):
        for index in (0, 8):
            value = report()
            value["cases"][index]["events"] = [] if index == 0 else copy.deepcopy(value["cases"][0]["events"])
            with self.subTest(index=index), self.assertRaises(RuntimeError): gate.validate(value)

    def test_handler_routing_and_task_lifetime_must_be_exact(self):
        for fields in (dict(native_tasks_after=4), dict(task_scope_closed=False), dict(callback_errors=["error"]), dict(bp_reference_call=False)):
            value = report(); value["cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][1]["counters"]["python_calls"] = 2
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_real_restore_and_closed_observer_scopes_required(self):
        for fields in (dict(original_fields_profile_cdo_restored=False), dict(original_inventory_restored=False),
            dict(scopes_closed=13), dict(active_observation_scopes=1), dict(native_quickslot_ability_active_with_three_tasks=False)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_hardware_rpc_replication_and_whole_asset_claims_rejected(self):
        for key in ("physical_keyboard_tested", "python_handler_replayed", "inventory_properties_written", "native_rpc_bypassed",
                "gameplay_event_replication_claimed", "whole_character_migrated", "full_acceptance"):
            value = report(); value[key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_explicit_selection_excludes_commandlet(self):
        self.assertEqual(validation_module(["-UEPCharacterQuickbarResult=x"]), "uep_lyra_characters.quickbar_input_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterQuickbarResult=x"]))
