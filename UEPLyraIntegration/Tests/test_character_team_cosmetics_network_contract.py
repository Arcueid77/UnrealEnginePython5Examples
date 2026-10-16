"""Actual local/native device boundaries and shutdown, not file replication."""
import ast
from pathlib import Path
import time
import types
import unittest
from test_character_team_cosmetics_contract import report as local
from uep_lyra_characters import team_cosmetics_network_contract as gate
from uep_lyra_hud.startup import validation_module


def reports():
    values = {peer: dict(local(peer != "server"), peer=peer, run_id="test", network_acceptance=True, network_software_only=True,
        gameplay_state_delivered_by_files=False, fixture_actor_replication_disabled=True, player_id=2 if peer == "B0" else 1,
        native_role=3 if peer == "server" else 2, native_net_mode="DedicatedServer" if peer == "server" else "Client",
        native_owner_local_control=peer != "server", team_change_replication_claimed=False, material_replication_claimed=False)
        for peer in ("server", "A", "B0")}
    values["server"].update(native_playing_gate=dict(native_playing_phase=True), server_waited_for_client_process_exit=True,
        all_local_checks_complete_before_release=True, cleanup_frozen_before_release=True, player_ids=dict(A=1, B0=2))
    return values


class CharacterTeamNetworkModels(unittest.TestCase):
    def test_three_actual_worlds_48_trials_60_bp_calls_and_32_scheduled_properties(self):
        result = gate.validate(reports())
        self.assertEqual((result["native_case_trials"], result["native_bp_invocations"], result["native_device_scheduler_properties"]), (48, 60, 32))

    def test_missing_world_and_failed_local_software_cleanup_rejected(self):
        for mutate in (lambda v: v.pop("B0"), lambda v: v["A"]["cases"].pop(), lambda v: v["A"].update(device_roots_released=0)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_owner_ids_roles_netmode_run_and_control_required(self):
        for fields in (dict(native_role=3), dict(player_id=2), dict(native_net_mode="Standalone"), dict(native_owner_local_control=False), dict(run_id="other")):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["native_device_subsystem_available"] = True
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_server_and_unpossessed_have_no_fake_local_platform_user(self):
        for peer, index in (("server", 0), ("A", 12)):
            value = reports(); value[peer]["cases"][index]["platform_user_valid"] = True
            with self.subTest(peer=peer), self.assertRaises(RuntimeError): gate.validate(value)

    def test_actual_playing_cleanup_freeze_and_client_process_exits_required(self):
        for fields in (dict(native_playing_gate=dict(native_playing_phase=False)), dict(server_waited_for_client_process_exit=False),
                dict(all_local_checks_complete_before_release=False), dict(cleanup_frozen_before_release=False)):
            value = reports(); value["server"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_files_do_not_replicate_team_material_or_fixture_actor(self):
        for fields in (dict(fixture_actor_replication_disabled=False), dict(gameplay_state_delivered_by_files=True),
                dict(team_change_replication_claimed=True), dict(material_replication_claimed=True), dict(network_software_only=False)):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_hardware_and_pixels_remain_unverified(self):
        for key in ("hardware_output_tested", "pixels_verified", "full_acceptance"):
            value = reports(); value["A"][key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_one_way_server_release_does_not_read_native_objects_again(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/team_cosmetics_network_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Server")
        namespace = dict(Peer=object, time=time, PEERS=("A", "B0"), require=gate.require, traceback=types.SimpleNamespace(format_exc=lambda: "unexpected native access"))
        namespace["token"] = lambda root, name, run: dict(exit_code=0)
        namespace["Native"] = types.SimpleNamespace(tick=lambda *args: (_ for _ in ()).throw(RuntimeError("native object was already destroyed")))
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        server = namespace["Server"].__new__(namespace["Server"])
        server.finished, server.complete, server.released, server.started = False, True, True, time.monotonic()
        server.root, server.run, server.report = "root", "run", {}; exits = []
        server.exit_native = lambda error=None: exits.append(error); server.status = lambda: None
        server.tick(.1); self.assertEqual(exits, [None]); self.assertTrue(server.report["server_waited_for_client_process_exit"])

    def test_explicit_network_selector_never_runs_in_authoring_commandlet(self):
        self.assertEqual(validation_module(["-UEPCharacterTeamNetworkResult=x"]), "uep_lyra_characters.team_cosmetics_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterTeamNetworkResult=x"]))
