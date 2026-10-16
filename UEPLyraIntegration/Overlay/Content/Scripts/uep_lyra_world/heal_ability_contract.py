"""Bounded native GAS/animation/timer proof; not network or placement proof."""
import argparse
import json
from pathlib import Path
import sys
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from uep_lyra_world.launcher_contract import equal, require

PLAN = ("original-montage", "native-cancel", "native-interrupt", "native-timer", "paused-world-time", "active-profile-switch", "external-native-end")


def validate(report):
    require(report["status"] == "passed" and len(report["cases"]) == len(PLAN), "native heal ability matrix incomplete")
    for flag in ("network_acceptance", "full_acceptance", "packaged_runtime", "ability_activate_called_by_probe",
                 "task_callbacks_called_by_probe", "health_properties_written", "animation_assets_modified", "production_placement_tested"):
        require(report[flag] is False, "unsupported heal ability claim: "+flag)
    require(report["native_inventory_equipment_ability_grant"] is True and report["original_player_restored"] is True,
            "heal ability native source/restore proof missing")
    for row, name in zip(report["cases"], PLAN):
        require(row["name"] == name and row["passed"] is True and equal(row["blueprint"], row["python"]),
                "heal ability BP/Python outcome differs")
        for side in ("blueprint", "python"):
            result = row[side]
            require(result["active_after"] is False and result["health_after"] > result["health_before"] and
                    result["health_after"] <= result["max_health"] and result["native_type_preserved"] is True,
                    "native heal effect/ability end/type missing")
        require(row["python_counters"]["activations"] == row["python_counters"]["heals"] == 1 and
                row["python_counters"]["scopes_created"] == row["python_counters"]["scopes_closed"] == 1 and
                row["python_counters"]["timers_created"] == row["python_counters"]["timers_cleared"] == 1,
                "heal Python bypass or task/timer leak")
        if name in ("original-montage", "paused-world-time"):
            require(row["python_counters"]["completed"] == 1 and row["python_counters"]["timer_callbacks"] == 0,
                    "native Montage completion/cancelled timer not observed")
        if name in ("native-cancel", "native-interrupt"):
            # Native CancelAbility can surface as Montage Interrupted, not
            # OnCancelled; require the actual interruption, not a guessed label.
            require(row["python_counters"]["interrupted"]+row["python_counters"]["cancelled"] == 1,
                    "native task interruption was not observed")
        if name == "active-profile-switch":
            require(row["native_profile_switch_exercised"] == [True, True], "active native ability Profile switch not exercised")
        else:
            require(row["python_counters"]["native_ends"] == 1, "native GAS end-notification cleanup was not actually reached")
        if name == "native-timer":
            require(row["python_counters"]["timer_callbacks"] == 1 and min(row["native_elapsed_seconds"]) >= .99,
                    "native 1s heal timer was shortened/replayed")
        if name == "paused-world-time":
            require(row["native_pause_observed"] == [True, True], "native heal task/timer pause not exercised")
        require(row["inventory_rollbacks"] == [True, True], "heal native inventory identity did not restore")
    final = report["policy_shutdown"]
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and
            final["timers_created"] == final["timers_cleared"] and final["errors"] == [], "heal shutdown retained task/timer")
    return dict(status="passed", bounded_runtime_acceptance=True, cases=len(PLAN), network_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
