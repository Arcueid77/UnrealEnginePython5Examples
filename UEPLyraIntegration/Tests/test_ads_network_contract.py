"""Two-client ADS report models; no in-engine proof from these tests."""
import copy
import unittest
from test_ads_contract import report as owner_report
from uep_lyra_abilities import ads_network_contract as gate


def reports():
    server = dict(status="passed", error=None, peer="server", run_id="fixture", cases=[], original_player_states_restored=True,
        server_waited_for_client_process_exit=True, native_playing_gate=dict(native_playing_phase=True), player_ids={"A": 250, "B0": 251},
        policy_shutdown=dict(active_count=0, scopes_created=12, scopes_closed=12, helpers_rooted=0, helpers_unrooted=0, errors=[]))
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "native_rpc_bypassed", "camera_or_speed_written_by_probe", "mapping_context_written_by_probe", "ui_message_replication_tested"): server[field] = False
    result = dict(server=server)
    for peer in gate.PEERS:
        owner = owner_report(); owner["cases"].pop(); owner["source_scopes_created"] = owner["source_scopes_closed"] = 10
        owner.update(peer=peer, run_id="fixture", player_id=server["player_ids"][peer], native_net_mode="Client", paused_world_scope="standalone only; network pause not tested")
        for field in ("local_camera_speed_mapping_written_by_probe", "ui_message_replication_tested", "native_rpc_bypassed", "packet_loss_tested", "travel_rejoin_tested"): owner[field] = False
        result[peer] = owner
        for index in range(len(gate.PLAN)*2):
            row = owner["cases"][index//2]["python" if index % 2 else "blueprint"]
            counts = copy.deepcopy(row["counters"])
            for field in ("ui_on", "ui_off", "mappings_added", "mappings_removed"): counts[field] = 0
            server["cases"].append(dict(target=peer, index=index, name=gate.PLAN[index//2], authoritative_role=3,
                authority_tasks_after=0, native_active_observed=True, native_half_speed_observed=True, native_camera_mode_observed=True,
                native_wait_task_observed=True, foreign_owner_unchanged=True, authority_original_restored=True,
                authority_counters=counts, client=dict(run_id="fixture", peer=peer, index=index, row=copy.deepcopy(row))))
    return result


class ADSNetworkGate(unittest.TestCase):
    def test_complete_matrix(self): self.assertEqual(gate.validate(reports())["native_authority_trials"], 20)

    def test_reject_client_only_camera_or_speed_and_foreign_owner_change(self):
        for field in ("native_half_speed_observed", "native_camera_mode_observed", "native_wait_task_observed", "foreign_owner_unchanged"):
            value = reports(); value["server"]["cases"][0][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_server_executing_local_mapping_or_ui(self):
        for field in ("ui_on", "ui_off", "mappings_added", "mappings_removed"):
            value = reports(); value["server"]["cases"][0]["authority_counters"][field] = 1
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_owner_matrix_restore_and_host_first(self):
        value = reports(); value["server"]["cases"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["server_waited_for_client_process_exit"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_forged_ack_or_scope_leak(self):
        value = reports(); value["server"]["cases"][0]["client"]["row"]["source_ui_events"] = []
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["policy_shutdown"]["scopes_closed"] = 11
        with self.assertRaises(RuntimeError): gate.validate(value)
