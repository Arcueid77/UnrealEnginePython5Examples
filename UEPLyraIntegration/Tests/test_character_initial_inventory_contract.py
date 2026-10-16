"""Reject same-but-wrong native grants, identity recovery and scope inflation."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_characters import initial_inventory_contract as gate
from uep_lyra_hud.startup import validation_module


def grant(actor="Pawn", avatar=False):
    before = dict(items=[dict(path="old", definition=gate.P)] if avatar else [], slots=["old", None, None] if avatar else [None]*3, active=0 if avatar else -1)
    after = dict(items=copy.deepcopy(before["items"])+[dict(path="new", definition=gate.P)], slots=["old" if avatar else "new", None, None], active=0)
    return dict(python_calls=1, fallback_calls=0, grant_calls=1, slot_add_attempts=1, slot_zero_requests=1,
        last_call=dict(profile="Python", authority=True, role=3, actor=actor, configured_definitions=[gate.P], before=before, after=after))


def report():
    rows = []
    for index, (name, profile, definitions, occupied) in enumerate(gate.PLAN):
        counters = dict(python_calls=int(profile == "Python"), fallback_calls=int(profile == "BlueprintFallback"),
            grant_calls=len(definitions)*int(profile == "Python"), slot_add_attempts=len(definitions)*int(profile == "Python"),
            slot_zero_requests=int(profile == "Python" and bool(definitions)), authority_noops=0,
            missing_controller_noops=0, missing_inventory_noops=0, missing_quickbar_noops=0)
        rows.append(dict(name=name, profile=profile, configured_definitions=list(definitions), occupied_first=occupied,
            native_character_class=gate.CLASS, bp_reference_call=True, native_model=gate.expected(index),
            original_item_retained=True, new_items_are_new_identities=True,
            added_items=[dict(path="item"+str(number), definition=definition) for number, definition in enumerate(definitions)], counters=counters,
            configuration_profile_cdo_restored=True, original_inventory_identities_restored=True))
    return dict(status="passed", cases=rows, natural_startup_python_grant=grant(), original_inventory_identities_restored=True,
        configuration_profile_cdo_restored=True, inventory_properties_written=False, python_handler_replayed=False,
        whole_character_migrated=False, full_acceptance=False, replication_tested=False)


class CharacterLoadoutReportModels(unittest.TestCase):
    def test_six_real_pairs_and_natural_startup_shape(self): self.assertEqual(gate.validate(report())["native_bp_call_pairs"], 6)

    def test_missing_reordered_and_failed_cases_rejected(self):
        for mutate in (lambda v: v["cases"].pop(), lambda v: v["cases"].reverse(), lambda v: v.update(status="failed")):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_matching_but_wrong_native_loadout_rejected(self):
        for field, actual in (("items", []), ("slots", [None]*3), ("active", -1), ("definition", "wrong"), ("equipment_class", "wrong"), ("stacks", [])):
            value = report()
            for row in value["cases"][2:4]: row["native_model"][field] = actual
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_stack_one_overflow_and_occupied_extras_not_silently_filtered(self):
        for index in (8, 10):
            value = report(); value["cases"][index]["added_items"].pop()
            with self.subTest(index=index), self.assertRaises(RuntimeError): gate.validate(value)

    def test_grants_must_be_new_distinct_identities_and_retain_original(self):
        for fields in (dict(original_item_retained=False), dict(new_items_are_new_identities=False)):
            value = report(); value["cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][4]["added_items"][1]["path"] = "item0"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_selected_profile_and_native_operation_counts_required(self):
        for fields in (dict(python_calls=0), dict(fallback_calls=1), dict(grant_calls=0), dict(slot_add_attempts=0), dict(slot_zero_requests=0), dict(authority_noops=1)):
            value = report(); value["cases"][3]["counters"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_natural_startup_is_not_replaced_by_manual_probe_success(self):
        for fields in (dict(python_calls=0), dict(fallback_calls=1), dict(grant_calls=2)):
            value = report(); value["natural_startup_python_grant"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_each_trial_and_final_state_must_restore_configuration_cdo_and_identities(self):
        for key in ("original_inventory_identities_restored", "configuration_profile_cdo_restored"):
            for target in ("root", "row"):
                value = report(); (value if target == "root" else value["cases"][0])[key] = False
                with self.subTest(key=key, target=target), self.assertRaises(RuntimeError): gate.validate(value)

    def test_bp_reference_call_and_original_class_required(self):
        for fields in (dict(bp_reference_call=False), dict(native_character_class="PythonSubclass")):
            value = report(); value["cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_inventory_writes_handler_replay_and_full_acceptance_rejected(self):
        for key in ("inventory_properties_written", "python_handler_replayed", "whole_character_migrated", "full_acceptance", "replication_tested"):
            value = report(); value[key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_natural_and_manual_startup_selectors_are_explicit(self):
        self.assertEqual(validation_module(["-UEPCharacterLoadoutResult=x"]), "uep_lyra_characters.initial_inventory_validation")
        self.assertEqual(validation_module(["-UEPCharacterLoadoutResult=x", "-UEPCharacterLoadoutNatural"]), "uep_lyra_characters.initial_inventory_natural_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterLoadoutResult=x"]))
