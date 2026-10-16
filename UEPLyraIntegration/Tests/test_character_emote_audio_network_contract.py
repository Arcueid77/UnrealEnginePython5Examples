"""Three-world local cosmetic Interface evidence cannot claim replication."""
import copy
import unittest
from test_character_emote_audio_contract import report as local_report
from uep_lyra_characters import emote_audio_network_contract as gate
from uep_lyra_hud.startup import validation_module


def reports():
    values = {}
    for peer in ("server", "A", "B0"):
        values[peer] = dict(local_report(), peer=peer, run_id="test", network_acceptance=True, network_software_only=True,
            audio_property_replication_claimed=False, gameplay_state_delivered_by_files=False,
            primary_player_id=2 if peer == "B0" else 1, secondary_player_id=1 if peer == "B0" else 2,
            primary_role=3 if peer == "server" else 2, secondary_role=3 if peer == "server" else 1,
            native_net_mode="DedicatedServer" if peer == "server" else "Client", authority_phase_gate_observed=peer != "server")
    values["server"].update(server_waited_for_client_process_exit=True, all_local_checks_complete_before_release=True,
        native_playing_gate=dict(native_playing_phase=True), player_ids=dict(A=1, B0=2))
    return values


class CharacterAudioNetworkModels(unittest.TestCase):
    def test_three_world_bounded_shape(self): self.assertEqual(gate.validate(reports())["roundtrip_cases"], 36)

    def test_two_actual_clients_and_three_complete_local_gates_required(self):
        for mutate in (lambda v: v.pop("B0"), lambda v: v["A"]["cases"].pop(), lambda v: v["server"]["native_gc"].update(both_components_valid=False)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_real_owner_foreign_replica_ids_and_roles_are_not_interchangeable(self):
        for fields in (dict(primary_player_id=2), dict(secondary_player_id=1), dict(primary_role=3), dict(secondary_role=2)):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_local_property_calls_cannot_be_claimed_as_replicated_payloads(self):
        for fields in (dict(audio_property_replication_claimed=True), dict(gameplay_state_delivered_by_files=True), dict(network_software_only=False)):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_real_exit_and_native_playing_barriers_required(self):
        for fields in (dict(server_waited_for_client_process_exit=False), dict(all_local_checks_complete_before_release=False),
            dict(native_playing_gate=dict(native_playing_phase=False))):
            value = reports(); value["server"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_peer_run_and_native_client_context_must_match(self):
        for fields in (dict(peer="B0"), dict(run_id="other"), dict(native_net_mode="Standalone"), dict(authority_phase_gate_observed=False)):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_network_startup_is_explicit_and_does_not_enable_commandlet_probes(self):
        self.assertEqual(validation_module(["-UEPCharacterAudioNetworkResult=x"]), "uep_lyra_characters.emote_audio_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterAudioNetworkResult=x"]))
