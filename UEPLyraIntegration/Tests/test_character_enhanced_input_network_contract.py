"""Authority RPC results, two actual input owners and one-way cleanup."""
import copy
import unittest
from test_character_enhanced_input_contract import report
from uep_lyra_characters.enhanced_input_contract import ACTIONS, PLAN
from uep_lyra_characters.enhanced_input_network_contract import validate


def reports():
    server = dict(status="passed", error=None, run_id="input-model", cases=[], player_ids=dict(A=21, B0=22),
        server_waited_for_client_process_exit=True, all_cleanup_frozen_before_release=True, original_inventory_restored=True,
        server_character_receivers_and_helpers_not_invoked=True, native_input_bindings={key: value[1] for key, value in ACTIONS.items()}, native_rpc_bypassed=False, gameplay_state_delivered_by_files=False, full_acceptance=False)
    clients = []
    for peer in ("A", "B0"):
        client = report(); client.update(peer=peer, run_id=server["run_id"], player_id=server["player_ids"][peer], native_net_mode="Client", native_role=2)
        for index, row in enumerate(client["cases"]):
            row["foreign_actor_input_and_helper_counters_unchanged"] = True
            server["cases"].append(dict(peer=peer, index=index, authority_role=3, other_owner_inventory_unchanged=True, authority_inventory=copy.deepcopy(row["inventory"])))
        clients.append(client)
    return [server, *clients]


class CharacterEnhancedInputNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(*self.reports)
    def test_complete_shape_is_not_runtime_acceptance(self): self.assertEqual(validate(*self.reports)["native_input_owner_trials"], 32)
    def test_second_native_client_required(self): self.reports[2]["cases"] = []; self.reject()
    def test_server_not_simulating_local_input(self): self.reports[0]["server_character_receivers_and_helpers_not_invoked"] = False; self.reject()
    def test_rpc_authority_must_match_native_client_equipment(self): self.reports[0]["cases"][0]["authority_inventory"]["active"] = 1; self.reject()
    def test_other_owner_inventory_must_remain_unchanged(self): self.reports[0]["cases"][0]["other_owner_inventory_unchanged"] = False; self.reject()
    def test_foreign_actor_must_not_replay_input_on_client(self): self.reports[1]["cases"][0]["foreign_actor_input_and_helper_counters_unchanged"] = False; self.reject()
    def test_native_roles_not_only_peer_labels(self): self.reports[2]["native_role"] = 1; self.reject()
    def test_frozen_cleanup_before_disconnect(self): self.reports[0]["all_cleanup_frozen_before_release"] = False; self.reject()
    def test_three_real_process_exits_server_last(self): self.reports[0]["server_waited_for_client_process_exit"] = False; self.reject()
    def test_files_not_gameplay_replication(self): self.reports[0]["gameplay_state_delivered_by_files"] = True; self.reject()
    def test_network_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterInputNetworkResult=x"]), "uep_lyra_characters.enhanced_input_network_validation")
