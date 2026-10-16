"""Equipment integration report models; no native networking from these tests."""
import copy
import unittest
from test_reload_magazine_network_contract import family_reports
from uep_lyra_weapons import weapon_instance_network_contract as gate


def reports():
    result = family_reports("rifle")
    for peer in ("server",)+gate.PEERS:
        ids = list(result["server"]["player_ids"].values()) if peer == "server" else [result["server"]["player_ids"][peer]]
        evidence = dict(read_only=True, restored=True, errors=[], scripted_replication=False, animation_state_written=False, initials={}, events=[],
            profile="Python", fixture_cdo_profile_selector_written=False, cdo_profile_selector_restored=True)
        for player_id in ids:
            state = dict(tags=["native-style"], selected_layer="native-layer", linked_layer="native-layer", montage="native-montage", montage_playing=True, dead_or_dying=False)
            counts = dict(equips=1, unequips=1, tag_queries=1, layer_picks=2, montage_calls=2)
            evidence["initials"][str(player_id)] = dict(native_class="original-rifle-class", native_role=3 if peer == "server" else 2,
                source_item_matches=True, profile="Python", counters=copy.deepcopy(counts), state=copy.deepcopy(state), native_cosmetic_tags=["native-style"])
            for equipped in (True, False):
                evidence["events"].append(dict(player_id=player_id, native_class="original-rifle-class", native_role=3 if peer == "server" else 2,
                    instance=peer+str(player_id), equipped=equipped, profile="Python", state=copy.deepcopy(state), counters=copy.deepcopy(counts), native_cosmetic_tags=["native-style"]))
        result[peer]["equipment_integration"] = evidence
    return result


class EquipmentNetworkGate(unittest.TestCase):
    def test_complete_native_owner_authority_matrix(self): self.assertEqual(gate.validate(reports())["actual_owners"], 2)

    def test_dedicated_server_native_cosmetics_can_be_empty(self):
        value = reports(); evidence = value["server"]["equipment_integration"]
        for row in list(evidence["initials"].values())+evidence["events"]:
            row["state"]["tags"] = []; row["native_cosmetic_tags"] = []
        self.assertEqual(gate.validate(value)["actual_owners"], 2)

    def test_native_female_owner_layer_can_differ_from_dedicated_server(self):
        value = reports(); evidence = value["A"]["equipment_integration"]
        for row in list(evidence["initials"].values())+evidence["events"]:
            row["state"].update(tags=["native-female"], selected_layer="native-female-layer", linked_layer="native-female-layer")
            row["native_cosmetic_tags"] = ["native-female"]
        self.assertEqual(gate.validate(value)["actual_owners"], 2)
        evidence["events"][0]["state"]["montage"] = "different-montage"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_original_blueprint_baseline_requires_actual_original_counters(self):
        value = reports()
        for peer in ("server",)+gate.PEERS:
            evidence = value[peer]["equipment_integration"]
            evidence.update(profile="BlueprintFallback", fixture_cdo_profile_selector_written=True)
            for row in list(evidence["initials"].values())+evidence["events"]:
                row["profile"] = "BlueprintFallback"
                row["counters"] = dict(equips=0, unequips=0, tag_queries=0, layer_picks=0, montage_calls=0,
                    fallback_equips=1, fallback_unequips=1, fallback_tag_queries=1)
        self.assertEqual(gate.validate(value)["actual_owners"], 2)
        value["A"]["equipment_integration"]["events"][0]["counters"]["equips"] = 1
        # The final per-instance snapshot must also show the forbidden business.
        value["A"]["equipment_integration"]["events"][-1]["counters"]["equips"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_native_remove_and_wrong_role(self):
        value = reports(); value["A"]["equipment_integration"]["events"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_wrong_native_layer_and_client_authority_difference(self):
        value = reports(); value["A"]["equipment_integration"]["events"][0]["state"]["linked_layer"] = None
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["A"]["equipment_integration"]["events"][0]["state"]["tags"] = ["other-style"]
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_scripted_replication_and_missing_observer_restore(self):
        value = reports(); value["server"]["equipment_integration"]["scripted_replication"] = True
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["A"]["equipment_integration"]["restored"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["B0"]["equipment_integration"]["events"][0]["native_role"] = 3
        with self.assertRaises(RuntimeError): gate.validate(value)
