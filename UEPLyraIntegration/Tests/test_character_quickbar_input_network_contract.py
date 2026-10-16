"""Native owner/authority evidence must match; files carry rendezvous only."""
import copy
import unittest
from test_character_quickbar_input_contract import report as local
from uep_lyra_characters import quickbar_input_network_contract as gate
from uep_lyra_hud.startup import validation_module


def reports():
    values = {peer: dict(local(), peer=peer, run_id="test", player_id=index+1, native_role=2, native_net_mode="Client",
        authority_phase_gate_observed=True, network_acceptance=True, local_inventory_written=False, gameplay_state_delivered_by_files=False)
        for index, peer in enumerate(("A", "B0"))}
    rows = [dict(peer=peer, index=index, authority_role=3, other_owner_inventory_unchanged=True,
        authority_inventory=copy.deepcopy(row["inventory"]), client=copy.deepcopy(row))
        for peer in ("A", "B0") for index, row in enumerate(values[peer]["cases"])]
    values["server"] = dict(status="passed", run_id="test", player_ids=dict(A=1, B0=2), cases=rows,
        native_playing_gate=dict(native_playing_phase=True), server_waited_for_client_process_exit=True,
        original_inventory_restored=True, server_character_helpers_not_invoked=True, native_rpc_bypassed=False,
        gameplay_state_delivered_by_files=False)
    return values


class CharacterSlotNetworkModels(unittest.TestCase):
    def test_two_real_owners_and_28_authority_results(self): self.assertEqual(gate.validate(reports())["authority_trials"], 28)

    def test_missing_client_or_case_rejected(self):
        for mutate in (lambda v: v.pop("B0"), lambda v: v["server"]["cases"].pop(), lambda v: v["A"]["cases"].pop()):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_authority_owner_inventory_and_foreign_owner_must_match(self):
        for fields in (dict(authority_role=2), dict(other_owner_inventory_unchanged=False), dict(peer="B0"), dict(index=1)):
            value = reports(); value["server"]["cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["cases"][0]["authority_inventory"]["active"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_playing_restore_and_server_last_exit_required(self):
        for fields in (dict(native_playing_gate=dict(native_playing_phase=False)), dict(original_inventory_restored=False),
            dict(server_waited_for_client_process_exit=False), dict(server_character_helpers_not_invoked=False)):
            value = reports(); value["server"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_actual_owner_role_identity_and_native_mode_required(self):
        for fields in (dict(native_role=3), dict(player_id=2), dict(native_net_mode="Standalone"), dict(run_id="other"), dict(authority_phase_gate_observed=False)):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_client_ack_is_the_same_native_report_not_just_correct_active_slot(self):
        value = reports(); value["server"]["cases"][0]["client"]["events"][0]["magnitude"] = 99.
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_rpc_bypass_or_gameplay_file_delivery_rejected(self):
        for peer, fields in (("server", dict(native_rpc_bypassed=True)), ("server", dict(gameplay_state_delivered_by_files=True)),
            ("A", dict(local_inventory_written=True)), ("A", dict(gameplay_state_delivered_by_files=True))):
            value = reports(); value[peer].update(fields)
            with self.subTest(peer=peer, fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_explicit_network_selection_does_not_run_in_commandlet(self):
        self.assertEqual(validation_module(["-UEPCharacterQuickbarNetworkResult=x"]), "uep_lyra_characters.quickbar_input_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterQuickbarNetworkResult=x"]))
