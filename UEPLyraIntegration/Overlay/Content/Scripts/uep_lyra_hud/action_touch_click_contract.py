"""Native CommonUI -> EnhancedInput -> GAS Jump, separate from touch hardware."""
import argparse
import json
import math
from pathlib import Path

PLAN = tuple((kind, profile) for kind in ("base", "mobile") for profile in ("BlueprintFallback", "Python"))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed", "native action-touch click report failed")
    require(report["synthetic_commonui_activation"] is True and report["native_input_gas_jump_tested"] is True and
            report["player_restored"] is True and report["jump_observer_closed"] is True,
            "native click/Jump or restore provenance incomplete")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_touch_tested",
                  "jump_or_launch_called_by_probe", "velocity_or_gravity_written", "ability_granted_by_probe"):
        require(report[field] is False, "unsupported click claim: "+field)
    require(len(report["cases"]) == len(PLAN) and report["widgets_created"] == report["widget_roots_released"] == 4,
            "click native matrix/root cleanup incomplete")
    for row, identity in zip(report["cases"], PLAN):
        require((row["kind"], row["profile"]) == identity and row["native_commonui_activations"] == 1 and
                row["native_jump_events"] == 1 and row["jump_event_pawn"] == report["player_pawn"],
                "click native activation crossed owner/replayed")
        require(math.isfinite(row["rise"]) and row["rise"] > 20. and row["movement_mode"] == 3 and
                row["vertical_velocity"] > 20., "native click did not produce actual Jump physics")
        require(row["python_clicks"] == int(identity[1] == "Python") and row["native_type_preserved"] is True,
                "click Python bypassed/replayed/type changed")
    require(report["policy_shutdown"]["active_count"] == 0 and report["policy_shutdown"]["errors"] == [],
            "click policy retained a subscription")
    return dict(status="passed", bounded_runtime_acceptance=True, cases=4,
                native_input_gas_jump_tested=True, physical_touch_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
