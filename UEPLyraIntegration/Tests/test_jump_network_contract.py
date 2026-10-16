"""Network proof gate negatives; fabricated data is not native acceptance."""
import copy
from pathlib import Path
import sys
import unittest
from test_jump_contract import report as client_report

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import jump_network_contract as contract


def reports():
    server = dict(status="passed", error=None, peer="server", run_id="fixture", server_waited_for_client_process_exit=True,
        native_playing_gate=dict(native_playing_phase=True, stable_authority_pawns=[[250, "PawnA"], [251, "PawnB"]]),
        player_ids={"A": 250, "B0": 251}, cases=[], policy_shutdown=dict(activations=14, scopes_created=14,
            scopes_closed=14, active_count=0, errors=[]))
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "ability_activation_called_by_probe",
                  "callback_replay", "authoritative_movement_written", "packet_loss_tested", "travel_rejoin_tested"): server[field] = False
    result = dict(server=server)
    for peer in contract.PEERS:
        client = client_report()
        client.update(peer=peer, run_id="fixture", player_id=server["player_ids"][peer], packet_loss_tested=False, travel_rejoin_tested=False)
        result[peer] = client
        for index in range(len(contract.PLAN)*2):
            profile = ("BlueprintFallback", "Python")[index % 2]
            ack = dict(run_id="fixture", peer=peer, index=index,
                row=copy.deepcopy(client["cases"][index//2]["python" if index % 2 else "blueprint"]))
            server["cases"].append(dict(target=peer, index=index, name=contract.PLAN[index//2], profile=profile,
                authoritative_role=3, native_active_observed=True, authority_final_inactive=True,
                authority_final_grounded=True, other_owner_stayed_idle=True, max_authority_rise=70., client=ack,
                authority_counters={key: int(profile == "Python") for key in
                    ("activations", "states_created", "releases_created", "scopes_created", "scopes_closed")}))
    return result


class JumpNetworkContract(unittest.TestCase):
    def test_complete_two_owner_matrix(self):
        self.assertEqual(contract.validate(reports())["native_authority_trials"], 28)

    def test_reject_host_first_or_foreign_identity(self):
        for field, replacement in (("server_waited_for_client_process_exit", False), ("player_ids", {"A": 250, "B0": 250})):
            value = reports(); value["server"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)
        value = reports(); value["B0"]["run_id"] = "foreign"
        with self.assertRaises(RuntimeError): contract.validate(value)
        value = reports(); value["server"]["native_playing_gate"]["native_playing_phase"] = False
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_missing_authority_or_owner_isolation(self):
        for field, replacement in (("native_active_observed", False), ("max_authority_rise", 0.),
                                   ("authoritative_role", 2), ("other_owner_stayed_idle", False)):
            value = reports(); value["server"]["cases"][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_missing_server_python_execution(self):
        value = reports(); value["server"]["cases"][1]["authority_counters"]["activations"] = 0
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_forged_or_mismatched_ack(self):
        value = reports(); value["server"]["cases"][0]["client"]["row"]["peak_rise"] = 999.
        with self.assertRaises(RuntimeError): contract.validate(value)
        value = reports(); value["server"]["cases"][0]["client"]["peer"] = "B0"
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_missing_case_and_leak(self):
        value = reports(); value["server"]["cases"].pop()
        with self.assertRaises(RuntimeError): contract.validate(value)
        value = reports(); value["server"]["policy_shutdown"]["scopes_closed"] = 13
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_replay_and_unrun_network_claims(self):
        for field in ("callback_replay", "authoritative_movement_written", "packet_loss_tested", "travel_rejoin_tested", "full_acceptance"):
            value = reports(); value["server"][field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)
