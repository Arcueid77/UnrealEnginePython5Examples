"""Synthetic fail-closed listener evidence and single-fixture entry tests."""
import ast
import copy
from pathlib import Path
import sys
import types
import unittest
from test_auto_respawn_helpers_contract import report as helpers_report, reports as helpers_network
from uep_lyra_abilities import auto_respawn_listeners_contract as gate


def add_row(row, name, profile):
    final = "BlueprintFallback" if name == "profile-switch-during-death" and profile == "Python" else "Python" if name == "profile-switch-during-death" else profile
    initial_prefix, final_prefix = ("" if profile == "Python" else "fallback_"), ("" if final == "Python" else "fallback_")
    stats = {key: 0 for key in ("bind_calls", "clear_calls", "avatar_binds", "health_binds", "avatar_unbinds", "health_unbinds",
        "fallback_bind_calls", "fallback_clear_calls")}
    stats[initial_prefix+"clear_calls"] += 1; stats[final_prefix+"clear_calls"] += 1
    stats[final_prefix+"bind_calls"] += 1
    if final == "Python": stats.update(avatar_binds=1, health_binds=1)
    for phase in ("living_query", "dead_query", "after_query"):
        row[phase]["listener_cache"] = dict(avatar_matches=True, health_matches=phase != "dead_query", health_is_null=phase == "dead_query")
    row.update(listener_probe={field: True for field in gate.PROBE_FIELDS}, listener_foreign_events=["death", "endplay"],
        listener_observer_closed=True, listener_counters=stats)


def add_peer(report):
    count = len(report["cases"])*(1 if report["network_acceptance"] else 2)
    report.update(death_listener_orchestration_migrated=True, timer_restart_business_migrated=False,
        foreign_native_delegate_delivery_tested=True, synthetic_delegate_broadcast=False,
        listener_fixture_shutdown=dict(created=count, closed=count, active=0))


def report():
    value = helpers_report(); add_peer(value)
    for case in value["cases"]:
        for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")): add_row(case[key], case["name"], profile)
    return value


def reports():
    value = helpers_network()
    for peer, data in value.items():
        add_peer(data)
        for row in data["cases"]: add_row(row, row["name"], row["profile"])
    for row in value["server"]["cases"]:
        row["owner_ack"]["row"] = copy.deepcopy(value[row["target"]]["cases"][row["index"]])
    return value


class ListenerEvidenceModels(unittest.TestCase):
    def test_bounded_standalone_synthetic_shape(self): self.assertTrue(gate.validate(report())["listener_orchestration_verified"])
    def test_bounded_two_owner_synthetic_shape(self): self.assertEqual(gate.validate_network(reports())["authority_trials"], 12)

    def test_each_actual_clear_rebind_probe_required(self):
        for field in gate.PROBE_FIELDS:
            value = report(); value["cases"][0]["python"]["listener_probe"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_cache_flags_cannot_hide_old_or_uncleared_native_ownership(self):
        for phase in ("living_query", "dead_query", "after_query"):
            for field in ("avatar_matches", "health_matches", "health_is_null"):
                value = report(); cache = value["cases"][0]["python"][phase]["listener_cache"]; cache[field] = not cache[field]
                with self.subTest(phase=phase, field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_foreign_native_delivery_cannot_be_missing_duplicated_or_reordered(self):
        for events in ([], ["death"], ["death", "death", "endplay"], ["endplay", "death"]):
            value = report(); value["cases"][0]["python"]["listener_foreign_events"] = events
            with self.assertRaises(RuntimeError): gate.validate(value)

    def test_original_event_dispatch_cannot_be_replaced_by_probe_only(self):
        for field in ("bind_calls", "clear_calls", "avatar_binds", "health_binds"):
            value = report(); value["cases"][0]["python"]["listener_counters"][field] = 0
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_fixture_scopes_and_no_synthetic_broadcast_required(self):
        for mutate in (lambda r: r.update(timer_restart_business_migrated=True), lambda r: r.update(synthetic_delegate_broadcast=True),
            lambda r: r["listener_fixture_shutdown"].update(active=1), lambda r: r["listener_fixture_shutdown"].update(closed=7)):
            value = report(); mutate(value)
            with self.assertRaises(RuntimeError): gate.validate(value)

    def test_network_owner_evidence_checked_even_with_matching_ack(self):
        value = reports(); value["A"]["cases"][0]["listener_foreign_events"] = []
        value["server"]["cases"][0]["owner_ack"]["row"] = copy.deepcopy(value["A"]["cases"][0])
        with self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_inherited_helper_modules_do_not_launch_another_listener_fixture(self):
        root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities"
        for name, flag in (("auto_respawn_helpers_validation.py", "-UEPAutoRespawnHelpersResult=x"),
            ("auto_respawn_helpers_network_validation.py", "-UEPAutoRespawnHelpersNetworkResult=x")):
            footer = ast.parse((root/name).read_text(encoding="utf-8")).body[-1]
            def unexpected(*args): raise AssertionError("duplicate inherited native fixture")
            scope = dict(sys=types.SimpleNamespace(argv=[flag, "-UEPAutoRespawnListeners"]), result="x",
                Validation=unexpected, Server=unexpected, Client=unexpected, arg=unexpected)
            exec(compile(ast.Module(body=[footer], type_ignores=[]), str(root/name), "exec"), scope)
