"""Natural full-policy startup evidence cannot substitute for lifecycle tests."""
import ast
import copy
from pathlib import Path
import types
import unittest
from test_auto_respawn_events_contract import report as event_report, reports as event_reports
from uep_lyra_abilities import auto_respawn_activation_contract as gate


def add_peer(report, profile="Python"):
    prefix = "" if profile == "Python" else "fallback_"
    report.update(activation_reset_ui_removal_business_migrated=True, activation_natural_regression_only=True,
        full_auto_respawn_acceptance=False, activation_startup_profile=profile,
        activation_startup={prefix+"added": 1, prefix+"activated": 1, prefix+"avatar_set": 1})


def add_row(row, name, profile):
    final = "BlueprintFallback" if name == "profile-switch-during-death" and profile == "Python" else "Python" if name == "profile-switch-during-death" else profile
    stats = dict(avatar_set=0, fallback_avatar_set=0, native_reset_starts=0, removed=0, fallback_removed=0, end_cleanups=0, fallback_end_cleanups=0)
    stats[("" if final == "Python" else "fallback_")+"avatar_set"] = 1
    row["activation_counters"] = stats
    for phase in ("living_query", "dead_query", "after_query"):
        row[phase]["activation_state"] = dict(listening=True, proxy_active=True, ended=False)


def report(profile="Python"):
    value = event_report(); add_peer(value, profile)
    for row in value["cases"]:
        add_row(row["blueprint"], row["name"], "BlueprintFallback"); add_row(row["python"], row["name"], "Python")
    return value


def reports():
    value = event_reports()
    for data in value.values():
        add_peer(data)
        for row in data["cases"]: add_row(row, row["name"], row["profile"])
    for row in value["server"]["cases"]: row["owner_ack"]["row"] = copy.deepcopy(value[row["target"]]["cases"][row["index"]])
    return value


class ActivationNaturalEvidenceModels(unittest.TestCase):
    def test_actual_startup_profile_variants_have_bounded_shape(self):
        for profile in ("Python", "BlueprintFallback"):
            self.assertTrue(gate.validate(report(profile))["actual_activation_startup_observed"])

    def test_two_actual_owners_natural_shape(self): self.assertEqual(gate.validate_network(reports())["authority_trials"], 12)

    def test_added_avatar_and_actual_standalone_activation_all_required(self):
        for field in ("added", "avatar_set", "activated"):
            value = report(); value["activation_startup"][field] = 0
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_root_inactive_client_still_requires_avatar_set_but_not_activation(self):
        value = reports(); value["A"]["activation_startup"]["activated"] = 0
        self.assertTrue(gate.validate_network(value)["actual_activation_startup_observed"])

    def test_native_listener_active_and_not_ended_at_every_natural_phase(self):
        for phase in ("living_query", "dead_query", "after_query"):
            for field in ("listening", "proxy_active", "ended"):
                value = report(); state = value["cases"][0]["python"][phase]["activation_state"]; state[field] = not state[field]
                with self.subTest(phase=phase, field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_natural_respawn_cannot_duplicate_native_listener_or_end_ability(self):
        for field in ("native_reset_starts", "removed", "fallback_removed", "end_cleanups", "fallback_end_cleanups"):
            value = report(); value["cases"][0]["python"]["activation_counters"][field] = 1
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_natural_gate_cannot_claim_full_lifecycle_acceptance(self):
        value = report(); value["full_auto_respawn_acceptance"] = True
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_event_modules_cannot_start_a_duplicate_activation_fixture(self):
        root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities"
        for name, flag in (("auto_respawn_events_validation.py", "-UEPAutoRespawnHelpersResult=x"),
            ("auto_respawn_events_network_validation.py", "-UEPAutoRespawnHelpersNetworkResult=x")):
            footer = ast.parse((root/name).read_text(encoding="utf-8")).body[-1]
            def unexpected(*args): raise AssertionError("duplicate inherited event fixture")
            scope = dict(sys=types.SimpleNamespace(argv=[flag, "-UEPAutoRespawnEvents", "-UEPAutoRespawnActivation"]), result="x",
                Validation=unexpected, Server=unexpected, Client=unexpected, arg=unexpected)
            exec(compile(ast.Module(body=[footer], type_ignores=[]), str(root/name), "exec"), scope)
