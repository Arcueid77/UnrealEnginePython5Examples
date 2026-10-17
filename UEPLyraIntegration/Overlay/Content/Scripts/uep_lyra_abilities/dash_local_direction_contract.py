"""Local direction ownership in real native activation, not a whole-Dash gate."""
import argparse
import json
import math
from pathlib import Path
from .dash_rpc_input_contract import validate as rpc, require, same_vector

SCENARIOS = ("no-input", "forward", "left", "camera-pitch", "ai-navigation")
STANDALONE_TRIALS = tuple((name, profile) for profile in ("BlueprintFallback", "Python") for name in SCENARIOS)


def close_vector(a, b, tolerance=.002):
    return len(a) == len(b) == 3 and all(math.isfinite(x) and math.isfinite(y) and abs(x-y) <= tolerance for x, y in zip(a, b))


def standalone(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_net_mode"] == "Standalone",
        "native standalone direction report incomplete")
    for key in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "enhanced_input_tested",
            "whole_dash_activation_migrated", "dash_task_business_migrated", "movement_parity_certified", "activation_event_replayed",
            "rpc_receiver_replayed", "ability_granted_by_fixture", "ability_direction_montage_written_by_fixture", "health_written_by_fixture",
            "raw_velocity_written_by_fixture", "gameplay_state_delivered_by_files"):
        require(report[key] is False, "unsupported local direction scope: "+key)
    require(report["actual_ability_class"] == "/ShooterCore/Game/Dash/GA_Hero_Dash.GA_Hero_Dash_C" and
        report["actual_granted_primary_instances"] is True and report["player"] != report["ai"] and report["ai_controller"], "actual distinct player/AI missing")
    require(report["request_entry"] == "ASC.TryActivateAbilityByClass" and report["movement_intent_entry"] == "Pawn.AddMovementInput" and
        report["fixture_control_rotation_entry"] == "Controller.SetControlRotation" and report["fixture_pose_entry"] == "Actor.K2_TeleportTo",
        "native activation/declared fixture entry differs")
    require(len(report["restoration"]) == 2 and all(all(row[key] is True for key in ("profile", "specs", "configuration", "pose_reset", "control_rotation"))
        for row in report["restoration"]), "player/AI original state restoration incomplete")
    require(len(report["cases"]) == len(STANDALONE_TRIALS), "standalone direction matrix incomplete")
    for index, row in enumerate(report["cases"]):
        name, profile = STANDALONE_TRIALS[index]; python = profile == "Python"; ai = name == "ai-navigation"
        require((row["index"], row["name"], row["profile"]) == (index, name, profile) and row["native_role"] == 3,
            "native standalone direction order/role differs")
        require(row["actor"] == report["ai" if ai else "player"] and row["input"]["ai"] is ai, "actual AI branch not exercised")
        for key in ("native_pose_reset", "native_request_accepted", "native_ability_ended", "specs_unchanged", "native_configuration_unchanged", "health_unchanged"):
            require(row[key] is True, "native standalone observation missing: "+key)
        require(row["quiet_ticks"] >= 20 and row["native_tasks_after"] == 0, "native task/end/quiet proof incomplete")
        local_row(row)
        expected = dict(python_calls=int(python), fallback_calls=int(not python))
        require(row["selector_counters"] == expected and row["rpc_counters"] == dict(python_calls=0, fallback_calls=0),
            "standalone selector/RPC route differs")
        inputs = row["input"]
        require(all(close_vector(inputs[key], inputs[key]) for key in ("facing", "last_input", "movement", "raw_last_input", "point", "control_rotation")),
            "nonfinite native input witness")
        if python:
            data = row["local_direction"]["last"]
            require(data["ai"] is ai and all(close_vector(data[key], inputs[key]) for key in ("facing", "last_input", "movement")),
                "Python did not use the independently observed native inputs")
        if ai:
            require(type(inputs["projection_succeeded"]) is bool and inputs["projected"] is not None and
                close_vector(inputs["movement"], inputs["last_input"]), "actual native AI projection result missing")
            if python: require(data["projection_succeeded"] is inputs["projection_succeeded"] and close_vector(data["projected"], inputs["projected"]),
                "Python replaced the original AI native projection output")
        else:
            require(inputs["projected"] is inputs["projection_succeeded"] is None, "player invented AI query")
            if name == "no-input": require(close_vector(inputs["raw_last_input"], [0., 0., 0.]), "no-input case actually had native input")
            if name == "camera-pitch":
                require(row["control_pitch_fixture"] == 20. and abs(inputs["control_rotation"][1]-20.) <= .002 and abs(inputs["movement"][2]) > .1,
                    "camera pitch fixture did not reach actual native camera")
                if python: require(data["bias"] is True and abs(row["chosen"]["direction"][2]) > .1, "camera-pitch branch was not selected")
        zero = all(abs(value) <= .0001 for value in row["chosen"]["direction"])
        require(row["zero_direction"] is zero, "zero/cancel branch observation contradicts native direction")
        if zero:
            require(row["immediate_active"] is False and row["native_active_observed"] is False and row["native_root_motion_task_observed"] is False and
                row["native_montage_task_observed"] is False and row["cooldown_repeat_rejected"] is None, "zero direction did not take original early cancellation")
        else:
            require(all(row[key] is True for key in ("native_active_observed", "native_root_motion_task_observed", "native_montage_task_observed", "cooldown_repeat_rejected")) and
                row["max_motion_distance"] > 1. and row["max_native_speed"] > 0., "native nonzero Dash tasks/motion/cooldown missing")
    for name in SCENARIOS:
        bp, py = [next(row for row in report["cases"] if (row["name"], row["profile"]) == (name, profile)) for profile in ("BlueprintFallback", "Python")]
        require(bp["chosen"]["montage"] == py["chosen"]["montage"] and close_vector(bp["chosen"]["direction"], py["chosen"]["direction"]) and
            bp["zero_direction"] is py["zero_direction"], "BP/Python native standalone payload/cancel differs")
        require(all(close_vector(bp["input"][key], py["input"][key]) for key in ("facing", "last_input", "movement", "control_rotation")),
            "BP/Python standalone native input control differs")
    return dict(status="passed", native_standalone_trials=len(STANDALONE_TRIALS), ai_navigation_tested=True,
        standalone_camera_noinput_tested=True, whole_dash_activation_migrated=False, movement_parity_certified=False)


def local_row(row, require_changed=False):
    python = row["profile"] == "Python"; value = row["local_direction"]
    require(value["counters"] == dict(python_calls=int(python), fallback_calls=int(not python)), "local direction route duplicated/bypassed")
    require(value["stored"] == row["chosen"], "local preparation fields differ from actual native activation fields")
    if python:
        data = value["last"]
        require(data is not None and data["montage"] == row["chosen"]["montage"] and same_vector(data["direction"], row["chosen"]["direction"]),
            "Python local direction result not stored in actual ability")
        require(same_vector(data["direction"], data["movement"] if data["bias"] else data["last_input"]), "original forward-bias direction choice differs")
        if not data["ai"]: require(data["projected"] is data["projection_succeeded"] is None, "player branch invented AI navigation")
        else: require(data["projected"] is not None and type(data["projection_succeeded"]) is bool, "actual AI native projection output missing")
        if require_changed:
            require(not same_vector(value["before"]["direction"], value["stored"]["direction"]) and
                value["before"]["montage"] != value["stored"]["montage"], "matching stale fields could mask missing local Python stores")
    else: require(value["last"] is None, "native fallback reported a Python local computation")


def network(reports):
    result = rpc(reports)
    for peer in ("A", "B0"):
        for row in reports[peer]["cases"]:
            local_row(row, require_changed=row["profile"] == "Python")
            if row["profile"] == "Python": require(row["local_direction"]["last"]["ai"] is False, "native player took AI direction branch")
    for row in reports["server"]["cases"]:
        require(row["local_direction_counters"] == dict(python_calls=0, fallback_calls=0), "remote authority incorrectly prepared local direction")
    return dict(result, native_local_direction_preparations=8, remote_authority_local_preparations=0, ai_navigation_tested=False,
        standalone_camera_noinput_tested=False, whole_dash_activation_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); args_group = parser.add_mutually_exclusive_group(required=True)
    args_group.add_argument("--directory"); args_group.add_argument("--report"); args = parser.parse_args()
    if args.directory:
        root = Path(args.directory); result = network({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    else: result = standalone(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))
    print(json.dumps(result))
