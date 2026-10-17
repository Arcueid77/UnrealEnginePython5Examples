"""Native predicted activation -> reliable SendInfo -> exactly selected stores."""
import argparse
import json
import math
from pathlib import Path
from .dash_selector_contract import CLASS

PLAN = ("forward", "left")
TRIALS = tuple((name, profile) for profile in ("BlueprintFallback", "Python") for name in PLAN)
PEERS = ("A", "B0")


def require(good, message):
    if not good: raise RuntimeError(message)


def same_vector(a, b):
    return len(a) == len(b) == 3 and all(math.isfinite(x) and math.isfinite(y) and abs(x-y) <= .0001 for x, y in zip(a, b))


def counts(value, python, received):
    require(value == dict(python_calls=int(python and received), fallback_calls=int(not python and received)), "Dash RPC store route duplicated/bypassed")


def client(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_role"] == 2 and report["native_net_mode"] == "Client",
        "Dash actual owner/native client report incomplete")
    for key in ("rpc_receiver_replayed", "activation_event_replayed", "ability_granted_by_fixture", "ability_direction_montage_written_by_fixture",
            "health_written_by_fixture", "raw_velocity_written_by_fixture", "gameplay_state_delivered_by_files", "physical_input_tested",
            "enhanced_input_tested", "whole_dash_activation_migrated", "dash_task_business_migrated", "movement_parity_certified", "full_acceptance", "packaged_runtime"):
        require(report[key] is False, "unsupported Dash RPC scope: "+key)
    require(report["request_entry"] == "ASC.TryActivateAbilityByClass" and report["movement_intent_entry"] == "Pawn.AddMovementInput" and
        report["actual_ability_class"] == CLASS and report["actual_granted_primary_instance"] is True and
        report["profile_restored"] and report["specs_unchanged"] and report["native_configuration_unchanged"], "Dash native request/configuration/cleanup proof missing")
    require(len(report["cases"]) == len(TRIALS), "Dash native owner matrix incomplete")
    for index, row in enumerate(report["cases"]):
        name, profile = TRIALS[index]; python = profile == "Python"
        require((row["index"], row["name"], row["profile"]) == (index, name, profile), "Dash owner matrix order differs")
        for key in ("native_request_accepted", "native_active_observed", "native_root_motion_task_observed", "native_montage_task_observed",
                "native_ability_ended", "quiet_after_end", "cooldown_repeat_rejected", "native_configuration_unchanged", "specs_unchanged"):
            require(row[key] is True, "Dash actual owner observation missing: "+key)
        require(row["native_tasks_after"] == 0 and row["max_motion_distance"] > 1. and row["max_native_speed"] > 0. and
            row["chosen"]["montage"] is not None and same_vector(row["chosen"]["direction"], row["chosen"]["direction"]), "Dash owner native task/motion/payload differs")
        counts(row["rpc_counters"], python, False)
        require(row["selector_counters"] == dict(python_calls=int(python), fallback_calls=int(not python)), "Dash owner selector was not the selected route")
    by_case = {(row["name"], row["profile"]): row["chosen"] for row in report["cases"]}
    for name in PLAN:
        bp, py = [by_case[name, profile] for profile in ("BlueprintFallback", "Python")]
        require(bp["montage"] == py["montage"] and same_vector(bp["direction"], py["direction"]), "BP/Python native input control differs")
    require(not same_vector(by_case["forward", "Python"]["direction"], by_case["left", "Python"]["direction"]) and
        by_case["forward", "Python"]["montage"] != by_case["left", "Python"]["montage"], "Native direction/montage controls were not distinct")
    return dict(status="passed", native_owner_trials=len(report["cases"]))


def validate(reports):
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["server_waited_for_client_process_exit"] and
        server["original_profiles_restored"] and server["specs_and_configuration_preserved"] and server["native_playing_gate"]["native_playing_phase"],
        "Dash native server cleanup/exit proof incomplete")
    require(server["rpc_receiver_replayed"] is server["activation_event_replayed"] is server["native_rpc_bypassed"] is
        server["gameplay_state_delivered_by_files"] is server["whole_dash_activation_migrated"] is server["full_acceptance"] is False,
        "Dash native ingress/partial scope overclaimed")
    require(len(set(server["player_ids"].values())) == 2 and set(server["player_ids"]) == set(PEERS), "Dash requires two actual native owners")
    for peer in PEERS:
        report = reports[peer]; client(report)
        require((report["peer"], report["run_id"], report["player_id"]) == (peer, server["run_id"], server["player_ids"][peer]), "Dash native owner identity differs")
    expected = [(peer, index) for peer in PEERS for index in range(len(TRIALS))]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "Dash native authority RPC matrix incomplete")
    for row in server["cases"]:
        peer, index = row["target"], row["index"]; owner = reports[peer]["cases"][index]
        require(row["native_role"] == 3 and row["actual_ability_class"] == CLASS and row["profile"] == owner["profile"] and row["name"] == owner["name"] and
            row["actual_receiver_authority"] is True and row["native_active_observed"] and row["native_root_motion_task_observed"] and
            row["native_montage_task_observed"] and row["native_tasks_after"] == 0 and row["native_ability_ended"] and
            row["foreign_owner_unchanged"] and row["quiet_after_end"] and row["native_configuration_unchanged"] and row["specs_unchanged"],
            "Dash actual authority RPC/native continuation/lifetime proof missing")
        python = row["profile"] == "Python"
        counts(row["rpc_counters"], python, True)
        require(same_vector(row["received"]["direction"], row["stored"]["direction"]) and
            same_vector(row["received"]["direction"], owner["chosen"]["direction"]) and
            row["received"]["montage"] == row["stored"]["montage"] == owner["chosen"]["montage"] and row["client"]["row"] == owner,
            "Native RPC payload/original-or-Python stores/independent owner observation differs")
        if python:
            require(not same_vector(row["stores_before_rpc"]["direction"], row["received"]["direction"]) and
                row["stores_before_rpc"]["montage"] != row["received"]["montage"], "Python stores could be masked by matching stale native values")
    resets = server["native_pose_resets"]
    require(len(resets) == len(expected) and all(row["native_api"] == "K2_TeleportTo" and row["succeeded"] for row in resets),
        "Declared collision-checked native pose-reset fixture missing")
    return dict(status="passed", actual_native_server_rpc_trials=len(expected), actual_owners=2, python_remote_store_business_migrated=True,
        native_rpc_bypassed=False, whole_dash_activation_migrated=False, movement_parity_certified=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
