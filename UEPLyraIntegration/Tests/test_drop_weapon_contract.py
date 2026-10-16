"""DropWeapon report gate models, not native inventory/replication evidence."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import drop_weapon_contract as gate


def report():
    result = dict(status="passed", error=None, cases=[], original_player_restored=True, fixture_native_authority_inventory_api=True,
        policy_shutdown=dict(active_count=0, errors=[]))
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed",
        "ability_activation_called_by_probe", "inventory_or_slots_written_as_properties", "world_pickup_spawned"): result[field] = False
    for name, extra, initial, expected in gate.PLAN:
        row = dict(native_type_preserved=True, original_item_identities_preserved=True, removed_item_absent=True,
            dropped_slot_empty=True, native_ability_inactive=True, fixture_original_restored=True, no_late_activation=True,
            active_slot=expected, input_injections=1, inventory_model=dict(active=expected, equipment_instigator_matches=True),
            counters=dict(activations=1, authority_branches=1, cycles=1, native_ends=1, items_removed=int(extra > 0), client_branches=0))
        result["cases"].append(dict(name=name, blueprint=copy.deepcopy(row), python=copy.deepcopy(row)))
    return result


class DropWeaponGate(unittest.TestCase):
    def test_complete_matrix(self): self.assertEqual(gate.validate(report())["pairs"], 4)

    def test_reject_wrong_item_slot_original_identity_and_late_input(self):
        for field in ("removed_item_absent", "dropped_slot_empty", "original_item_identities_preserved", "no_late_activation"):
            value = report(); value["cases"][0]["python"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_replayed_activation_property_write_and_added_pickup(self):
        for field in ("ability_activation_called_by_probe", "inventory_or_slots_written_as_properties", "world_pickup_spawned"):
            value = report(); value[field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_diff_missing_python_path_and_unrestored_fixture(self):
        value = report(); value["cases"][0]["python"]["inventory_model"]["active"] = 9
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["python"]["counters"]["activations"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["original_player_restored"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
