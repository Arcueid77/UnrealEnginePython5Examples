"""Per-world real hide/undo does not certify hide replication or network death."""
import unittest
import test_character_begin_play_network_contract as begin_models
from test_character_equipment_hide_contract import upgrade, counts, CLASS
from uep_lyra_characters.equipment_hide_network_contract import validate


def reports():
    values = begin_models.reports()
    for peer, value in values.items():
        upgrade(value); value.update(peer=peer, equipment_hide_replication_tested=False, network_death_hide_ingress_tested=False, network_equipment_hide_cases=[])
        for target in (("A", "B0") if peer == "server" else (peer,)):
            for profile in ("BlueprintFallback", "Python"):
                value["network_equipment_hide_cases"].append(dict(target=target, profile=profile, actual_character_class=CLASS, instances=1,
                    spawned_actor_paths=["native-weapon"], bp_reference_call=True, native_all_hidden=True, native_pawn_hidden_unchanged=True,
                    original_visibility_restored=True, inventory_identity_restored=True, profile_restored=True,
                    counters=counts(profile == "Python"), native_role=3 if peer == "server" else 2))
    return values


class CharacterEquipmentHideNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.reports)
    def test_complete_shape_is_model(self): self.assertEqual(validate(self.reports)["local_native_network_equipment_hide_calls"], 8)
    def test_native_owner_hide_required(self): self.reports["A"]["network_equipment_hide_cases"][1]["native_all_hidden"] = False; self.reject()
    def test_exact_original_visibility_restore(self): self.reports["server"]["network_equipment_hide_cases"][0]["original_visibility_restored"] = False; self.reject()
    def test_no_hide_replication_claim(self): self.reports["server"]["equipment_hide_replication_tested"] = True; self.reject()
    def test_no_network_death_claim(self): self.reports["B0"]["network_death_hide_ingress_tested"] = True; self.reject()
    def test_actual_native_role(self): self.reports["A"]["network_equipment_hide_cases"][0]["native_role"] = 3; self.reject()
    def test_inventory_identity_unchanged(self): self.reports["A"]["network_equipment_hide_cases"][0]["inventory_identity_restored"] = False; self.reject()
