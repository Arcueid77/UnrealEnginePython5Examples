"""Bounded rendered-UMG function/message/lifecycle proof, not physical touch."""
import argparse
import json
import math
from pathlib import Path

CASES = ("initial", "style-flags", "primed-reset", "disabled", "enabled", "selected", "deselected",
         "owner-duration", "foreign-owner-ignored", "restart-duration", "paused-game-time",
         "completed", "destruct-no-delivery", "native-reconstruct", "live-profile-roundtrip")


def cases_for(kind):
    return tuple("original-child-no-tick" if kind == "mobile" and name == "completed" else name for name in CASES)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def equal(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b) < .0001
    return a == b


def validate(report):
    require(report["status"] == "passed", "action-touch native report failed")
    for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_touch_tested",
                 "native_input_action_effect_tested", "widget_tick_called_by_probe", "production_placement_tested"):
        require(report[flag] is False, "unsupported action-touch claim: "+flag)
    require(report["test_owned_mounted_pairs"] is True and report["direct_bp_functions_called_by_probe"] is True and
            report["native_commonui_state_changes"] is True and report["synthetic_typed_duration_producer"] is True,
            "action-touch fixture/transport provenance missing")
    require(report["widgets_created"] == report["widgets_removed"] == report["widget_roots_released"] == 4 and
            report["owned_listeners_closed"] is True and report["native_widget_reconstruction_tested"] is True,
            "action-touch widget/listener cleanup incomplete")
    require(len(report["cases"]) == len(CASES)*2, "action-touch native matrix incomplete")
    require([row["cdo"]["bHasScriptImplementedTick"] for row in report["native_widget_scheduling"]] == [True, False] and
            all(row["cdo"]["TickFrequency"] == 1 and all(widget["bHasScriptImplementedTick"] is (row["kind"] == "base")
                and widget["TickFrequency"] == 1 for widget in row["widgets"]) for row in report["native_widget_scheduling"]),
            "action-touch original native Tick scheduling changed")
    for row, (kind, name) in zip(report["cases"], ((kind, name) for kind in ("base", "mobile") for name in cases_for(kind))):
        require((row["kind"], row["name"]) == (kind, name) and row["same_class"] is True and
                (row["automatic_ticks"] > 1 if kind == "base" else row["automatic_ticks"] == 0) and equal(row["python"], row["blueprint"]),
                "action-touch native BP/Python state/type/ticks differ")
    require(report["shutdown"]["active_count"] == 0 and report["shutdown"]["errors"] == [] and
            report["shutdown"]["scopes_created"] == report["shutdown"]["scopes_closed"],
            "action-touch shutdown subscription imbalance")
    return dict(status="passed", bounded_runtime_acceptance=True, cases=len(CASES)*2,
                network_acceptance=False, physical_touch_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
