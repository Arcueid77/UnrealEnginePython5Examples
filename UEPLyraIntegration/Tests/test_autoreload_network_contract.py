"""Modeled report gate tests; these are not native network evidence."""
import copy
import unittest
from test_autoreload_contract import report as owner_report, family_report
from uep_lyra_abilities import autoreload_network_contract as gate


def reports():
    server = dict(status="passed", error=None, peer="server", run_id="fixture", cases=[],
        original_inventory_restored=True, server_waited_for_client_process_exit=True,
        native_playing_gate=dict(native_playing_phase=True), fixture_authority_inventory_setup=True,
        player_ids={"A": 250, "B0": 251}, policy_shutdown=dict(active_count=0, scopes_created=0, scopes_closed=0, errors=[]))
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "inventory_properties_written", "local_only_authority_activation_called", "native_rpc_bypassed", "gameplay_event_replication_tested"): server[field] = False
    result = dict(server=server)
    for peer in gate.PEERS:
        owner = owner_report(); owner.update(peer=peer, run_id="fixture", player_id=server["player_ids"][peer])
        for field in ("local_inventory_written", "gameplay_event_replication_tested", "native_rpc_bypassed", "packet_loss_tested", "travel_rejoin_tested"): owner[field] = False
        result[peer] = owner
        for index in range(len(gate.PLAN)*2):
            name = gate.PLAN[index//2]; row = owner["cases"][index//2]["python" if index % 2 else "blueprint"]
            ack = {key: copy.deepcopy(value) for key, value in row.items() if key != "fixture_ammo_restored"}
            server["cases"].append(dict(target=peer, index=index, name=name, profile=("BlueprintFallback", "Python")[index % 2],
                authoritative_role=3, other_inventory_unchanged=True, local_only_authority_stayed_inactive=True,
                authority_original_restored=True, authority_final_ammo=[row["final_magazine"], row["final_spare"]],
                minimum_magazine=0, native_reload_active_observed=name in ("empty-spare", "real-fire-auto-reload"),
                client=dict(run_id="fixture", peer=peer, index=index, row=ack)))
    return result


def family_reports(weapon="pistol", capacity=12):
    result = reports(); server = result["server"]
    server.update(schema_version=2, weapon=weapon, native_equipped_autoreload_grants={peer: 1 for peer in gate.PEERS})
    if weapon != "pistol":
        server.update(equipped_fixture_states_restored=True, temporary_weapons_removed=True,
            native_weapon_fixtures={peer: dict(weapon=weapon, slot=1, owned_item=peer+"-temporary-item",
                original_model=dict(definition="/Game/Weapons/ID_Pistol")) for peer in gate.PEERS})
    for peer in gate.PEERS:
        owner = result[peer]
        owner.update(family_report(weapon, capacity), equipped_fixture_state_restored=True)
        if weapon != "pistol":
            owner.update(temporary_weapon_removed=True, native_weapon_fixture=dict(original_model=dict(definition="/Game/Weapons/ID_Pistol")))
    for row in server["cases"]:
        owner = result[row["target"]]["cases"][row["index"]//2]["python" if row["index"] % 2 else "blueprint"]
        row.update(initial_ammo=owner["initial_ammo"], authority_ammo_api_calls_after_permit=0,
            authority_final_ammo=[owner["final_magazine"], owner["final_spare"]])
        row["client"]["row"] = {key: copy.deepcopy(value) for key, value in owner.items() if key != "fixture_ammo_restored"}
        reload = int(row["name"] in ("empty-spare", "real-fire-auto-reload"))
        row["authority_reload_counts"] = dict(activations=reload, native_ends=reload, authority_reloads=reload,
            transferred_rounds=capacity*reload, reload_events=reload, tasks_created=2*reload, scopes_created=reload, scopes_closed=reload)
    return result


class AutoReloadNetworkGate(unittest.TestCase):
    def test_complete_two_owner_matrix(self): self.assertEqual(gate.validate(reports())["native_authority_trials"], 24)

    def test_all_original_autoreload_weapon_families(self):
        for weapon, capacity in (("pistol", 12), ("rifle", 30), ("shotgun", 8)):
            with self.subTest(weapon=weapon): self.assertEqual(gate.validate(family_reports(weapon, capacity))["native_authority_trials"], 24)

    def test_predicted_requests_retry_but_authority_reloads_once(self):
        value = family_reports()
        for peer in gate.PEERS:
            pair = value[peer]["cases"][2]
            pair["blueprint"]["reload_event_deliveries"] = 15
            pair["python"]["reload_event_deliveries"] = 18
            pair["python"]["counters"].update(reload_requests=18, polls=22)
        for row in value["server"]["cases"]:
            owner = value[row["target"]]["cases"][row["index"]//2]["python" if row["index"] % 2 else "blueprint"]
            row["client"]["row"] = {key: copy.deepcopy(item) for key, item in owner.items() if key != "fixture_ammo_restored"}
        self.assertEqual(gate.validate(value)["native_authority_trials"], 24)
        value["A"]["cases"][2]["python"]["counters"]["reload_requests"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_duplicate_actual_reload_transfer_and_unclosed_scope(self):
        for key in ("activations", "authority_reloads", "transferred_rounds", "reload_events", "tasks_created", "scopes_closed", "native_ends"):
            value = family_reports(); value["server"]["cases"][4]["authority_reload_counts"][key] += 1
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_family_mismatch_authority_reseed_and_replaced_grant(self):
        for peer, key, replacement in (("A", "weapon", "pistol"), ("server", "native_equipped_autoreload_grants", {"A": 0, "B0": 1})):
            value = family_reports("rifle", 30); value[peer][key] = replacement
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)
        for key, replacement in (("authority_ammo_api_calls_after_permit", 1), ("initial_ammo", [0, 60])):
            value = family_reports("rifle", 30); value["server"]["cases"][6][key] = replacement
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_temporary_native_family_restore_and_foreign_item(self):
        for peer, key in (("A", "temporary_weapon_removed"), ("B0", "equipped_fixture_state_restored"),
            ("server", "equipped_fixture_states_restored"), ("server", "temporary_weapons_removed")):
            value = family_reports("shotgun", 8); value[peer][key] = False
            with self.subTest(peer=peer, key=key), self.assertRaises(RuntimeError): gate.validate(value)
        value = family_reports("rifle", 30); value["server"]["native_weapon_fixtures"]["A"]["weapon"] = "shotgun"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_localonly_authority_activation_and_other_owner_change(self):
        for field in ("local_only_authority_stayed_inactive", "other_inventory_unchanged", "authority_original_restored"):
            value = reports(); value["server"]["cases"][0][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_client_only_reload_and_fake_empty(self):
        for field, replacement in (("native_reload_active_observed", False), ("minimum_magazine", 1)):
            value = reports(); value["server"]["cases"][6][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_divergent_server_ammo_or_ack(self):
        value = reports(); value["server"]["cases"][0]["authority_final_ammo"][0] = 99
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["cases"][0]["client"]["row"]["tasks_after_end"] = 99
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_matrix_identity_and_scope_leak(self):
        value = reports(); value["server"]["cases"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["B0"]["player_id"] = 250
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["policy_shutdown"]["active_count"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_rpc_bypass_local_ammo_write_and_host_first_exit(self):
        for peer, field in (("server", "native_rpc_bypassed"), ("A", "local_inventory_written"), ("server", "gameplay_event_replication_tested")):
            value = reports(); value[peer][field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["server"]["server_waited_for_client_process_exit"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
