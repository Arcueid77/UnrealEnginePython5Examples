"""Independent owner/authority/restore checks cannot be replaced with local data."""
import ast
import copy
from pathlib import Path
import types
import unittest
from test_character_initial_inventory_contract import report as local, grant
from uep_lyra_characters import initial_inventory_network_contract as gate
from uep_lyra_hud.startup import validation_module


def reports():
    values, rows = {}, []
    for number, peer in enumerate(("A", "B0")):
        owner_rows = []
        for index, row in enumerate(local()["cases"]):
            python = row["profile"] == "Python"
            owner = dict(index=index, name=row["name"], profile=row["profile"], replica_model=copy.deepcopy(row["native_model"]),
                native_role=2, native_authority=False, bp_reference_call=True, native_inventory_before_after_unchanged=True,
                original_item_retained=True, added_definitions=sorted(row["configured_definitions"]), profile_configuration_cdo_restored=True,
                counters=dict(python_calls=int(python), fallback_calls=int(not python), authority_noops=int(python), grant_calls=0,
                    slot_add_attempts=0, slot_zero_requests=0, missing_controller_noops=0, missing_inventory_noops=0, missing_quickbar_noops=0))
            owner_rows.append(owner)
            rows.append(dict(copy.deepcopy(row), peer=peer, index=index, authority_role=3, other_authority_owner_unchanged=True,
                owner_observation=copy.deepcopy(owner)))
        startup = dict(python_calls=1, fallback_calls=0, grant_calls=0, authority_noops=1, last_call=dict(authority=False, role=2))
        values[peer] = dict(status="passed", cases=owner_rows, peer=peer, run_id="test", player_id=number+1, native_net_mode="Client",
            native_role=2, authority_phase_gate_observed=True, original_inventory_identities_restored=True, profile_configuration_cdo_restored=True,
            foreign_turn_own_inventory_unchanged=True, inventory_observers=dict(created=1, closed=1, active=0), native_inventory_signals=["native"],
            signal_payload_owner_claimed=False, local_inventory_written=False, gameplay_state_delivered_by_files=False, whole_character_migrated=False,
            natural_remote_startup=startup, network_acceptance=True, full_acceptance=False)
    values["server"] = dict(status="passed", run_id="test", player_ids=dict(A=1, B0=2), cases=rows,
        natural_startup_grants={peer: grant() for peer in ("A", "B0")}, native_playing_gate=dict(native_playing_phase=True),
        server_waited_for_client_process_exit=True, all_original_inventory_identities_restored=True,
        gameplay_state_delivered_by_files=False, inventory_properties_written=False, whole_character_migrated=False,
        restore_frozen_before_release=True, full_acceptance=False)
    return values


class CharacterLoadoutNetworkModels(unittest.TestCase):
    def test_24_native_authority_and_owner_replica_remote_noop_trials(self): self.assertEqual(gate.validate(reports())["native_authority_trials"], 24)

    def test_missing_peer_or_case_cannot_pass(self):
        for mutate in (lambda v: v.pop("B0"), lambda v: v["server"]["cases"].pop(), lambda v: v["A"]["cases"].pop()):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_identical_but_wrong_replica_and_authority_models_rejected(self):
        value = reports(); value["server"]["cases"][2]["native_model"]["items"] = []
        value["server"]["cases"][2]["owner_observation"]["replica_model"]["items"] = []
        value["A"]["cases"][2]["replica_model"]["items"] = []
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_non_authority_calls_must_not_grant_or_modify_inventory(self):
        for mutate in (lambda r: r.update(native_authority=True), lambda r: r.update(native_inventory_before_after_unchanged=False),
            lambda r: r["counters"].update(grant_calls=1), lambda r: r["counters"].update(authority_noops=0)):
            value = reports(); mutate(value["A"]["cases"][1])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_authority_role_foreign_owner_and_server_last_exit_required(self):
        for fields in (dict(authority_role=2), dict(other_authority_owner_unchanged=False)):
            value = reports(); value["server"]["cases"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        for fields in (dict(server_waited_for_client_process_exit=False), dict(all_original_inventory_identities_restored=False)):
            value = reports(); value["server"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_owning_client_context_scope_and_original_identities_required(self):
        for fields in (dict(native_net_mode="Standalone"), dict(native_role=3), dict(player_id=2), dict(original_inventory_identities_restored=False),
            dict(inventory_observers=dict(created=1, closed=0, active=1)), dict(native_inventory_signals=[])):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_client_startup_observation_does_not_invent_natural_entry_or_allow_any_grant(self):
        value = reports(); value["A"]["natural_remote_startup"] = dict(python_calls=0, fallback_calls=0, grant_calls=0, authority_noops=0, last_call=None)
        gate.validate(value)
        value["A"]["natural_remote_startup"]["grant_calls"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_rpc_data_files_local_inventory_write_and_payload_owner_overclaims_rejected(self):
        for fields in (dict(local_inventory_written=True), dict(gameplay_state_delivered_by_files=True), dict(signal_payload_owner_claimed=True), dict(whole_character_migrated=True)):
            value = reports(); value["A"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_network_selection_explicit_and_disabled_for_commandlet(self):
        self.assertEqual(validation_module(["-UEPCharacterLoadoutNetworkResult=x"]), "uep_lyra_characters.initial_inventory_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterLoadoutNetworkResult=x"]))

    def test_original_state_is_frozen_before_release_not_after_native_disconnect(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/initial_inventory_network_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Server")
        published, reads, finished = [], [], []
        def native_read(controller):
            if published: raise AssertionError("native owner has already disconnected")
            reads.append(controller); return "original"
        namespace = dict(fingerprint=native_read, state=native_read, require=gate.require, PEERS=("A", "B0"),
            atomic_write=lambda *args: published.append(args), token=lambda *args: dict(exit_code=0) if len(reads) == 4 and len(published) == 2 else None)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        server = namespace["Server"].__new__(namespace["Server"])
        server.release_started, server.root, server.run, server.report = False, Path("fixture"), "test", {}
        server.trials = {peer: types.SimpleNamespace(controller=peer, original="original", original_model="original") for peer in ("A", "B0")}
        server.finish = lambda: finished.append(True)
        server.release_clients(); self.assertEqual(len(reads), 4); self.assertEqual(len(published), 1)
        # Simulate clients disappearing immediately after the release file.
        published.append("disconnected"); server.release_clients()
        self.assertEqual(len(reads), 4); self.assertEqual(finished, [True]); self.assertIs(server.report["restore_frozen_before_release"], True)

    def test_post_disconnect_restore_and_full_version_overclaims_rejected(self):
        for fields in (dict(restore_frozen_before_release=False), dict(full_acceptance=True)):
            value = reports(); value["server"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
