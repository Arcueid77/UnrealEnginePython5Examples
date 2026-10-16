import copy
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/dash_native_contract.py"
spec = importlib.util.spec_from_file_location("dash_native_report_contract", source)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def valid_report():
    report = {"schema_version": 1, "mode": "native-dash-gas-death-and-invalid-health", "status": "passed", "error": None,
              "native_request_accepted": True, "native_dash_producer_tested": True, "native_death_event_tested": True,
              "dead_health_tested": True, "invalid_health_feedback_tested": True, "production_widget": "production",
              "ability_class": "/ShooterCore/Game/Dash/GA_Hero_Dash.GA_Hero_Dash_C",
              "native_failure_delivery_count": 0, "native_failure_producer_tested": False, "cases": []}
    for flag in ("full_acceptance", "network_acceptance", "lethal_damage_tested", "fixture_event_invoked",
                 "ability_or_health_properties_written", "physical_key_input_tested", "duration_broadcast_called_by_fixture",
                 "widget_tick_invoked_by_fixture", "lifecycle_event_invoked_by_fixture"):
        report[flag] = False
    state = {"duration": 5.0, "start": 1.0, "visibility": 3, "glow": 0.25, "fill": 0.25, "charging": True}
    for index, name in enumerate(contract.CASES):
        if index in (0, 2):
            actual = dict(state, charging=index == 0)
            report["cases"].append({"name": name, "widget": "production", "profile": "Python", "test_owned_lifecycle_widget": False,
                                     "automatic_ticks": 3, "python": actual, "blueprint": dict(actual)})
        elif index == 1:
            report["cases"].append({"name": name, "accepted": False, "duration_deliveries": 1})
        elif index == 3:
            report["cases"].append({"name": name, "death_state": 1, "death_callbacks": 1,
                                     "python": {"visibility": 1}, "blueprint": {"visibility": 1}})
        else:
            report["cases"].append({"name": name, "synthetic_payload": True, "owner_has_pawn": False,
                                     "python": {"visibility": 1}, "blueprint": {"visibility": 1}})
    final = {"active_count": 0, "scopes_created": 4, "scopes_closed": 4, "errors": []}
    report["shutdown"], report["failure_shutdown"] = dict(final), dict(final)
    report["shutdown"]["pool_lifetime"] = {"active_count": 0, "ticker_active": False, "registered": 1, "unregistered": 1, "errors": []}
    return report


class NativeDashReportTests(unittest.TestCase):
    def test_native_gate_has_bounded_claim(self):
        result = contract.validate(valid_report())
        self.assertTrue(result["native_dash_producer_tested"])
        self.assertFalse(result["native_failure_producer_tested"])
        self.assertFalse(result["full_acceptance"])

    def test_synthetic_duration_or_manual_event_cannot_claim_native_producer(self):
        for flag in ("duration_broadcast_called_by_fixture", "ability_or_health_properties_written", "fixture_event_invoked",
                     "widget_tick_invoked_by_fixture", "lethal_damage_tested"):
            report = valid_report()
            report[flag] = True
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_missing_actual_activation_death_or_invalid_branch_rejected(self):
        for flag in ("native_request_accepted", "native_dash_producer_tested", "native_death_event_tested", "invalid_health_feedback_tested"):
            report = valid_report()
            report[flag] = False
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_wrong_ability_or_model_rejected(self):
        report = valid_report()
        report["ability_class"] = "test-owned-replacement"
        with self.assertRaises(AssertionError):
            contract.validate(report)
        report = valid_report()
        report["cases"][0]["blueprint"]["duration"] = 7.0
        with self.assertRaises(AssertionError):
            contract.validate(report)

    def test_failure_producer_claim_must_have_native_delivery(self):
        report = valid_report()
        report["native_failure_producer_tested"] = True
        with self.assertRaises(AssertionError):
            contract.validate(report)

    def test_case_inventory_and_final_lifetime_rejected(self):
        for mutate in (lambda report: report["cases"].pop(),
                       lambda report: report["failure_shutdown"].update(active_count=1),
                       lambda report: report["shutdown"]["pool_lifetime"].update(ticker_active=True)):
            report = valid_report()
            mutate(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)


if __name__ == "__main__":
    unittest.main()
