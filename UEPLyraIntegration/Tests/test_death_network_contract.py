"""Reject fabricated/incomplete native network proof; models are not acceptance."""
import copy
import importlib.util
from pathlib import Path
import unittest
from test_death_contract import report as standalone

file = Path(__file__).resolve().parents[1]/"Tools/validate_death_network_reports.py"
spec = importlib.util.spec_from_file_location("death_network_report_gate", file)
gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)


def reports():
    template = standalone()
    base = dict(status="passed", error=None, run_id="native-run", cases=[])
    for flag in ("full_acceptance", "packaged_runtime", "physical_input_tested", "death_event_sent_by_probe", "ability_activation_called_by_probe",
                 "callback_replay", "health_properties_written", "death_duration_written", "packet_loss_tested", "travel_rejoin_tested"):
        base[flag] = False
    server = dict(copy.deepcopy(base), peer="server", server_waited_for_client_process_exit=True,
        native_playing_gate=dict(native_playing_phase=True), real_lethal_gas_damage=True, player_ids=dict(A=1, B0=2),
        source_scopes_created=20, source_scopes_closed=20)
    clients = {peer: dict(copy.deepcopy(base), peer=peer, player_id=index+1, cue_observer_restored=True) for index, peer in enumerate(gate.PEERS)}
    for peer, row in dict(server=server, **clients).items():
        count = len(gate.PLAN)*(2 if peer == "server" else 1)
        row["policy_shutdown"] = {key: count for key in ("activations", "cameras_set", "cues_executed", "waits_created", "scopes_created", "scopes_closed")}
        row["policy_shutdown"].update(active_count=0, errors=[])
    for position in range(20):
        peer, index = gate.PEERS[position//10], position % 10
        original = template["cases"][index//2]
        source = copy.deepcopy(original["python" if index % 2 else "blueprint"])
        common = dict(position=position, target=peer, index=index, profile="Python" if index % 2 else "BlueprintFallback")
        server["cases"].append(dict(source, **common, name=original["name"], other_owner_unchanged=True, health_after=0,
            source_observer_kind="native_wait_gameplay_event_on_death", source_delivery_owner_active=[True]))
        for report in clients.values():
            report["cases"].append(dict(common, old_pawn=source["old_pawn"], native_health_zero_seen=True, native_respawn_seen=True,
                respawn_delay_restored=True,
                cues=[copy.deepcopy(source["cue"])], owner_activation_observed=True, death_camera_matched=True,
                native_type_preserved=True, native_cancelable=False, owner_event=copy.deepcopy(source["source_event"])))
    return server, clients


class DeathNetworkGate(unittest.TestCase):
    def test_complete_two_owner_two_viewer_matrix(self):
        self.assertEqual(gate.validate_reports(*reports())["authority_trials"], 20)

    def test_reject_missing_foreign_viewer_or_duplicate_cue(self):
        for amount in (0, 2):
            server, clients = reports(); clients["B0"]["cases"][0]["cues"] *= amount
            with self.subTest(amount=amount), self.assertRaises(RuntimeError): gate.validate_reports(server, clients)

    def test_reject_skipped_authority_damage_and_owner_activation(self):
        for field in ("native_health_zero_seen", "owner_activation_observed", "death_camera_matched", "native_type_preserved"):
            server, clients = reports(); clients["A"]["cases"][0][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate_reports(server, clients)
        server, clients = reports(); server["cases"][0]["other_owner_unchanged"] = False
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)

    def test_reject_wrong_run_and_early_server_exit(self):
        server, clients = reports(); clients["A"]["run_id"] = "foreign"
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)
        server, clients = reports(); server["server_waited_for_client_process_exit"] = False
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)

    def test_reject_missing_native_timer_or_cleanup(self):
        server, clients = reports(); server["cases"][2]["native_elapsed"] = .2
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)
        server, clients = reports(); clients["B0"]["policy_shutdown"]["active_count"] = 1
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)

    def test_reject_native_payload_loss_and_callback_replay(self):
        server, clients = reports(); clients["A"]["cases"][0]["cues"][0]["context"] = {}
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)
        server, clients = reports(); clients["B0"]["callback_replay"] = True
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)
