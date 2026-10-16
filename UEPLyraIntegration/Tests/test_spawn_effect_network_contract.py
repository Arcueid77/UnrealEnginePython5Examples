"""ServerInitiated spawn report models and passive-client source regressions."""
import ast
import copy
from pathlib import Path
import unittest
from uep_lyra_abilities import spawn_effect_network_contract as gate
from uep_lyra_hud.startup import validation_module
from test_spawn_effect_contract import report as standalone_report


def reports():
    source = standalone_report(); cases = {row["name"]: row for row in source["cases"]}
    result = {}
    for peer in ("server",)+gate.PEERS:
        value = copy.deepcopy(source)
        value.update(peer=peer, run_id="native-run", cases=[], foreign_cases=[], native_policy=[2, 1, 2], native_rpc_bypassed=False,
            gameplay_state_delivered_by_files=False, packet_loss_tested=False, travel_rejoin_tested=False, physical_input_tested=False,
            local_ability_activation_called=False)
        result[peer] = value
    server = result["server"]
    server.update(player_ids=dict(A=256, B0=257), server_waited_for_client_process_exit=True,
        native_playing_gate=dict(native_playing_phase=True), native_input_locks_suspended=dict(A=2, B0=3),
        native_input_locks_restored=dict(A=2, B0=3), fixture_authority_native_activation=True, native_initials={})
    position = 0
    for peer in gate.PEERS:
        result[peer]["player_id"] = server["player_ids"][peer]
        server["native_initials"][peer] = dict(default_python_on_spawn=True, native_role=3, player_id=server["player_ids"][peer])
        for index, (name, profile) in enumerate((name, profile) for name in gate.NETWORK_PLAN for profile in ("BlueprintFallback", "Python")):
            row = copy.deepcopy(cases[name]["python"])
            row.update(position=position, index=index, name=name, profile=profile, target=peer, native_role=3,
                native_source_avatar_matches=True, health_unchanged=True, other_owner_unchanged=True,
                actual_owner_rpc_start_observed=True, local_ability_activation_called=False)
            if profile == "BlueprintFallback":
                row["counters"] = dict(activations=0, tasks_created=0, scopes_created=0, fallback_activations=1,
                    fallback_native_ends=int(name != "active-profile-switch"))
            server["cases"].append(copy.deepcopy(row))
            row["native_role"] = 2; row["profile_teardown_ended_ability"] = False
            if profile == "Python": row["counters"]["native_ends"] = 1
            else: row["counters"]["fallback_native_ends"] = 1
            result[peer]["cases"].append(row)
            other = gate.PEERS[1] if peer == gate.PEERS[0] else gate.PEERS[0]
            result[other]["foreign_cases"].append(dict(position=position, original_state_unchanged=True))
            position += 1
    return result


class SpawnEffectNetworkGate(unittest.TestCase):
    def test_complete_two_owner_matrix(self): self.assertEqual(gate.validate(reports())["native_authority_trials"], 28)

    def test_only_explicit_network_lane_starts(self):
        self.assertEqual(validation_module(["-UEPSpawnEffectNetworkResult=report.json"]), "uep_lyra_abilities.spawn_effect_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPSpawnEffectNetworkResult=report.json"]))

    def test_reject_direct_client_activation_wrong_role_and_unreplicated_cleanup(self):
        for field, replacement in (("local_ability_activation_called", True), ("native_role", 3), ("effects_after_end", 1)):
            value = reports(); value["A"]["cases"][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_false_source_and_unobserved_native_owner_start(self):
        for field in ("native_source_avatar_matches", "actual_owner_rpc_start_observed"):
            value = reports(); value["server"]["cases"][0][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_consumed_foreign_lock_and_changed_foreign_owner(self):
        value = reports(); row = next(row for row in value["A"]["cases"] if row["name"] == "foreign-input-lock")
        row["movement_after_end"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["B0"]["foreign_cases"][0]["original_state_unchanged"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_wrong_rpc_end_route_and_authority_input_stack_restore(self):
        value = reports(); row = next(row for row in value["A"]["cases"] if row["name"] == "active-profile-switch" and row["profile"] == "Python")
        row["counters"]["native_ends"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["native_input_locks_restored"]["A"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_client_source_never_calls_native_activation_or_replays_event(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/spawn_effect_network_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8"))
        client = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Client")
        strings = {node.value for node in ast.walk(client) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        self.assertNotIn("TryActivateAbilityByClass", strings); self.assertNotIn("K2_ActivateAbility", strings)
        function = next(node for node in client.body if isinstance(node, ast.FunctionDef) and node.name == "may_capture_end")
        namespace = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(file), "exec"), namespace)
        class NativeState:
            def effects(self): return 1
            def tasks(self): return 0
            def immune(self): return False
        state = NativeState(); self.assertFalse(namespace["may_capture_end"](state))
        state.effects = lambda: 0; self.assertTrue(namespace["may_capture_end"](state))
