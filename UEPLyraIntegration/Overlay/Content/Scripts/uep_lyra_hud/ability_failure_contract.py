"""Pure report gate for a bounded failure-feedback differential, not all Lyra."""

import json
import math
from pathlib import Path
import sys


CASES = (
    "initial-collapsed", "typed-owner-reason", "foreign-owner-ignored",
    "same-reason-no-retrigger", "paused-world-ui-delay-continues",
    "one-second-native-outro-boundary", "native-outro-completion-collapses",
    "hidden-blueprint-resume", "hidden-python-resume", "resumed-message-exact-once",
    "destruct-no-late-delivery", "same-widget-native-reconstruct",
    "different-reason-waits-for-outro", "different-reason-after-native-outro",
    "deferred-latest-foreign-payload", "persistent-outro-callback-order",
    "profile-teardown-cancels-pending-work",
)
EXPECTED_STATES = (
    (None, 1), ("UEP failure A", 3), ("UEP failure A", 3), ("UEP failure A", 3),
    ("UEP failure A", 1), ("UEP failure A", 1), ("UEP failure A", 1),
    ("UEP failure A", 1), ("UEP failure A", 1), ("UEP resumed", 3),
    ("UEP resumed", 1), ("UEP remount", 3), ("UEP remount", 3),
    ("UEP replacement", 3), ("UEP foreign deferred", 3), ("UEP foreign deferred", 1),
    ("pending first", 3),
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_report(report):
    require(report.get("schema_version") == 2 and report.get("status") == "passed",
            "failure fixture did not pass after shutdown")
    require(report.get("error") is None, "failure fixture recorded an error")
    for name in ("production_reachability_tested", "compiled_vm_transport", "profile_resume_explicit"):
        require(report.get(name) is True, "missing bounded evidence: " + name)
    for name in ("full_acceptance", "network_acceptance", "native_ability_producer_tested",
                 "native_localized_text_identity_tested", "dead_health_branch_tested",
                 "widget_event_invoked_by_fixture", "original_oninitialized_replayed"):
        require(report.get(name) is False, "unexpected or unbounded claim: " + name)
    require(report.get("production_default_profile") == "Python", "production did not declare Python")
    require("W_ShooterHUDLayout" in report.get("production_widget", "") and
            "W_AbilityFailureFeedback" in report.get("production_widget", ""), "not the production HUD widget")
    cases = report.get("cases", [])
    require([case.get("name") for case in cases] == list(CASES), "missing, repeated or reordered failure case")
    for case, (text, visibility) in zip(cases, EXPECTED_STATES):
        require(case.get("same_class") is True, "failure widget class changed")
        require(set(case.get("python", {})) == {"text", "visibility"} and
                case["python"] == case.get("blueprint"), "failure BP/Python visible state differs")
        require(isinstance(case["python"]["text"], str) and case["python"]["visibility"] == visibility and
                (text is None or case["python"]["text"] == text), "failure authored case state differs")
    pause = report.get("paused_wall_seconds", 0)
    require(math.isfinite(pause) and pause >= 1.0, "game-clock pause not exercised")
    require(report.get("timer_clock") == "native-retriggerable-delay" and
            report.get("paused_world_clock_frozen") is True and report.get("paused_ui_expired") is True,
            "native widget-clock pause behavior not proved")
    timing = report.get("first_outro_timing", {})
    step = timing.get("max_observed_ui_frame", 0)
    bound = timing.get("tolerance_seconds", 0)
    require(math.isfinite(step) and 0 < step <= 0.075, "invalid native UI-frame sampling")
    require(math.isfinite(bound) and 0 < bound <= 0.15 and bound <= max(0.025, 2 * step) + 1e-6,
            "timer comparison widened beyond two observed UI frames")
    actual, original = timing.get("python_seconds", 0), timing.get("blueprint_seconds", 0)
    require(all(math.isfinite(value) and abs(value - 1.0) <= bound for value in (actual, original)) and
            abs(actual - original) <= bound, "one-second native outro boundary differs")
    require(report.get("animation_transitions") and report.get("different_outro_observed") is True,
            "natural animations were not observed")
    final = report.get("shutdown", {})
    require(final.get("active_count") == 0 and final.get("scopes_created", 0) >= 4 and
            final.get("scopes_created") == final.get("scopes_closed") and
            final.get("tickers_created") == final.get("tickers_closed") == 0 and
            final.get("native_delay_callbacks", 0) > 0 and final.get("errors") == [],
            "failure scope/ticker shutdown incomplete")
    return True


def validate_culture_report(report):
    require(report.get("schema_version") == 1 and report.get("status") == "passed" and report.get("error") is None,
            "native culture fixture did not pass after shutdown")
    require(report.get("native_localized_text_identity_tested") is True and
            report.get("native_ability_producer_tested") is False and report.get("full_acceptance") is False and
            report.get("network_acceptance") is False and report.get("rebroadcast_on_culture_change") is False and
            report.get("fixture_event_invoked") is False, "native culture scope differs")
    require(report.get("seed") == {"namespace": "InputKeys", "key": "LeftMouseButton", "native_live_table": True},
            "native text seed provenance differs")
    cases = report.get("cases", [])
    require([case["culture"] for case in cases] == ["en", "zh-Hans", "en"], "missing culture roundtrip")
    for case in cases:
        require(case["python"] == case["blueprint"] and case["python"]["visibility"] == 3 and
                isinstance(case["python"]["text"], str) and case["python"]["text"], "native culture UI mismatch")
    require(cases[0]["python"]["text"] == cases[2]["python"]["text"] == "Left Mouse Button" and
            cases[1]["python"]["text"] != cases[0]["python"]["text"], "localized text identity did not survive")
    final = report.get("shutdown", {})
    require(final.get("active_count") == 0 and final.get("scopes_created", 0) >= 2 and
            final.get("scopes_created") == final.get("scopes_closed") and final.get("errors") == [],
            "native culture scope shutdown incomplete")
    return True


if __name__ == "__main__":
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    (validate_culture_report if "--culture" in sys.argv else validate_report)(report)
    print("UEP_ABILITY_FAILURE_REPORT_GATE_PASSED")
