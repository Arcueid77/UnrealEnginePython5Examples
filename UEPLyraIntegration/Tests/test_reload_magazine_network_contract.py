"""Reload two-owner report models, not in-engine prediction/replication proof."""
import copy
import unittest
from test_reload_magazine_contract import report as owner_report
from uep_lyra_abilities import reload_magazine_network_contract as gate


def reports():
    server = dict(status="passed", error=None, run_id="fixture", cases=[], original_player_states_restored=True,
        server_waited_for_client_process_exit=True, native_playing_gate=dict(native_playing_phase=True), fixture_authority_inventory_setup=True,
        player_ids={"A": 250, "B0": 251}, policy_shutdown=dict(active_count=0, scopes_created=14, scopes_closed=14, errors=[]))
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "native_rpc_bypassed", "inventory_properties_written", "gameplay_event_replication_tested", "network_pause_tested", "ability_activation_called_by_probe"): server[field] = False
    result = dict(server=server)
    for peer in gate.PEERS:
        owner = owner_report(); owner["cases"].pop()
        owner.update(peer=peer, run_id="fixture", player_id=server["player_ids"][peer], native_net_mode="Client")
        for field in ("local_inventory_written", "native_rpc_bypassed", "gameplay_event_replication_tested", "packet_loss_tested", "travel_rejoin_tested", "network_pause_tested"): owner[field] = False
        result[peer] = owner
        for index in range(len(gate.PLAN)*2):
            name = gate.PLAN[index//2]; refused = name in gate.REFUSED
            row = owner["cases"][index//2]["python" if index % 2 else "blueprint"]
            row["native_inventory_model"] = dict(magazine=row["final_ammo"][0], spare=row["final_ammo"][2], equipment="original-pistol")
            row["counters"]["authority_reloads"] = 0
            counts = copy.deepcopy(row["counters"])
            counts.update(client_events=0, fallback_activations=int(not refused), fallback_native_ends=int(not refused),
                fallback_reloads=int(not refused and name not in gate.EARLY))
            if index % 2: counts.update(native_ends=int(not refused), authority_reloads=int(not refused and name not in gate.EARLY))
            else: counts["activations"] = 0
            server["cases"].append(dict(target=peer, index=index, name=name, authoritative_role=3, foreign_owner_unchanged=True,
                authority_original_restored=True, native_ability_inactive=True, authority_tasks_after=0, authority_no_firing_after_end=False,
                authority_final_ammo=copy.deepcopy(row["final_ammo"]), initial_ammo=copy.deepcopy(row["initial_ammo"]),
                authority_inventory_model=copy.deepcopy(row["native_inventory_model"]), authority_counters=counts,
                authority_active_observed=not refused, authority_tasks_observed=0 if refused else 2,
                authority_montage_playing_observed=not refused, authority_expected_no_firing_observed=not refused, held_barrier_published=not refused,
                client=dict(run_id="fixture", peer=peer, index=index, row={key: copy.deepcopy(value) for key, value in row.items() if key != "fixture_ammo_restored"})))
    return result


def family_reports(weapon):
    result = reports(); server = result["server"]
    server.update(weapon=weapon, equipped_fixture_states_restored=True, temporary_weapons_removed=True,
        native_weapon_fixtures={peer: dict(weapon=weapon) for peer in gate.PEERS}, native_equipped_autoreload_grants={peer: int(weapon != "netshooter") for peer in gate.PEERS})
    from uep_lyra_abilities.reload_magazine_contract import WEAPONS
    for peer in gate.PEERS:
        owner = result[peer]
        owner.update(weapon=weapon, native_reload_class=WEAPONS[weapon][0], equipped_fixture_state_restored=True,
            temporary_weapon_removed=True, native_weapon_fixture=dict(weapon=weapon), native_equipped_autoreload_grant_count=int(weapon != "netshooter"))
        for pair in owner["cases"]:
            for side in ("blueprint", "python"): pair[side]["native_class"] = WEAPONS[weapon][0]
    for row in server["cases"]:
        owner = result[row["target"]]["cases"][row["index"]//2]["python" if row["index"] % 2 else "blueprint"]
        row["client"]["row"] = {key: copy.deepcopy(value) for key, value in owner.items() if key != "fixture_ammo_restored"}
    return result


class ReloadMagazineNetworkGate(unittest.TestCase):
    def test_actual_weapon_family_matrices(self):
        for weapon in ("rifle", "shotgun", "netshooter"):
            self.assertEqual(gate.validate(family_reports(weapon))["native_authority_trials"], 36)

    def test_reject_unremoved_temporary_weapon_and_cross_family(self):
        value = family_reports("rifle"); value["server"]["temporary_weapons_removed"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = family_reports("rifle"); value["A"]["weapon"] = "shotgun"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_equipped_fixture_restored_but_original_pistol_not_restored(self):
        value = family_reports("shotgun"); value["B0"]["temporary_weapon_removed"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_prototype_invented_autoreload_grant(self):
        value = family_reports("netshooter"); value["A"]["native_equipped_autoreload_grant_count"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)
    def test_complete_matrix(self): self.assertEqual(gate.validate(reports())["native_authority_trials"], 36)

    def test_reject_local_ammo_write_and_rpc_bypass(self):
        for field in ("local_inventory_written", "native_rpc_bypassed", "network_pause_tested"):
            value = reports(); value["A"][field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_authority_task_montage_and_foreign_owner_isolation(self):
        for field, bad in (("authority_tasks_observed", 0), ("authority_montage_playing_observed", False), ("foreign_owner_unchanged", False)):
            value = reports(); value["server"]["cases"][0][field] = bad
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_forged_ack_or_unreplicated_authority_ammo(self):
        value = reports(); value["server"]["cases"][0]["client"]["row"]["input_injections"] = 2
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["cases"][0]["authority_final_ammo"][0] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_client_refusal_activating_server_and_original_bp_bypassed(self):
        value = reports(); value["server"]["cases"][4]["authority_active_observed"] = True
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["cases"][0]["authority_counters"]["fallback_reloads"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_matrix_restore_and_server_first_exit(self):
        value = reports(); value["server"]["cases"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)
        for field in ("original_player_states_restored", "server_waited_for_client_process_exit"):
            value = reports(); value["server"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
