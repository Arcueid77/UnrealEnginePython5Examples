"""Emote network report models, explicitly not native networking evidence."""
import copy
import unittest
from test_emote_contract import report as owner_report
from uep_lyra_abilities import emote_network_contract as gate


def reports():
    server = dict(status="passed", error=None, peer="server", run_id="fixture", cases=[], original_player_states_restored=True,
        original_profiles_restored=True, server_waited_for_client_process_exit=True, native_playing_gate=dict(native_playing_phase=True),
        player_ids={"A": 250, "B0": 251}, policy_shutdown=dict(active_count=0, scopes_created=20, scopes_closed=20, errors=[]))
    flags = ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "ability_activation_called_by_probe", "native_rpc_bypassed", "packet_loss_tested", "travel_rejoin_tested",
        "network_movement_interruption_tested", "network_crouch_interruption_tested", "network_pause_tested", "gameplay_state_delivered_by_files")
    server.update({field: False for field in flags})
    result = dict(server=server)
    for peer in gate.PEERS:
        owner = owner_report()
        owner["cases"] = [row for row in owner["cases"] if row["name"] in gate.PLAN]
        owner.update(peer=peer, run_id="fixture", player_id=server["player_ids"][peer], native_net_mode="Client", native_owner_role=2,
            native_external_movement_fixture=False, native_movement_producer="not exercised in this network batch",
            fixture_scopes_created=10, fixture_scopes_closed=10)
        for field in flags:
            if field not in owner: owner[field] = False
        result[peer] = owner
        for index in range(len(gate.PLAN) * 2):
            row = owner["cases"][index // 2]["python" if index % 2 else "blueprint"]
            counts = copy.deepcopy(row["counters"]); counts["fallback_activations"] = 1
            server["cases"].append(dict(target=peer, index=index, name=gate.PLAN[index // 2], authoritative_role=3,
                authority_tasks_after=0, native_active_observed=True, native_montage_observed=True, native_task_observed=True,
                foreign_owner_unchanged=True, authority_original_restored=True, native_type_source_preserved=True,
                actual_authority_held=True, authority_counters=counts,
                client=dict(run_id="fixture", peer=peer, index=index, row=copy.deepcopy(row))))
    return result


class EmoteNetworkGate(unittest.TestCase):
    def test_complete_native_report_model(self):
        self.assertEqual(gate.validate(reports())["native_authority_trials"], 20)

    def test_rejects_client_only_animation_missing_authority_or_foreign_mutation(self):
        for field in ("native_active_observed", "native_montage_observed", "native_task_observed", "foreign_owner_unchanged",
                      "native_type_source_preserved", "actual_authority_held"):
            value = reports(); value["server"]["cases"][0][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_rejects_owner_identity_role_replay_and_widened_scope(self):
        for mutation in (lambda r: r["A"].update(native_owner_role=3), lambda r: r["A"].update(player_id=251),
            lambda r: r["server"].update(native_rpc_bypassed=True), lambda r: r["server"].update(network_pause_tested=True),
            lambda r: r["server"].update(gameplay_state_delivered_by_files=True), lambda r: r["server"]["cases"].pop()):
            value = reports(); mutation(value)
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError): gate.validate(value)

    def test_rejects_mismatched_ack_source_and_leaked_authority_scope(self):
        for mutation in (lambda r: r["server"]["cases"][0]["client"].update(index=7),
            lambda r: r["server"]["cases"][1]["authority_counters"].update(scopes_closed=1),
            lambda r: r["server"].update(server_waited_for_client_process_exit=False)):
            value = reports(); mutation(value)
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError): gate.validate(value)


if __name__ == "__main__": unittest.main()
