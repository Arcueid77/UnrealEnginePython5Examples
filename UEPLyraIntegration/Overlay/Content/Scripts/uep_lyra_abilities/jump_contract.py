"""Fail-closed native input/ability comparison, not a hardware input claim."""
import argparse
import json
import math
from pathlib import Path

PLAN = ("release-fast", "release-held", "native-cancel", "external-native-end",
        "active-profile-switch", "native-state-end", "repeat-release")
FALSE_CLAIMS = ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested",
                "jump_called_by_probe", "ability_activation_called_by_probe", "task_callbacks_replayed",
                "velocity_or_gravity_written", "ability_granted_by_probe", "ui_grant_remove_tested")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None, "jump native report failed")
    require(report["enhanced_input_injection"] is True and report["native_gas_instance"] is True and
            report["player_restored"] is True, "jump input/source/restoration missing")
    require(all(report[name] is False for name in FALSE_CLAIMS), "unsupported jump acceptance claim")
    require([row["name"] for row in report["cases"]] == list(PLAN), "jump matrix incomplete")
    for row in report["cases"]:
        for profile in ("blueprint", "python"):
            side = row[profile]
            require(side["active_while_held"] and side["native_type_preserved"] and side["landed"] and
                    side["active_after"] is False and side["pressed_jump_after"] is False,
                    "jump native ability/character final state differs")
            require(math.isfinite(side["peak_rise"]) and side["peak_rise"] > 20. and side["jump_events"] == 1,
                    "jump physics/event proof missing or repeated")
            require(side["intervention"] == row["name"] and side["input_injections"] >= 2,
                    "jump ended before its native intervention")
            expected = "BlueprintFallback" if profile == "blueprint" else "Python"
            if row["name"] == "active-profile-switch":
                expected = "Python" if profile == "blueprint" else "BlueprintFallback"
            require(side["profile_after"] == expected, "jump instance Profile selection wrong")
            require(side["native_state_stopped_jump"] == (row["name"] == "native-state-end"),
                    "native state-end delegate not exercised")
        require(abs(row["blueprint"]["peak_rise"]-row["python"]["peak_rise"]) < 2.,
                "BP/Python native Jump apex differs beyond the two-centimetre sampling tolerance")
        counts = row["python_counters"]
        require(counts["activations"] == counts["states_created"] == counts["releases_created"] == 1 and
                counts["scopes_created"] == counts["scopes_closed"] == 1,
                "Python did not own exactly one native activation/task scope")
        require(counts["native_ends"] == int(row["name"] != "active-profile-switch"),
                "native EndAbility adapter/teardown count wrong")
        require(counts["input_releases"] == int(row["name"] in
                ("release-fast", "release-held", "native-state-end", "repeat-release")),
                "native input-release delegate count wrong")
        require(counts["state_ended"] == int(row["name"] == "native-state-end"), "native state delegate count wrong")
    shutdown = report["policy_shutdown"]
    require(shutdown["active_count"] == 0 and shutdown["scopes_created"] == shutdown["scopes_closed"] and
            shutdown["errors"] == [] and report["jump_observer_closed"] is True,
            "jump shutdown leaked task bindings or native observer")
    return dict(status="passed", bounded_runtime_acceptance=True, cases=len(PLAN), physical_input_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
