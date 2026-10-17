"""Actual event dispatch/order witnesses plus the accepted native direction/RPC gates."""
import argparse
import copy
import json
from pathlib import Path
from . import dash_local_direction_contract as local
from .dash_rpc_input_contract import require, same_vector

SCENARIOS = local.SCENARIOS+("crouched-forward",)
STANDALONE_TRIALS = tuple((name, profile) for profile in ("BlueprintFallback", "Python") for name in SCENARIOS)


def activation_row(row, controlled, authority=None, zero=False, crouched=False):
    python = row["profile"] == "Python"; entry = row["activation_entry"]
    require(entry["counters"] == dict(python_calls=int(python), fallback_calls=int(not python)), "actual activation event duplicated/bypassed")
    if not python:
        require(entry["last"] is None, "original activation was reported as a Python event body"); return
    data = entry["last"]
    require(data is not None and data["local_controlled"] is controlled, "actual activation local-control decision differs")
    order = ["local-control"]
    if not controlled:
        require(data["zero_direction"] is data["committed"] is data["crouched_before"] is data["authority"] is None and
            data["uncrouch_called"] is data["rpc_sent"] is data["native_tasks_started"] is False,
            "remote authority did local work before native RPC")
    else:
        order += ["prepare-local", "zero-check"]
        require(data["zero_direction"] is zero, "native zero-direction activation decision differs")
        if zero:
            order += ["cancel"]
            require(data["committed"] is data["crouched_before"] is data["authority"] is None and
                data["uncrouch_called"] is data["rpc_sent"] is data["native_tasks_started"] is False, "zero direction committed or started work")
        else:
            order += ["commit"]
            if crouched: order += ["uncrouch"]
            order += ["authority"]
            if not authority: order += ["send-info"]
            order += ["native-tasks"]
            require(data["committed"] is True and data["crouched_before"] is crouched and data["uncrouch_called"] is crouched and
                data["authority"] is authority and data["rpc_sent"] is (not authority) and data["native_tasks_started"] is True,
                "native commit/crouch/authority/RPC/task activation decision differs")
    require(data["order"] == order, "activation/RPC/native-task order differs")


def standalone(report):
    require(report["actual_activation_event_business_migrated"] is True and report["native_commit_failure_tested"] is False and
        report["native_crouch_restored"] is True and report["crouch_fixture_entry"] == "Character.Crouch", "bounded activation scope/crouch restoration missing")
    require(len(report["cases"]) == len(STANDALONE_TRIALS), "native activation matrix incomplete")
    base = copy.deepcopy(report); base["cases"] = [row for row in base["cases"] if row["name"] in local.SCENARIOS]
    for index, row in enumerate(base["cases"]): row["index"] = index
    local.standalone(base)
    for value in report["restoration"]:
        require(value["control_expected"] == value["control_after"] and local.close_vector(value["control_expected"], value["control_after"]) and
            type(value["native_control_reset_forced"]) is bool, "original native control rotation not exactly restored")
    for index, row in enumerate(report["cases"]):
        require((row["index"], row["name"], row["profile"]) == (index, *STANDALONE_TRIALS[index]), "native activation matrix order differs")
        crouched = row["name"] == "crouched-forward"
        require(row["input"]["native_crouched_before"] is crouched and row["native_crouched_after"] is False, "native crouch/uncrouch observation missing")
        activation_row(row, True, True, zero=row["zero_direction"], crouched=crouched)
        if crouched:
            local.local_row(row)
            for key in ("native_request_accepted", "native_active_observed", "native_root_motion_task_observed", "native_montage_task_observed",
                    "cooldown_repeat_rejected", "native_pose_reset", "native_ability_ended", "specs_unchanged", "native_configuration_unchanged", "health_unchanged"):
                require(row[key] is True, "native crouched activation evidence missing: "+key)
            require(row["native_role"] == 3 and row["actor"] == report["player"] and row["input"]["ai"] is False and row["zero_direction"] is False and
                row["native_tasks_after"] == 0 and row["quiet_ticks"] >= 20 and row["max_motion_distance"] > 1. and row["max_native_speed"] > 0.,
                "native crouched activation/task/quiet proof incomplete")
            python = row["profile"] == "Python"
            require(row["selector_counters"] == dict(python_calls=int(python), fallback_calls=int(not python)) and
                row["rpc_counters"] == dict(python_calls=0, fallback_calls=0), "crouched selector/standalone RPC route differs")
    bp, py = [next(row for row in report["cases"] if (row["name"], row["profile"]) == ("crouched-forward", profile)) for profile in ("BlueprintFallback", "Python")]
    require(bp["chosen"]["montage"] == py["chosen"]["montage"] and same_vector(bp["chosen"]["direction"], py["chosen"]["direction"]) and
        all(local.close_vector(bp["input"][key], py["input"][key]) for key in ("facing", "last_input", "movement", "control_rotation")),
        "original/Python native crouch input/output control differs")
    return dict(status="passed", native_standalone_activation_trials=12, actual_event_overridden=True, native_crouch_tested=True,
        native_commit_failure_tested=False, whole_dash_activation_migrated=False, native_task_business_migrated=False)


def network(reports):
    result = local.network(reports)
    for peer in ("A", "B0"):
        for row in reports[peer]["cases"]: activation_row(row, True, False)
    for row in reports["server"]["cases"]: activation_row(row, False)
    return dict(result, actual_event_overridden=True, native_client_activation_events=8, native_remote_authority_activation_events=8,
        native_commit_failure_tested=False, native_task_business_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--directory"); group.add_argument("--report"); args = parser.parse_args()
    if args.directory:
        root = Path(args.directory); result = network({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    else: result = standalone(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))
    print(json.dumps(result))
