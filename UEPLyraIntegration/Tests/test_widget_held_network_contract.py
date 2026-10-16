"""LocalOnly native network report models; not actual network acceptance."""
import copy
from pathlib import Path
import sys
import unittest
from test_widget_held_contract import fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_abilities import widget_held_network_contract as gate


def reports():
    server = dict(status="passed", error=None, peer="server", run_id="fixture", cases=[], original_player_states_restored=True,
        server_waited_for_client_process_exit=True, native_playing_gate=dict(native_playing_phase=True), player_ids={"A": 251, "B0": 252},
        policy_shutdown=dict(activations=0, fallback_activations=0, active_count=0, scopes_created=0, scopes_closed=0, errors=[]))
    flags = ("full_acceptance", "packaged_runtime", "physical_input_tested", "ability_activation_called_by_probe", "callback_replay",
             "packet_loss_tested", "travel_rejoin_tested", "gameplay_state_delivered_by_files", "localonly_ui_replication_claimed", "network_pause_tested")
    server.update({key: False for key in flags})
    result = dict(server=server)
    for peer in gate.PEERS:
        other = next(value for value in gate.PEERS if value != peer)
        owner = fixture()
        owner.update(targets=["tdm"], safety_regressions=[], cases=[row for row in owner["cases"]
            if row["target"] == "tdm" and row["name"] in gate.NETWORK_PLAN], peer=peer, run_id="fixture",
            player_id=server["player_ids"][peer], native_owner_role=2, native_net_mode="Client", passive_held_observations=[])
        owner.update({key: False for key in flags})
        result[peer] = owner
        for index in range(len(gate.NETWORK_PLAN) * 2):
            row = owner["cases"][index // 2][("blueprint", "python")[index % 2]]
            passive = dict(run_id="fixture", peer=other, target=peer, index=index, stage="held", player_id=server["player_ids"][other],
                native_owner_unchanged=True, native_ability_inactive=True, native_tasks=0, native_menu_empty=True)
            server["cases"].append(dict(target=peer, index=index, name=gate.NETWORK_PLAN[index // 2],
                profile=("BlueprintFallback", "Python")[index % 2], authority_inactive_samples=3,
                native_localonly_authority_unchanged=True, foreign_local_owner_observed=True, passive=passive,
                client=dict(run_id="fixture", peer=peer, index=index, row=copy.deepcopy(row))))
    for peer in gate.PEERS:
        result[peer]["passive_held_observations"] = [copy.deepcopy(row["passive"]) for row in server["cases"] if row["target"] != peer]
    return result


class HeldNetworkGate(unittest.TestCase):
    def test_complete_synthetic_report_shape(self):
        self.assertEqual(gate.validate_network(reports())["native_rows"], 24)

    def test_requires_two_distinct_actual_native_clients(self):
        for mutate in (lambda data: data.pop("B0"), lambda data: data["A"].update(native_owner_role=3),
                       lambda data: data["A"].update(player_id=252), lambda data: data["A"].update(native_net_mode="Standalone")):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_authority_must_remain_inactive_without_owned_scope(self):
        for mutate in (lambda data: data["server"]["cases"][0].update(native_localonly_authority_unchanged=False),
                       lambda data: data["server"]["cases"][0].update(authority_inactive_samples=0),
                       lambda data: data["server"]["policy_shutdown"].update(activations=1),
                       lambda data: data["server"]["policy_shutdown"].update(scopes_created=1)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_requires_independent_foreign_local_ui_for_every_held_trial(self):
        for mutate in (lambda data: data["A"]["passive_held_observations"].pop(),
                       lambda data: data["B0"]["passive_held_observations"][0].update(native_menu_empty=False),
                       lambda data: data["server"]["cases"][0].update(foreign_local_owner_observed=False)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_ack_identity_or_final_observation_mismatch_is_rejected(self):
        for mutate in (lambda data: data["server"]["cases"][0]["client"].update(index=7),
                       lambda data: data["server"]["cases"][0]["client"].update(run_id="foreign"),
                       lambda data: data["server"]["cases"][0]["client"]["row"].update(input_injections=99),
                       lambda data: data["server"]["cases"][0]["passive"].update(peer="A"),
                       lambda data: data["server"]["cases"][0]["passive"].update(native_tasks=1)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_travel_or_replicated_ui_claim_and_incomplete_exits_are_rejected(self):
        for mutate in (lambda data: data["A"].update(localonly_ui_replication_claimed=True),
                       lambda data: data["B0"].update(travel_rejoin_tested=True),
                       lambda data: data["server"].update(server_waited_for_client_process_exit=False),
                       lambda data: data["server"]["cases"].pop()):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate_network(value)


if __name__ == "__main__":
    unittest.main()
