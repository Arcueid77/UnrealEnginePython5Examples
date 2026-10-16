"""Reject two-owner report overclaims; modeled data only."""
import copy
from pathlib import Path
import sys
import unittest
from test_quickslot_contract import report as client_report
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import quickslot_network_contract as contract


def reports():
    server = dict(status="passed", error=None, peer="server", run_id="fixture", original_inventory_restored=True,
        server_waited_for_client_process_exit=True, native_playing_gate=dict(native_playing_phase=True),
        player_ids={"A": 250, "B0": 251}, cases=[], policy_shutdown=dict(activations=40, tasks_created=120,
            scopes_created=40, scopes_closed=40, active_count=0, errors=[]))
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
                  "inventory_properties_written", "native_rpc_bypassed", "ui_presentation_comparison_tested", "gameplay_event_replication_tested"): server[field] = False
    result = dict(server=server)
    for peer in contract.PEERS:
        client = client_report(); client.update(peer=peer, run_id="fixture", player_id=server["player_ids"][peer],
            local_inventory_written=False, local_movement_written=False, ui_presentation_comparison_tested=False, gameplay_event_replication_tested=False)
        result[peer] = client
        for index in range(len(contract.PLAN)*2):
            name, _, selected = contract.PLAN[index//2]
            row = client["cases"][index//2]["python" if index % 2 else "blueprint"]
            server["cases"].append(dict(target=peer, index=index, name=name, profile=("BlueprintFallback", "Python")[index % 2],
                expected_slot=selected, authoritative_role=3, other_inventory_unchanged=True,
                authority_inventory=copy.deepcopy(row["inventory"]), client=dict(run_id="fixture", peer=peer, index=index, row=copy.deepcopy(row))))
    return result


class QuickslotNetworkContract(unittest.TestCase):
    def test_complete_two_owner_matrix(self): self.assertEqual(contract.validate(reports())["native_authority_trials"], 40)

    def test_reject_host_first_or_unrestored_inventory(self):
        for field in ("server_waited_for_client_process_exit", "original_inventory_restored"):
            value = reports(); value["server"][field] = False
            with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_wrong_authority_or_foreign_inventory_change(self):
        for field, replacement in (("authoritative_role", 2), ("other_inventory_unchanged", False), ("expected_slot", 99)):
            value = reports(); value["server"]["cases"][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_mismatched_ack_and_identity(self):
        value = reports(); value["server"]["cases"][0]["authority_inventory"]["active"] = 99
        with self.assertRaises(RuntimeError): contract.validate(value)
        value = reports(); value["B0"]["player_id"] = 250
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_replay_and_event_replication_or_ui_overclaim(self):
        for field in ("callback_replay", "native_rpc_bypassed", "ui_presentation_comparison_tested", "gameplay_event_replication_tested"):
            value = reports(); value["server"][field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_matrix_and_task_leak(self):
        value = reports(); value["server"]["cases"].pop()
        with self.assertRaises(RuntimeError): contract.validate(value)
        value = reports(); value["server"]["policy_shutdown"]["scopes_closed"] = 39
        with self.assertRaises(RuntimeError): contract.validate(value)
