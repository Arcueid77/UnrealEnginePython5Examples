"""DropWeapon network report models; not native replication evidence."""
import copy
import unittest
from test_drop_weapon_contract import report as owner_report
from uep_lyra_abilities import drop_weapon_network_contract as gate


def reports():
    server = dict(status="passed", error=None, run_id="fixture", cases=[], original_inventory_restored=True,
        server_waited_for_client_process_exit=True, native_playing_gate=dict(native_playing_phase=True),
        fixture_authority_inventory_setup=True, player_ids={"A": 250, "B0": 251}, policy_shutdown=dict(active_count=0, errors=[]))
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "native_rpc_bypassed", "inventory_properties_written", "gameplay_event_replication_tested"): server[field] = False
    result = dict(server=server)
    for peer in gate.PEERS:
        owner = owner_report()
        owner.update(peer=peer, run_id="fixture", player_id=server["player_ids"][peer], native_net_mode="Client")
        for field in ("local_inventory_written", "native_rpc_bypassed", "gameplay_event_replication_tested", "packet_loss_tested", "travel_rejoin_tested"): owner[field] = False
        result[peer] = owner
        for index in range(len(gate.PLAN)*2):
            name, count, initial, expected = gate.PLAN[index//2]
            client = owner["cases"][index//2]["python" if index % 2 else "blueprint"]
            counts = client["counters"]
            counts.update(fallback_activations=0, fallback_native_ends=0)
            if index % 2: counts.update(authority_branches=0, cycles=0, items_removed=0, client_branches=1)
            else:
                for key in counts: counts[key] = 0
                counts.update(fallback_activations=1, fallback_native_ends=1)
            authority = copy.deepcopy(counts)
            if index % 2: authority.update(authority_branches=1, cycles=1, items_removed=int(count > 0), client_branches=0)
            row = dict(target=peer, index=index, name=name, authoritative_role=3, expected_slot=expected,
                foreign_owner_unchanged=True, removed_item_absent=True, dropped_slot_empty=True, original_item_identities_preserved=True,
                native_ability_inactive=True, authority_original_restored=True, authority_counters=authority,
                authority_inventory_model=copy.deepcopy(client["inventory_model"]), client=dict(run_id="fixture", peer=peer, index=index,
                    row={key: copy.deepcopy(value) for key, value in client.items() if key != "fixture_original_restored"}))
            server["cases"].append(row)
    return result


class DropWeaponNetworkGate(unittest.TestCase):
    def test_complete_matrix(self): self.assertEqual(gate.validate(reports())["native_authority_trials"], 16)

    def test_reject_client_inventory_write_and_rpc_bypass(self):
        for field in ("local_inventory_written", "native_rpc_bypassed", "gameplay_event_replication_tested"):
            value = reports(); value["A"][field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_authority_effect_and_foreign_owner_change(self):
        for field in ("removed_item_absent", "dropped_slot_empty", "foreign_owner_unchanged", "original_item_identities_preserved", "authority_original_restored"):
            value = reports(); value["server"]["cases"][0][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["cases"][1]["authoritative_role"] = 2
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_forged_ack_and_different_replicated_equipment(self):
        value = reports(); value["server"]["cases"][0]["client"]["row"]["input_injections"] = 2
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["cases"][0]["authority_inventory_model"]["active"] = 2
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_case_unrestored_fixture_and_host_first_exit(self):
        value = reports(); value["server"]["cases"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)
        for field in ("original_inventory_restored", "server_waited_for_client_process_exit"):
            value = reports(); value["server"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_original_bp_not_running_and_python_authority_bypassed(self):
        value = reports(); value["server"]["cases"][0]["authority_counters"]["fallback_native_ends"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["cases"][1]["authority_counters"]["items_removed"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)
