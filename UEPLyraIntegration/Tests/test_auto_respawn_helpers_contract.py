"""Synthetic report rejection tests; none are native runtime acceptance."""
import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities.auto_respawn_helpers_contract import PLAN, FALSE_FLAGS, AUTHORITY_PHASES, validate, spec_model


def row(name, profile):
    switched = name == "profile-switch-during-death"
    final = "BlueprintFallback" if switched and profile == "Python" else "Python" if switched else profile
    prefix, end = ("" if profile == "Python" else "fallback_"), ("" if final == "Python" else "fallback_")
    stats = {field: 0 for field in ("player_state_queries", "death_queries", "death_end_calls", "abilities_ended",
        "fallback_player_state_queries", "fallback_death_queries", "fallback_death_end_calls")}
    stats.update({prefix+"player_state_queries": 3, prefix+"death_queries": 3, end+"death_end_calls": 1, "abilities_ended": int(final == "Python")})
    return dict(native_type_preserved=True, native_auto_respawn_active=True, native_auto_respawn_still_active=True,
        native_death_active_observed=True, native_death_ended=True, delay_unchanged=True, specs_unchanged=True,
        living_query=dict(owner_matches=True, dead=False), dead_query=dict(owner_matches=True, dead=True),
        after_query=dict(owner_matches=True, dead=False), old_pawn="old", new_pawn="new", health_before=100.,
        health_after_damage=0., respawn_health=100., original_delay=5., native_elapsed=8., native_net_policy=0,
        native_security_policy=3, native_owner_role=3, profile_switched=switched,
        native_pause_observed=name == "paused-world-time", counters=stats, specs_before={}, specs_after={},
        **{phase: dict(ability_authority=True, activation_mode=0, pawn_role=3, game_mode_available=True) for phase in AUTHORITY_PHASES})


def report():
    return dict(status="passed", error=None, original_profile_restored=True, original_specs_restored=True,
        real_lethal_gas_damage=True, network_acceptance=False, **{field: False for field in FALSE_FLAGS},
        cases=[dict(name=name, blueprint=row(name, "BlueprintFallback"), python=row(name, "Python")) for name in PLAN])


class HelperReportModels(unittest.TestCase):
    def test_bounded_synthetic_shape(self): self.assertEqual(validate(report())["pairs"], 4)

    def test_native_equipment_handle_renewal_preserves_logical_model(self):
        self.assertEqual(spec_model([(1, "weapon"), (2, "weapon")]), spec_model([(8, "weapon"), (9, "weapon")]))
        self.assertNotEqual(spec_model([(1, "weapon"), (2, "weapon")]), spec_model([(8, "weapon")]))

    def test_persistent_auto_respawn_handle_must_not_be_replaced(self):
        path = "/ShooterCore/Game/Respawn/GA_AutoRespawn.GA_AutoRespawn_C"
        self.assertNotEqual(spec_model([(1, path)]), spec_model([(2, path)]))

    def test_spec_flag_cannot_hide_changed_native_model(self):
        value = report(); value["cases"][0]["python"]["specs_after"] = {"changed": True}
        with self.assertRaises(RuntimeError): validate(value)

    def test_missing_pairs_and_reordered_pairs_rejected(self):
        for cases in (report()["cases"][:-1], list(reversed(report()["cases"]))):
            value = report(); value["cases"] = cases
            with self.assertRaises(RuntimeError): validate(value)

    def test_overclaims_and_restoration_fail_closed(self):
        for key in FALSE_FLAGS+("original_profile_restored", "original_specs_restored", "real_lethal_gas_damage"):
            value = report(); value[key] = not value[key]
            with self.subTest(key=key), self.assertRaises(RuntimeError): validate(value)

    def test_wrong_owner_or_death_query_rejected(self):
        for phase in ("living_query", "dead_query", "after_query"):
            for field in ("owner_matches", "dead"):
                value = report(); value["cases"][0]["python"][phase][field] = not value["cases"][0]["python"][phase][field]
                with self.subTest(phase=phase, field=field), self.assertRaises(RuntimeError): validate(value)

    def test_original_bp_must_reach_python_end_helper(self):
        for key in ("death_end_calls", "abilities_ended", "player_state_queries", "death_queries"):
            value = report(); value["cases"][0]["python"]["counters"][key] = 0
            with self.subTest(key=key), self.assertRaises(RuntimeError): validate(value)

    def test_native_damage_policy_and_restart_required(self):
        for key, replacement in (("new_pawn", "old"), ("original_delay", .1), ("health_after_damage", 50.),
            ("native_elapsed", 1.), ("native_security_policy", 0), ("native_owner_role", 2), ("native_death_ended", False),
            ("native_auto_respawn_still_active", False), ("specs_unchanged", False)):
            value = copy.deepcopy(report()); value["cases"][0]["python"][key] = replacement
            with self.subTest(key=key), self.assertRaises(RuntimeError): validate(value)

    def test_middeath_profile_switch_and_native_pause_required(self):
        for index, field in ((2, "profile_switched"), (3, "native_pause_observed")):
            value = report(); value["cases"][index]["python"][field] = False
            with self.assertRaises(RuntimeError): validate(value)


from uep_lyra_abilities import auto_respawn_helpers_network_contract as network


def reports():
    server = report(); server.update(peer="server", run_id="fixture", network_acceptance=True,
        player_ids={"A": 1, "B0": 2}, server_waited_for_client_process_exit=True, owners_restored_before_client_release=True,
        native_playing_gate=dict(native_playing_phase=True), all_owners_restored=True,
        owner_restoration={peer: dict(profile=True, specs=True, delay=True, alive=True) for peer in network.PEERS},
        gameplay_state_delivered_by_files=False, native_rpc_bypassed=False, packet_loss_tested=False, travel_rejoin_tested=False, cases=[])
    result = {"server": server}
    for peer in network.PEERS:
        client = report(); client.update(peer=peer, run_id="fixture", network_acceptance=True, cases=[], foreign_cases=[],
            player_id=server["player_ids"][peer], native_net_mode="Client", local_damage_applied=False,
            local_ability_activation_called=False, gameplay_state_delivered_by_files=False,
            native_rpc_bypassed=False, packet_loss_tested=False, travel_rejoin_tested=False, authority_phase_gate_observed=True)
        result[peer] = client
    position = 0
    for peer in network.PEERS:
        other = "B0" if peer == "A" else "A"
        for index in range(network.TRIALS):
            name, profile = network.NETWORK_PLAN[index//2], ("BlueprintFallback", "Python")[index % 2]
            authority = row(name, profile)
            authority.update(position=position, target=peer, index=index, name=name, profile=profile, foreign_owner_unchanged=True,
                native_auto_respawn_active=False, native_auto_respawn_still_active=False)
            owner = copy.deepcopy(authority); owner["native_owner_role"] = 2
            for phase in AUTHORITY_PHASES: owner[phase].update(pawn_role=2, game_mode_available=False)
            result[peer]["cases"].append(owner)
            foreign = dict(position=position, target=peer, local_owner_unchanged=True)
            result[other]["foreign_cases"].append(foreign)
            authority.update(owner_ack=dict(run_id="fixture", peer=peer, position=position, index=index, row=copy.deepcopy(owner)),
                foreign_ack=dict(run_id="fixture", peer=other, position=position, row=copy.deepcopy(foreign)))
            server["cases"].append(authority); position += 1
    return result


class HelperNetworkReportModels(unittest.TestCase):
    def test_complete_two_owner_synthetic_shape(self):
        self.assertEqual(network.validate(reports())["authority_trials"], 12)

    def test_distinct_real_client_identities_required(self):
        for mutate in (lambda data: data.pop("B0"), lambda data: data["A"].update(player_id=2),
            lambda data: data["A"].update(native_net_mode="Standalone")):
            value = reports(); mutate(value)
            with self.assertRaises(RuntimeError): network.validate(value)

    def test_every_authority_owning_and_foreign_case_required(self):
        for peer, field in (("server", "cases"), ("A", "cases"), ("B0", "foreign_cases")):
            value = reports(); value[peer][field].pop()
            with self.assertRaises(RuntimeError): network.validate(value)

    def sync_ack(self, value, index=0):
        value["server"]["cases"][index]["owner_ack"]["row"] = copy.deepcopy(value["A"]["cases"][index])

    def test_client_original_guard_requires_end_in_exact_final_profile(self):
        for index in range(network.TRIALS):
            for field in ("death_end_calls", "fallback_death_end_calls", "abilities_ended"):
                value = reports(); stats = value["A"]["cases"][index]["counters"]
                stats[field] = 1-stats[field]; self.sync_ack(value, index)
                with self.subTest(index=index, field=field), self.assertRaises(RuntimeError): network.validate(value)

    def test_client_ability_guard_is_distinct_from_pawn_role(self):
        value = reports()
        self.assertIs(value["A"]["cases"][0]["native_auto_respawn_active"], False)
        self.assertEqual(value["A"]["cases"][0]["native_authority_at_death"],
            dict(ability_authority=True, activation_mode=0, pawn_role=2, game_mode_available=False))
        self.assertEqual(network.validate(value)["owner_trials"], 12)

    def test_each_native_guard_snapshot_is_required_without_trusting_ack(self):
        for phase in AUTHORITY_PHASES:
            value = reports(); value["A"]["cases"][0].pop(phase); self.sync_ack(value)
            with self.subTest(phase=phase), self.assertRaises(RuntimeError): network.validate(value)

    def test_actual_authority_mode_role_and_gamemode_are_all_checked(self):
        for phase in AUTHORITY_PHASES:
            for field, invalid in (("ability_authority", False), ("activation_mode", 1), ("activation_mode", False),
                ("pawn_role", 3), ("game_mode_available", True)):
                value = reports(); value["A"]["cases"][0][phase][field] = invalid; self.sync_ack(value)
                with self.subTest(phase=phase, field=field), self.assertRaises(RuntimeError): network.validate(value)

    def test_bp_python_native_lifetime_must_match_even_if_each_is_stable(self):
        value = reports(); value["A"]["cases"][1].update(native_auto_respawn_active=True, native_auto_respawn_still_active=True)
        self.sync_ack(value, 1)
        with self.assertRaises(RuntimeError): network.validate(value)

    def test_original_bp_must_call_authority_python_helper(self):
        value = reports(); value["server"]["cases"][1]["counters"]["death_end_calls"] = 0
        with self.assertRaises(RuntimeError): network.validate(value)

    def test_foreign_observation_and_both_ack_identities_required(self):
        for mutate in (lambda data: data["server"]["cases"][0]["owner_ack"].update(run_id="foreign"),
            lambda data: data["server"]["cases"][0]["foreign_ack"].update(peer="A"),
            lambda data: data["A"]["foreign_cases"][0].update(local_owner_unchanged=False)):
            value = reports(); mutate(value)
            with self.assertRaises(RuntimeError): network.validate(value)

    def test_owner_report_cannot_disagree_with_authority_ack(self):
        value = reports(); value["A"]["cases"][0]["native_elapsed"] = 9.
        with self.assertRaises(RuntimeError): network.validate(value)

    def test_exit_barrier_restore_and_no_bypass_claims_required(self):
        for mutate in (lambda data: data["server"].update(server_waited_for_client_process_exit=False),
            lambda data: data["server"].update(owners_restored_before_client_release=False),
            lambda data: data["server"]["owner_restoration"]["A"].update(specs=False),
            lambda data: data["A"].update(authority_phase_gate_observed=False),
            lambda data: data["A"].update(local_damage_applied=True), lambda data: data["B0"].update(gameplay_state_delivered_by_files=True)):
            value = reports(); mutate(value)
            with self.assertRaises(RuntimeError): network.validate(value)
