"""Evidence-gate tests; fabricated reports below are not Unreal acceptance."""

import ast
import copy
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"
sys.path.insert(0, str(SCRIPTS))
from uep_lyra_hud.ability_failure_contract import CASES, EXPECTED_STATES, validate_report, validate_culture_report


def report_fixture():
    report = {"schema_version": 2, "status": "passed", "error": None,
              "timer_clock": "native-retriggerable-delay", "paused_world_clock_frozen": True, "paused_ui_expired": True,
              "production_widget": "W_ShooterHUDLayout_C_0.W_AbilityFailureFeedback",
              "production_default_profile": "Python", "cases": [], "paused_wall_seconds": 1.1,
              "first_outro_timing": {"python_seconds": 1.01, "blueprint_seconds": 1.02,
                                      "max_observed_ui_frame": 0.02, "tolerance_seconds": 0.04},
              "animation_transitions": [{"fixture": True}], "different_outro_observed": True,
              "shutdown": {"active_count": 0, "scopes_created": 4, "scopes_closed": 4,
                           "tickers_created": 0, "tickers_closed": 0, "native_delay_callbacks": 5, "errors": []}}
    for name in ("production_reachability_tested", "compiled_vm_transport", "profile_resume_explicit"):
        report[name] = True
    for name in ("full_acceptance", "network_acceptance", "native_ability_producer_tested",
                 "native_localized_text_identity_tested", "dead_health_branch_tested",
                 "widget_event_invoked_by_fixture", "original_oninitialized_replayed"):
        report[name] = False
    for name, (text, visibility) in zip(CASES, EXPECTED_STATES):
        state = {"text": text or "original asset text", "visibility": visibility}
        report["cases"].append({"name": name, "same_class": True, "python": state, "blueprint": copy.deepcopy(state)})
    return report


class FailureContractTests(unittest.TestCase):
    def setUp(self):
        self.report = report_fixture()

    def test_complete_bounded_report_passes_gate(self):
        self.assertTrue(validate_report(self.report))

    def test_normal_exit_or_pre_shutdown_status_is_not_acceptance(self):
        for status in ("running", "awaiting_shutdown", "failed"):
            self.report["status"] = status
            with self.assertRaises(AssertionError):
                validate_report(self.report)

    def test_missing_repeated_and_reordered_cases_are_rejected(self):
        cases = self.report["cases"]
        for changed in (cases[:-1], cases + [cases[0]], list(reversed(cases))):
            self.report["cases"] = changed
            with self.assertRaises(AssertionError):
                validate_report(self.report)

    def test_equal_but_wrong_authored_visibility_is_rejected(self):
        self.report["cases"][0]["python"]["visibility"] = 3
        self.report["cases"][0]["blueprint"]["visibility"] = 3
        with self.assertRaisesRegex(AssertionError, "authored case"):
            validate_report(self.report)

    def test_blueprint_python_reason_mismatch_is_rejected(self):
        self.report["cases"][2]["blueprint"]["text"] = "foreign was displayed"
        with self.assertRaisesRegex(AssertionError, "visible state"):
            validate_report(self.report)

    def test_synthetic_input_cannot_claim_native_or_full_acceptance(self):
        for name in ("native_ability_producer_tested", "native_localized_text_identity_tested",
                     "dead_health_branch_tested", "full_acceptance", "network_acceptance"):
            changed = copy.deepcopy(self.report)
            changed[name] = True
            with self.assertRaisesRegex(AssertionError, "unbounded claim"):
                validate_report(changed)

    def test_missing_natural_animation_and_ownership_evidence_is_rejected(self):
        for name, value in (("production_reachability_tested", False), ("animation_transitions", []),
                            ("different_outro_observed", False), ("production_widget", "test-owned-only")):
            changed = copy.deepcopy(self.report)
            changed[name] = value
            with self.assertRaises(AssertionError):
                validate_report(changed)

    def test_timer_gate_does_not_accept_nan_or_widened_tolerance(self):
        for key, value in (("python_seconds", float("nan")), ("python_seconds", 1.1),
                           ("tolerance_seconds", 0.14), ("max_observed_ui_frame", 0.2)):
            changed = copy.deepcopy(self.report)
            changed["first_outro_timing"][key] = value
            with self.assertRaises(AssertionError):
                validate_report(changed)

    def test_unbalanced_or_errored_lifecycle_is_rejected(self):
        for key, value in (("active_count", 1), ("scopes_closed", 3), ("tickers_closed", 3),
                           ("errors", ["cancel failed"])):
            changed = copy.deepcopy(self.report)
            changed["shutdown"][key] = value
            with self.assertRaisesRegex(AssertionError, "shutdown"):
                validate_report(changed)

    def test_native_widget_events_are_not_directly_invoked_by_fixture(self):
        tree = ast.parse((SCRIPTS / "uep_lyra_hud/ability_failure_validation.py").read_text(encoding="utf-8"))
        prohibited = {"Tick", "OnInitialized", "Construct", "Destruct", "OnAnimationFinished",
                      "OutroCompleted", "OutroCurrentCompleted", "SetAnimationCurrentTime"}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            self.assertNotIn(node.func.attr, prohibited)
            if node.func.attr in ("call_function", "call_mixin_original") and node.args:
                if isinstance(node.args[0], ast.Constant):
                    self.assertNotIn(node.args[0].value, prohibited)


class FailureCultureContractTests(unittest.TestCase):
    def setUp(self):
        self.report = {"schema_version": 1, "status": "passed", "error": None,
            "native_localized_text_identity_tested": True, "native_ability_producer_tested": False,
            "full_acceptance": False, "network_acceptance": False, "rebroadcast_on_culture_change": False,
            "fixture_event_invoked": False, "seed": {"namespace": "InputKeys", "key": "LeftMouseButton", "native_live_table": True},
            "cases": [], "shutdown": {"active_count": 0, "scopes_created": 2, "scopes_closed": 2, "errors": []}}
        for culture, text in (("en", "Left Mouse Button"), ("zh-Hans", "鼠标左键"), ("en", "Left Mouse Button")):
            state = {"text": text, "visibility": 3}
            self.report["cases"].append({"culture": culture, "python": state, "blueprint": copy.deepcopy(state)})

    def test_native_text_roundtrip_report_passes(self):
        self.assertTrue(validate_culture_report(self.report))

    def test_unchanged_display_string_does_not_prove_native_identity(self):
        self.report["cases"][1]["python"]["text"] = "Left Mouse Button"
        self.report["cases"][1]["blueprint"]["text"] = "Left Mouse Button"
        with self.assertRaisesRegex(AssertionError, "identity"):
            validate_culture_report(self.report)

    def test_rebroadcast_cannot_prove_original_native_text_was_preserved(self):
        self.report["rebroadcast_on_culture_change"] = True
        with self.assertRaisesRegex(AssertionError, "scope"):
            validate_culture_report(self.report)

    def test_native_gas_claim_is_not_a_live_text_fixture_result(self):
        self.report["native_ability_producer_tested"] = True
        with self.assertRaisesRegex(AssertionError, "scope"):
            validate_culture_report(self.report)

    def test_culture_shutdown_leak_is_rejected(self):
        self.report["shutdown"]["scopes_closed"] = 1
        with self.assertRaisesRegex(AssertionError, "shutdown"):
            validate_culture_report(self.report)


if __name__ == "__main__":
    unittest.main()
