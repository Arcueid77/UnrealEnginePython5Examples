"""Pressed-widget report rejection models; not native UI/network proof."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_abilities import widget_pressed_contract as gate
from uep_lyra_abilities import widget_pressed_network_contract as network


def report():
    value = dict(status="passed", error=None, cases=[], pending_regressions=[], mixed_profiles=[],
        fixture_scopes_created=28, fixture_scopes_closed=28,
        policy_shutdown=dict(active_count=0, scopes_created=74, scopes_closed=74, errors=[]))
    value.update({field: False for field in gate.FALSE_CLAIMS})
    value.update({field: True for field in ("original_specs_restored", "original_profiles_restored", "original_cdos_preserved",
                                           "native_layer_restored", "fixture_observers_closed")})
    for target in gate.TARGETS:
        for name in gate.PLAN:
            row = {field: True for field in ("native_type_preserved", "profile_selected", "original_config_preserved", "native_widget_active",
                "native_widget_owner", "native_original_layer", "release_kept_ui", "native_ability_ended", "layer_restored", "specs_preserved",
                "foreign_listener_preserved", "no_late_callbacks", "ordinary_end_preserved_native_ui", "profile_teardown_ended_all",
                "inactive_handoff_kept_ui", "native_pause_observed", "native_ui_active_during_pause")}
            row.update(widget_class=gate.WIDGETS[target], native_tasks_during=0, native_tasks_after=0, input_injections=1,
                       native_instance_count=2, foreign_native_events=1)
            bp, py = copy.deepcopy(row), copy.deepcopy(row)
            bp["counters"] = dict(fallback_activations=2, activations=0)
            py["counters"] = dict(activations=2, pushes_requested=2, widgets_pushed=2, fallback_activations=0, scopes_created=4, scopes_closed=4)
            value["cases"].append(dict(target=target, name=name, blueprint=bp, python=py))
        for name in ("cancel-pending", "profile-switch-pending", "other-spec-pending"):
            row = {field: True for field in ("native_pending_observed", "native_pending_proxy_collected", "native_scopes_balanced",
                "native_layer_restored", "native_abilities_ended", "no_late_callbacks", "native_asc_handle_activation_fixture")}
            value["pending_regressions"].append(dict(row, target=target, name=name, bp_parity_claimed=False))
        for order in (0, 1):
            row = {field: True for field in ("native_asc_handle_activation_fixture", "profiles_independent", "native_type_preserved",
                "native_ui_observed", "native_layer_restored", "scopes_balanced")}
            value["mixed_profiles"].append(dict(row, target=target, order=order, counters=dict(activations=1, fallback_activations=1)))
    return value


def reports():
    server = dict(status="passed", error=None, peer="server", run_id="fixture", cases=[], player_ids={"A": 251, "B0": 252},
        native_context_ready=True, original_authority_states_restored=True, server_waited_for_client_process_exit=True,
        native_authority_initial_states={}, policy_shutdown=dict(activations=0, fallback_activations=0, scopes_created=0, scopes_closed=0, active_count=0, errors=[]))
    flags = ("full_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed", "task_callbacks_replayed",
             "packet_loss_tested", "travel_rejoin_tested", "gameplay_state_delivered_by_files", "localonly_ui_replication_claimed")
    server.update({field: False for field in flags}); result = dict(server=server)
    for peer in network.PEERS:
        other = next(value for value in network.PEERS if value != peer)
        owner = report()
        owner.update(cases=[row for row in owner["cases"] if row["name"] in gate.NETWORK_PLAN], pending_regressions=[], mixed_profiles=[],
            fixture_scopes_created=24, fixture_scopes_closed=24, peer=peer, run_id="fixture", player_id=server["player_ids"][peer],
            native_owner_role=2, native_net_mode="Client", passive_held_observations=[])
        owner.update({field: False for field in flags}); result[peer] = owner
        server["native_authority_initial_states"][peer] = dict(role=3,
            abilities=[dict(cls=path, active=False, tasks=0, net=1) for path in gate.CLASSES.values() for _ in range(2)])
        for index in range(network.TRIALS):
            passive = dict(run_id="fixture", peer=other, target=peer, index=index, stage="held", player_id=server["player_ids"][other],
                native_ability_count=4, native_owner_unchanged=True, native_menu_empty=True, native_all_inactive=True,
                native_profiles_preserved=True, native_specs_preserved=True)
            server["cases"].append(dict(target=peer, index=index, ui_target=gate.TARGETS[index // (len(gate.NETWORK_PLAN) * 2)],
                name=gate.NETWORK_PLAN[(index // 2) % len(gate.NETWORK_PLAN)], profile=("BlueprintFallback", "Python")[index % 2],
                authority_inactive_samples=3, native_authority_unchanged=True, foreign_local_owner_observed=True,
                client=dict(run_id="fixture", peer=peer, index=index, row=copy.deepcopy(owner["cases"][index // 2][("blueprint", "python")[index % 2]])), passive=passive))
    for peer in network.PEERS:
        result[peer]["passive_held_observations"] = [copy.deepcopy(row["passive"]) for row in server["cases"] if row["target"] != peer]
    return result


class PressedGate(unittest.TestCase):
    def test_complete_report_shape_only(self):
        self.assertEqual(gate.validate(report())["pairs"], 14)

    def test_missing_pair_or_wrong_ui_is_rejected(self):
        for mutate in (lambda data: data["cases"].pop(), lambda data: data["cases"][0]["python"].update(widget_class="wrong")):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_duplicate_grants_cannot_be_deleted_or_wrong_profile_executed(self):
        for mutate in (lambda data: data["cases"][0]["python"].update(native_instance_count=1),
                       lambda data: data["cases"][0]["python"]["counters"].update(fallback_activations=1)):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_ordinary_end_must_keep_native_ui_but_active_handoff_must_end(self):
        for index, field in ((1, "ordinary_end_preserved_native_ui"), (3, "profile_teardown_ended_all"), (5, "inactive_handoff_kept_ui")):
            value = report(); value["cases"][index]["python"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_pending_gc_and_same_bp_instance_independence_required(self):
        for mutate in (lambda data: data["pending_regressions"][0].update(native_pending_proxy_collected=False),
                       lambda data: data["pending_regressions"][0].update(bp_parity_claimed=True),
                       lambda data: data["mixed_profiles"][0].update(profiles_independent=False)):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_shutdown_leak_or_widened_claim_rejected(self):
        for mutate in (lambda data: data["policy_shutdown"].update(active_count=1), lambda data: data.update(fixture_scopes_closed=0),
                       lambda data: data.update(input_filter_tokens_directly_observed=True)):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)


class PressedNetworkGate(unittest.TestCase):
    def test_complete_network_shape_only(self):
        self.assertEqual(network.validate_network(reports())["native_owner_trials"], 48)

    def test_two_distinct_real_clients_required(self):
        for mutate in (lambda data: data.pop("B0"), lambda data: data["A"].update(native_owner_role=3), lambda data: data["A"].update(player_id=252)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): network.validate_network(value)

    def test_native_localonly_authority_must_stay_idle(self):
        for mutate in (lambda data: data["server"]["policy_shutdown"].update(activations=1),
                       lambda data: data["server"]["native_authority_initial_states"]["A"]["abilities"][0].update(net=0),
                       lambda data: data["server"]["cases"][0].update(native_authority_unchanged=False)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): network.validate_network(value)

    def test_every_foreign_ui_profile_and_spec_observation_required(self):
        for mutate in (lambda data: data["A"]["passive_held_observations"].pop(),
                       lambda data: data["A"]["passive_held_observations"][0].update(native_profiles_preserved=False),
                       lambda data: data["B0"]["passive_held_observations"][0].update(native_specs_preserved=False)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): network.validate_network(value)

    def test_ack_identity_order_and_source_row_must_match(self):
        for mutate in (lambda data: data["server"]["cases"][0]["client"].update(index=2),
                       lambda data: data["server"]["cases"][0].update(ui_target="map"),
                       lambda data: data["server"]["cases"][0]["client"]["row"].update(input_injections=2)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): network.validate_network(value)

    def test_normal_exits_and_narrow_scope_required(self):
        for mutate in (lambda data: data["server"].update(server_waited_for_client_process_exit=False),
                       lambda data: data["A"].update(localonly_ui_replication_claimed=True), lambda data: data["B0"].update(travel_rejoin_tested=True)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): network.validate_network(value)


if __name__ == "__main__": unittest.main()
