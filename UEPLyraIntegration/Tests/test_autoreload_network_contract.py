"""Modeled report gate tests; these are not native network evidence."""
import copy
import unittest
from test_autoreload_contract import report as owner_report
from uep_lyra_abilities import autoreload_network_contract as gate


def reports():
    server = dict(status="passed", error=None, peer="server", run_id="fixture", cases=[],
        original_inventory_restored=True, server_waited_for_client_process_exit=True,
        native_playing_gate=dict(native_playing_phase=True), fixture_authority_inventory_setup=True,
        player_ids={"A": 250, "B0": 251}, policy_shutdown=dict(active_count=0, scopes_created=0, scopes_closed=0, errors=[]))
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "inventory_properties_written", "local_only_authority_activation_called", "native_rpc_bypassed", "gameplay_event_replication_tested"): server[field] = False
    result = dict(server=server)
    for peer in gate.PEERS:
        owner = owner_report(); owner.update(peer=peer, run_id="fixture", player_id=server["player_ids"][peer])
        for field in ("local_inventory_written", "gameplay_event_replication_tested", "native_rpc_bypassed", "packet_loss_tested", "travel_rejoin_tested"): owner[field] = False
        result[peer] = owner
        for index in range(len(gate.PLAN)*2):
            name = gate.PLAN[index//2]; row = owner["cases"][index//2]["python" if index % 2 else "blueprint"]
            ack = {key: copy.deepcopy(value) for key, value in row.items() if key != "fixture_ammo_restored"}
            server["cases"].append(dict(target=peer, index=index, name=name, profile=("BlueprintFallback", "Python")[index % 2],
                authoritative_role=3, other_inventory_unchanged=True, local_only_authority_stayed_inactive=True,
                authority_original_restored=True, authority_final_ammo=[row["final_magazine"], row["final_spare"]],
                minimum_magazine=0, native_reload_active_observed=name in ("empty-spare", "real-fire-auto-reload"),
                client=dict(run_id="fixture", peer=peer, index=index, row=ack)))
    return result


class AutoReloadNetworkGate(unittest.TestCase):
    def test_complete_two_owner_matrix(self): self.assertEqual(gate.validate(reports())["native_authority_trials"], 24)

    def test_reject_localonly_authority_activation_and_other_owner_change(self):
        for field in ("local_only_authority_stayed_inactive", "other_inventory_unchanged", "authority_original_restored"):
            value = reports(); value["server"]["cases"][0][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_client_only_reload_and_fake_empty(self):
        for field, replacement in (("native_reload_active_observed", False), ("minimum_magazine", 1)):
            value = reports(); value["server"]["cases"][6][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_divergent_server_ammo_or_ack(self):
        value = reports(); value["server"]["cases"][0]["authority_final_ammo"][0] = 99
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["cases"][0]["client"]["row"]["tasks_after_end"] = 99
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_matrix_identity_and_scope_leak(self):
        value = reports(); value["server"]["cases"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["B0"]["player_id"] = 250
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["policy_shutdown"]["active_count"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_rpc_bypass_local_ammo_write_and_host_first_exit(self):
        for peer, field in (("server", "native_rpc_bypassed"), ("A", "local_inventory_written"), ("server", "gameplay_event_replication_tested")):
            value = reports(); value[peer][field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["server_waited_for_client_process_exit"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
