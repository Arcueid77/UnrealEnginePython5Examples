"""Actual Melee ASC/montage lifecycle; trace/damage remains a later gate."""
import argparse
import json
from pathlib import Path
from .melee_hit_montage_contract import require

TRIALS = tuple((name, profile) for profile in ("BlueprintFallback", "Python") for name in ("natural", "interrupt", "cancel", "profile-switch"))


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["actual_granted_primary_instance"] and report["native_role"] == 3,
        "actual native Melee activation report incomplete")
    require(report["request_entry"] == "ASC.TryActivateAbilityByClass" and report["actual_ability_class"] == "/ShooterCore/Game/Melee/GA_Melee.GA_Melee_C", "native Melee request/type changed")
    for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_event_replayed", "task_callbacks_replayed", "ability_granted_by_fixture", "health_or_raw_velocity_written", "trace_damage_business_migrated"):
        require(report[flag] is False, "Melee activation scope overclaimed: "+flag)
    for key in ("profile_restored", "specs_unchanged", "config_unchanged", "native_pose_restored"):
        require(report[key] is True, "native activation cleanup missing: "+key)
    require(report["native_control_restoration"]["control_rotation"] and report["shutdown"]["active_count"] == 0 and
        report["shutdown"]["scopes_created"] == report["shutdown"]["scopes_closed"] and report["shutdown"]["errors"] == [], "Melee scope/control cleanup leaked")
    require(len(report["cases"]) == len(TRIALS), "native Melee activation matrix incomplete")
    for index, value in enumerate(report["cases"]):
        name, profile = TRIALS[index]; python = profile == "Python"; switched = name == "profile-switch"
        require((value["index"], value["name"], value["profile"]) == (index, name, profile), "native Melee matrix order differs")
        for key in ("native_pose_reset", "native_request_accepted", "native_repeat_rejected", "native_active_observed", "native_montage_task_observed",
                "native_ended", "actual_scope_closed", "all_pawn_health_unchanged", "specs_unchanged", "config_unchanged"):
            require(value[key] is True, "native Melee observation missing: "+key)
        require(value["equipment"]["weapon"] and value["equipment"]["montage"] == value["native_initial_montage"] and
            value["native_tasks_after"] == 0 and value["quiet_ticks"] >= 20 and value["native_root_task_observed"] is False,
            "actual first-equipment montage/no-hit task proof missing")
        counts = value["stats"]; expected = dict(activations=int(python), fallback_activations=int(not python), commits=int(python), cast_failed=0,
            montage_tasks=int(python), authority_trace_entries=int(python), scopes_created=int(python), scopes_closed=int(python),
            native_ends=int(python and not switched), fallback_native_ends=int(not python and not switched))
        require(all(counts.get(key, 0) == count for key, count in expected.items()), "native Melee activation ownership differs")
        callbacks = [counts.get(key, 0) for key in ("completed", "blend_out", "interrupted", "cancelled")]
        require(all(value in (0, 1) for value in callbacks) and sum(callbacks) == int(python and not switched), "native montage event missing/duplicated")
        if name != "natural":
            action = value["intervention"]
            require(action is not None and action["active_before"] and action["active_after"] is False and .07 <= action["time"] < 1., "real active montage intervention missing")
            if switched: require(action["new_profile"] != profile, "actual active Profile did not change")
    for name in ("natural", "interrupt", "cancel", "profile-switch"):
        values = [value for value in report["cases"] if value["name"] == name]
        require(values[0]["equipment"] == values[1]["equipment"], "native BP/Python equipment control differs")
    return dict(status="passed", actual_native_melee_activation_trials=len(TRIALS), montage_lifecycle_scope_tested=True,
        trace_damage_business_migrated=False, multiplayer_activation_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True); args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
