"""Native game-clock boundaries, actual interventions and no late producer work."""
import argparse
import json
import math
from pathlib import Path
from .dash_rpc_input_contract import require
from .dash_activation_contract import activation_row
from .dash_tasks_contract import shutdown, compare_cues

PLAN = ("pause-root", "pause-delay", "montage-interrupt", "native-cancel", "profile-switch-active")
TRIALS = tuple((name, profile) for profile in ("BlueprintFallback", "Python") for name in PLAN)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_net_mode"] == "Standalone" and
        report["lifecycle_interventions_declared"] and report["frame_times_observed"], "native lifecycle report incomplete")
    shutdown(report)
    for flag in ("activation_event_replayed", "rpc_receiver_replayed", "ability_granted_by_fixture", "ability_direction_montage_written_by_fixture",
            "health_written_by_fixture", "raw_velocity_written_by_fixture", "gameplay_state_delivered_by_files", "full_acceptance", "packaged_runtime"):
        require(report[flag] is False, "lifecycle scope overclaimed: "+flag)
    require(len(report["restoration"]) == 2 and all(all(value[key] is True for key in ("profile", "specs", "configuration", "pose_reset", "control_rotation"))
        for value in report["restoration"]) and report["native_crouch_restored"], "native actors not restored after lifecycle controls")
    require(len(report["cases"]) == len(TRIALS), "native lifecycle matrix incomplete")
    for index, value in enumerate(report["cases"]):
        name, profile = TRIALS[index]; python = profile == "Python"; paused = name.startswith("pause-"); switched = name == "profile-switch-active"
        require((value["index"], value["name"], value["profile"]) == (index, name, profile) and value["native_role"] == 3, "lifecycle matrix/role differs")
        for key in ("native_request_accepted", "native_active_observed", "native_root_motion_task_observed", "native_montage_task_observed",
                "cooldown_repeat_rejected", "native_ability_ended", "specs_unchanged", "native_configuration_unchanged", "health_unchanged"):
            require(value[key] is True, "native lifecycle observation missing: "+key)
        require(value["native_tasks_after"] == 0 and value["quiet_ticks"] >= 20 and value["zero_direction"] is False, "native lifecycle task/quiet proof incomplete")
        life = value["lifecycle"]; samples = life["samples"]; action = life["intervention"]
        require(life["quiet_unchanged"] and action is not None and action["active_before"] is True and len(samples) >= 3, "real active intervention missing")
        activation_row(dict(profile=profile, activation_entry=life["activation_at_start"]), True, True)
        times = [sample["time"] for sample in samples]
        require(all(math.isfinite(t) for t in times) and all(b >= a for a, b in zip(times, times[1:])), "native lifecycle game clock nonfinite/reversed")
        quantum = max(b-a for a, b in zip(times, times[1:])); require(0. < quantum <= .15, "native lifecycle frame bound unavailable")
        ended = next((sample["time"] for sample in samples if not sample["active"]), None)
        require(ended is not None, "native inactive transition missing")
        data = value["task_business"]; counts = data["stats"]
        require(data["actual_task_scope_closed"] and data["observer_errors"] == [] and len(data["ui"]) == len(data["cues"]) == 1 and
            data["ui"][0]["instigator"] == data["cues"][0]["target"] == value["actor"], "native lifecycle producer/scope proof missing")
        expected = dict(task_starts=int(python), fallback_task_starts=int(not python), montage_tasks=int(python), root_tasks=int(python),
            scopes_created=int(python), scopes_closed=int(python), ui_messages=int(python), cues=int(python), remote_commits=0,
            root_finished=int(python and paused), native_delays_started=int(python and paused), delay_completed=int(python and paused),
            fallback_delay_completed=int(not python and paused), native_ends=int(python and not switched), fallback_native_ends=int(not python and not switched),
            montage_interrupted=int(python and name == "montage-interrupt"), montage_cancelled=0)
        if python and name == "native-cancel":
            # Native montage stop may synchronously broadcast interruption
            # before its cancellation delegate gets a chance to broadcast.
            interrupted, cancelled = counts.get("montage_interrupted", 0), counts.get("montage_cancelled", 0)
            require(interrupted in (0, 1) and cancelled in (0, 1) and interrupted+cancelled == 1, "native cancellation montage event missing/duplicated")
            expected.update(montage_interrupted=interrupted, montage_cancelled=cancelled)
        require(all(counts.get(key, 0) == count for key, count in expected.items()), "native lifecycle task/callback ownership differs")
        if paused:
            pause = life["pause"]
            require(action["native_entry"] == "GameplayStatics.SetGamePaused" and pause is not None and pause["ticks"] >= 3 and
                pause["unpaused"] and .3 <= pause["wall_seconds"] <= 2. and pause["tasks"]["root"] is (name == "pause-root"), "actual native pause branch missing")
            root_end = next((sample["time"] for sample in samples if not sample["root"]), None)
            require(root_end is not None and abs(root_end-times[0]-.25) <= 2*quantum and abs(ended-times[0]-.55) <= 3*quantum,
                "native root/Delay end game-time boundary differs")
        else:
            entry = {"montage-interrupt": "Character.StopAnimMontage", "native-cancel": "GameplayAbility.K2_CancelAbility", "profile-switch-active": "ue.set_mixin_profile"}[name]
            require(action["native_entry"] == entry and action["root_before"] is True and action["active_after"] is False and
                0. <= ended-action["time"] <= 2*quantum, "native interruption/teardown did not end real active ability")
            if switched: require(action["new_profile"] != profile, "actual Profile did not switch")
    for name in PLAN:
        bp, py = [next(value for value in report["cases"] if (value["name"], value["profile"]) == (name, profile)) for profile in ("BlueprintFallback", "Python")]
        compare_cues(bp["task_business"]["cues"], py["task_business"]["cues"])
    return dict(status="passed", actual_native_lifecycle_trials=len(TRIALS), pause_root_and_original_delay_tested=True,
        native_montage_interrupt_cancel_profile_teardown_tested=True, network_lifecycle_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True); args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
