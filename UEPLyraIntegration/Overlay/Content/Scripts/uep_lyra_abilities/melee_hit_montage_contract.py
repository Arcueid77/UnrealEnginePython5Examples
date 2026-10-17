"""Native helper values/ABI/ownership; no trace/damage/activation acceptance."""
import argparse
import json
import math
from pathlib import Path

NORMALS = (("zero", (0., 0., 0.)), ("front", (1., 0., 0.)), ("back", (-1., 0., 0.)),
    ("left", (0., 1., 0.)), ("right", (0., -1., 0.)), ("half-positive", (1., .5, 0.)),
    ("half-negative", (1., -.5, 0.)), ("back-half-positive", (-1., .5, 0.)), ("back-half-negative", (-1., -.5, 0.)),
    ("outside-positive", (1., .500000001, 0.)), ("outside-negative", (1., -.500000001, 0.)),
    ("inside-positive", (1., .499999999, 0.)), ("tiny-positive", (1e-12, 0., 0.)),
    ("nonunit", (10., 1., 2.)), ("vertical", (0., 0., 2.)), ("zero-half", (0., .5, 0.)))
PLAN = tuple(dict(target=target, name=name, normal=list(normal)) for target in ("native-identity-control", "actual-player-pawn") for name, normal in NORMALS)
ASSETS = {name: "/Game/Characters/Heroes/Mannequin/Animations/Actions/"+asset+"."+asset for name, asset in (
    ("back", "AM_MM_HitReact_Back_Med_01"), ("front", "AM_MM_HitReact_Front_Hvy_01"),
    ("right", "AM_MM_HitReact_Right_Med_01"), ("left", "AM_MM_HitReact_Left_Med_01"))}


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["actual_granted_primary_instance"] and
        report["actual_ability_class"] == "/ShooterCore/Game/Melee/GA_Melee.GA_Melee_C", "actual Melee native helper report missing")
    for flag in ("fixture_activated_ability", "fixture_granted_ability", "gameplay_state_delivered_by_files", "full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "whole_melee_activation_trace_damage_migrated"):
        require(report[flag] is False, "helper scope overclaimed: "+flag)
    require(report["original_profile_restored"] and report["native_specs_unchanged"] and report["caller_roots"]["created"] == report["caller_roots"]["released"] and
        report["control_actor_destroyed"] and report["quiet_after_helper_calls"], "native Melee helper cleanup missing")
    require(len(report["cases"]) == len(PLAN), "native hit helper matrix incomplete")
    for row, expected in zip(report["cases"], PLAN):
        require(row["input"] == expected and row["native_normal"] == expected["normal"], "native double boundary input was narrowed/changed")
        forward, right = row["native_forward_dot"], row["native_right_dot"]
        require(math.isfinite(forward) and math.isfinite(right) and row["target_path"], "native Actor/dot control missing")
        choice = ("front" if forward > 0. else "back") if -.5 <= right <= .5 else ("left" if right > 0. else "right")
        for name, python in (("blueprint", False), ("python", True)):
            value = row[name]
            require(value["result"] == ASSETS[choice] and value["counters"] == dict(python_calls=int(python), fallback_calls=int(not python), invalid_actor_native_fallback=0),
                "native montage result or selected helper routing differs")
            if python:
                require(value["last"]["forward_dot"] == forward and value["last"]["right_dot"] == right and value["last"]["choice"] == choice,
                    "Python did not use actual native Actor dots")
        require(row["native_state_before"] == row["native_state_after"], "helper changed native gameplay state")
    return dict(status="passed", actual_native_helper_pairs=len(PLAN), actual_actor_and_typed_bp_caller_tested=True,
        activation_trace_damage_tested=False, full_acceptance=False)


def network(reports):
    for peer, role, mode in (("server", 3, "DedicatedServer"), ("A", 2, "Client"), ("B0", 2, "Client")):
        value = reports[peer]; validate(value)
        require(value["peer"] == peer and value["native_role"] == role and value["native_net_mode"] == mode and
            value["helper_two_owner_network_tested"] is True, "actual native Melee helper world/role missing")
    server = reports["server"]
    require(server["server_waited_for_client_process_exit"] and server["all_helper_owners_restored_before_release"] and
        server["other_authority_owner_unchanged"], "authority ownership/restore/exit barrier incomplete")
    require(len({value["run_id"] for value in reports.values()}) == 1 and reports["A"]["player_id"] != reports["B0"]["player_id"] and
        all(server["authority_player_ids"][peer] == reports[peer]["player_id"] for peer in ("A", "B0")), "native two-owner identity mismatch")
    return dict(status="passed", actual_native_helper_pairs_per_world=len(PLAN), actual_worlds=3, actual_owners=2,
        predicted_activation_rpc_trace_damage_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--report"); group.add_argument("--directory"); args = parser.parse_args()
    if args.directory:
        root = Path(args.directory); result = network({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    else: result = validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))
    print(json.dumps(result))
