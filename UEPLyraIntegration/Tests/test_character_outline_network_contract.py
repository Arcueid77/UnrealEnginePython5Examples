"""Three real native software worlds cannot certify replicated/visible outlines."""
import copy
import unittest
from test_character_outline_contract import report as local
from uep_lyra_characters import outline_network_contract as gate
from uep_lyra_hud.startup import validation_module


def reports():
    values = {peer: dict(local(peer != "server"), peer=peer, run_id="test", network_acceptance=True, network_software_only=True,
        gameplay_state_delivered_by_files=False, fixture_actor_replication_disabled=True, player_id=2 if peer == "B0" else 1,
        native_role=3 if peer == "server" else 2, native_net_mode="DedicatedServer" if peer == "server" else "Client")
        for peer in ("server", "A", "B0")}
    values["server"].update(native_playing_gate=dict(native_playing_phase=True), server_waited_for_client_process_exit=True,
        all_local_checks_complete_before_release=True, cleanup_frozen_before_release=True, player_ids=dict(A=1, B0=2))
    return values


class CharacterOutlineNetworkModels(unittest.TestCase):
    def test_three_worlds_48_trials_54_real_bp_invocations(self):
        result = gate.validate(reports()); self.assertEqual((result["native_case_trials"], result["native_bp_invocations"]), (48, 54))

    def test_missing_peer_and_local_gate_failure_rejected(self):
        for mutate in (lambda v: v.pop("B0"), lambda v: v["A"]["cases"].pop(), lambda v: v["server"].update(fixture_probe_class_roots_released=0)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_real_native_owner_ids_roles_modes_and_local_control_required(self):
        for fields in (dict(native_role=3), dict(player_id=2), dict(native_net_mode="Standalone"), dict(native_owner_local_control=False), dict(run_id="other")):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_server_is_not_faked_as_a_local_rendered_player(self):
        value = reports(); value["server"] = dict(local(True), **{key: value["server"][key] for key in value["server"] if key not in local(True)})
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_playing_cleanup_and_actual_client_exits_required(self):
        for fields in (dict(native_playing_gate=dict(native_playing_phase=False)), dict(server_waited_for_client_process_exit=False),
            dict(all_local_checks_complete_before_release=False), dict(cleanup_frozen_before_release=False)):
            value = reports(); value["server"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_owned_fixture_actor_does_not_replicate_and_files_do_not_deliver_material_state(self):
        for fields in (dict(fixture_actor_replication_disabled=False), dict(gameplay_state_delivered_by_files=True), dict(network_software_only=False)):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_material_replication_pixels_and_production_roots_remain_unclaimed(self):
        for fields in (dict(material_replication_claimed=True), dict(pixels_verified=True), dict(production_roots_objects=True)):
            value = reports(); value["B0"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_network_startup_is_explicit_and_commandlet_stays_disabled(self):
        self.assertEqual(validation_module(["-UEPCharacterOutlineNetworkResult=x"]), "uep_lyra_characters.outline_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterOutlineNetworkResult=x"]))
