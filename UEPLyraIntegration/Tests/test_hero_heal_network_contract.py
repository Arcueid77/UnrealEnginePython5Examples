"""Reject native authority/owner divergence; modeled reports only."""
import copy
import unittest
from test_hero_heal_contract import report as owner_report
from uep_lyra_abilities import hero_heal_network_contract as gate


def reports():
    server = dict(status="passed", error=None, peer="server", run_id="fixture", cases=[],
        original_player_states_restored=True, original_ability_specs_restored=True,
        server_waited_for_client_process_exit=True, native_playing_gate=dict(native_playing_phase=True),
        fixture_authority_grant_and_health=True, authority_input_baseline_fixture=True,
        native_input_locks_suspended={"A": 1, "B0": 1}, native_input_locks_restored={"A": 1, "B0": 1}, player_ids={"A": 250, "B0": 251},
        policy_shutdown=dict(active_count=0, scopes_created=14, scopes_closed=14, errors=[]))
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "health_properties_written", "native_rpc_bypassed", "activation_handler_replayed", "task_callbacks_replayed", "animation_assets_modified",
        "original_montage_or_effect_written", "gameplay_event_replication_tested"): server[field] = False
    result = dict(server=server)
    for peer in gate.PEERS:
        owner = owner_report(); owner["cases"].pop()
        owner.update(peer=peer, run_id="fixture", player_id=server["player_ids"][peer])
        for field in ("local_health_written", "local_ability_granted", "native_rpc_bypassed", "gameplay_event_replication_tested", "packet_loss_tested", "travel_rejoin_tested"): owner[field] = False
        result[peer] = owner
        for index in range(len(gate.NETWORK_PLAN)*2):
            row = owner["cases"][index//2]["python" if index % 2 else "blueprint"]
            row["authority_health_confirmed"] = True
            ack = {key: copy.deepcopy(value) for key, value in row.items() if key != "fixture_health_restored"}
            server["cases"].append(dict(target=peer, index=index, name=gate.NETWORK_PLAN[index//2],
                profile=("BlueprintFallback", "Python")[index % 2], authoritative_role=3, native_active_observed=True,
                native_effect_observed=True, native_movement_lock_observed=True, native_task_triple_observed=True, native_first_heal_observed=True,
                foreign_owner_unchanged=True, authority_movement_baseline_restored=True, authority_original_restored=True,
                authority_effects_after=0, authority_tasks_after=0, authority_health=row["health_after"],
                authority_counters=copy.deepcopy(row["counters"]), client=dict(run_id="fixture", peer=peer, index=index, row=ack)))
    return result


class HeroHealNetworkGate(unittest.TestCase):
    def test_complete_native_matrix(self): self.assertEqual(gate.validate(reports())["native_authority_trials"], 28)

    def test_local_state_does_not_imply_immediate_authority_effect_removal(self):
        value = reports()
        for peer in gate.PEERS:
            for side in ("blueprint", "python"):
                value[peer]["cases"][6][side]["native_state_end_released_effects_while_active"] = False
            for row in value["server"]["cases"]:
                if row["target"] == peer and row["name"] == "native-state-end": row["client"]["row"]["native_state_end_released_effects_while_active"] = False
        self.assertEqual(gate.validate(value)["native_authority_trials"], 28)
        value["A"]["cases"][6]["python"]["native_state_end_released_movement_while_active"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_native_authority_active_effect_input_or_tasks(self):
        for field in ("native_active_observed", "native_effect_observed", "native_movement_lock_observed", "native_task_triple_observed", "foreign_owner_unchanged"):
            value = reports(); value["server"]["cases"][0][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_authority_health_divergence_and_native_leak(self):
        for field, replacement in (("authority_health", 99.), ("authority_effects_after", 1), ("authority_tasks_after", 1)):
            value = reports(); value["server"]["cases"][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_client_health_write_grant_and_rpc_bypass(self):
        for field in ("local_health_written", "local_ability_granted", "native_rpc_bypassed"):
            value = reports(); value["A"][field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_matrix_unrestored_specs_and_host_first(self):
        value = reports(); value["server"]["cases"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)
        for field in ("original_ability_specs_restored", "server_waited_for_client_process_exit"):
            value = reports(); value["server"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_authority_policy_scope_leak_or_forged_ack(self):
        value = reports(); value["server"]["cases"][1]["authority_counters"]["scopes_closed"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["native_input_locks_restored"]["A"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["cases"][0]["client"]["row"]["health_after"] = 99.
        with self.assertRaises(RuntimeError): gate.validate(value)
