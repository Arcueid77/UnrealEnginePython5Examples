"""Native Emote evidence gate; does not accept callback replay or fake input."""
import argparse
import json
import math
from pathlib import Path

PLAN = ("natural-duration", "native-movement", "native-crouch", "crouched-entry",
        "native-cancel", "external-native-end", "active-profile-switch", "repeat", "paused-world-time")
FALSE_CLAIMS = ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested",
    "activation_handler_replayed", "movement_handler_replayed", "task_callbacks_replayed", "animation_assets_modified",
    "movement_velocity_written", "native_rpc_bypassed", "foreign_listener_parity_claimed")


def require(value, message):
    if not value:
        raise RuntimeError(message)


def validate(report, plan=PLAN):
    require(report["status"] == "passed" and report["error"] is None, "Emote did not pass")
    for field in FALSE_CLAIMS:
        require(report[field] is False, "unsupported Emote claim: " + field)
    require(report["player_movement_input_tested"] is False, "physical/player movement input was not exercised")
    if "native-movement" in plan:
        require(report["native_external_movement_fixture"] is True and report["native_movement_producer"] == "Character.LaunchCharacter",
                "native external-movement fixture source differs")
    else:
        require(report["native_external_movement_fixture"] is False, "network external movement was not exercised")
    for field in ("native_existing_spec_input_activation", "original_player_restored", "original_profile_restored",
                  "original_widget_grant_preserved", "fixture_observers_closed", "original_cdo_untouched"):
        require(report[field] is True, "Emote restoration/source proof missing: " + field)
    require([row["name"] for row in report["cases"]] == list(plan), "Emote native matrix incomplete")
    duration = report["native_montage_length"]
    require(type(duration) in (float, int) and math.isfinite(duration) and duration > 5., "original native Emote montage missing")
    for case in report["cases"]:
        for side in ("blueprint", "python"):
            row = case[side]
            for field in ("native_type_preserved", "native_source_preserved", "profile_selected", "native_montage_observed",
                          "native_montage_stopped", "widget_grant_preserved", "player_restored", "ability_ended"):
                require(row[field] is True, "Emote native observation missing: " + field)
            require(row["input_injections"] >= 1 and row["native_tasks_during"] == 1 and row["native_tasks_after"] == 0,
                    "Emote native input/task proof incomplete")
            require(row["foreign_calls_before_intervention"] >= 2, "foreign movement subscriber was never live")
            expected_events = ([] if case["name"] in ("external-native-end", "active-profile-switch") else
                               ["OnInterrupted"] if case["name"] in ("native-movement", "native-crouch", "native-cancel") else ["OnCompleted"])
            require(row["native_montage_events"] == expected_events and row["native_end_callbacks"] == len(expected_events),
                    "Emote native montage callback route duplicated/missing")
            if case["name"] in ("natural-duration", "crouched-entry", "repeat", "paused-world-time"):
                require(row["native_montage_events"] == ["OnCompleted"], "native Emote completion missing")
                require(duration - .3 <= row["active_game_seconds"] <= duration + 1., "native Emote duration differs")
            if case["name"] == "native-movement":
                require(row["native_velocity_observed"] > 0., "native LaunchCharacter did not actually move")
            if case["name"] == "native-crouch":
                require(row["native_crouch_observed"], "native crouch interruption not observed")
            if case["name"] == "crouched-entry":
                require(row["crouched_before_activation"] and row["native_uncrouch_observed"], "native entry uncrouch missing")
            if case["name"] == "active-profile-switch":
                require(row["profile_teardown_ended_ability"], "Emote Profile handoff did not native-End")
            if case["name"] == "paused-world-time":
                require(row["native_pause_observed"] and row["active_during_pause"], "native Emote clock/montage did not pause")
        row, counts = case["python"], case["python"]["counters"]
        require(counts["activations"] == counts["tasks_created"] == 1, "native input bypassed Python Emote")
        require(counts["scopes_created"] == counts["scopes_closed"] == 2, "Emote task/movement scopes unbalanced")
        require(row["no_late_python_movement"] and row["foreign_calls_after_end"] >= 2,
                "Python Emote removed foreign callbacks or retained its own after End")
        if case["name"] in ("native-movement", "native-crouch"):
            require(counts["movement_stops"] == counts["montage_interrupted"] == 1,
                    "actual movement did not route through Python to native montage interruption")
            require(case["blueprint"]["foreign_calls_after_end"] == 0,
                    "original BP ClearAll foreign-listener difference was not actually reproduced")
        if case["name"] == "crouched-entry":
            require(counts["uncrouches"] == 1, "Python skipped original entry uncrouch")
    stats = report["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [],
            "Emote policy shutdown leak/error")
    require(report["fixture_scopes_created"] == report["fixture_scopes_closed"] == len(plan) * 2,
            "Emote source/foreign-listener fixture leaked")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(plan),
                original_clear_all_foreign_difference_tested="native-movement" in plan, native_enhanced_input_activation=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
