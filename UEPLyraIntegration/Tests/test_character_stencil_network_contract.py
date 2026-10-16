"""Three-world direct/nested stencil calls with actual native role boundaries."""
import ast
from pathlib import Path
import time
import types
import unittest
from test_character_stencil_contract import report as local
from uep_lyra_characters import stencil_network_contract as gate
from uep_lyra_hud.startup import validation_module


def reports():
    values = {peer: dict(local(peer != "server"), peer=peer, run_id="test", network_acceptance=True, network_software_only=True,
        gameplay_state_delivered_by_files=False, player_id=2 if peer == "B0" else 1, native_role=3 if peer == "server" else 2,
        native_net_mode="DedicatedServer" if peer == "server" else "Client", native_owner_local_control=peer != "server",
        team_change_replication_claimed=False, material_replication_claimed=False, stencil_replication_claimed=False)
        for peer in ("server", "A", "B0")}
    values["server"].update(native_playing_gate=dict(native_playing_phase=True), server_waited_for_client_process_exit=True,
        all_local_checks_complete_before_release=True, cleanup_frozen_before_release=True, player_ids=dict(A=1, B0=2))
    return values


class CharacterStencilNetworkModels(unittest.TestCase):
    def test_three_worlds_120_trials_156_calls_and_72_native_gc_calls(self):
        result = gate.validate(reports()); self.assertEqual((result["native_case_trials"], result["native_bp_invocations"], result["native_gc_calls"]), (120, 156, 72))

    def test_missing_client_and_incomplete_direct_matrix_fail(self):
        for mutate in (lambda v: v.pop("B0"), lambda v: v["A"]["stencil_cases"].pop()):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_client_owner_native_role_and_control_not_faked(self):
        for mutate in (lambda v: v["A"].update(native_role=3), lambda v: v["A"]["stencil_cases"][0].update(locally_controlled=False)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_nonlocal_server_does_not_use_local_player_zero_rule(self):
        value = reports(); value["server"]["stencil_cases"][2]["components"][0]["value"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_child_lifetime_and_caller_roots_required_in_every_world(self):
        for fields in (dict(native_child_actor_created_destroyed=False), dict(stencil_caller_roots_released=0)):
            value = reports(); value["B0"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_cleanup_and_real_client_exits_precede_server_shutdown(self):
        for fields in (dict(cleanup_frozen_before_release=False), dict(server_waited_for_client_process_exit=False)):
            value = reports(); value["server"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_pixels_replication_and_entire_parent_family_remain_unclaimed(self):
        for fields in (dict(stencil_replication_claimed=True), dict(pixels_verified=True), dict(whole_parent_class_family_migrated=True)):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_post_release_server_only_reads_pod_exit_records_not_native_actors(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/stencil_network_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Server")
        namespace = dict(Peer=object, time=time, PEERS=("A", "B0"), require=gate.require, traceback=types.SimpleNamespace(format_exc=lambda: "unexpected native access"))
        namespace["token"] = lambda root, name, run: dict(exit_code=0)
        namespace["Native"] = types.SimpleNamespace(tick=lambda *args: (_ for _ in ()).throw(RuntimeError("destroyed native Actor")))
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        server = namespace["Server"].__new__(namespace["Server"]); exits = []
        server.finished, server.complete, server.released, server.started = False, True, True, time.monotonic()
        server.root, server.run, server.report = "root", "run", {}
        server.exit_native = lambda error=None: exits.append(error); server.status = lambda: None
        server.tick(.1); self.assertEqual(exits, [None]); self.assertTrue(server.report["server_waited_for_client_process_exit"])

    def test_network_validation_selector_is_explicit_and_no_commandlet_side_effect(self):
        self.assertEqual(validation_module(["-UEPCharacterStencilNetworkResult=x"]), "uep_lyra_characters.stencil_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterStencilNetworkResult=x"]))
