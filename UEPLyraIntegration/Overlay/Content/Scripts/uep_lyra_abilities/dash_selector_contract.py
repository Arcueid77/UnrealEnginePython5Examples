"""Typed original BP vs Python helper outputs; not Dash activation or movement."""
import argparse
import json
import math
from pathlib import Path
from .auto_respawn_helpers_contract import require

CLASS = "/ShooterCore/Game/Dash/GA_Hero_Dash.GA_Hero_Dash_C"
FIELDS = ("Dash_Fwd Montage", "Dash_Bwd Montage", "Dash_Left Montage", "Dash_Right Montage")


def vector(yaw, scale=1., z=0.): return [math.cos(math.radians(yaw))*scale, math.sin(math.radians(yaw))*scale, z]


def plan():
    angles = sorted(set(range(-180, 181, 15))|{-135.001, -134.999, -45.001, -44.999, 44.999, 45.001, 134.999, 135.001})
    rows = [dict(name="yaw-"+str(yaw), facing=[1., 0., 0.], movement=vector(yaw), null_field=None) for yaw in angles]
    rows += [dict(name=name, facing=facing, movement=movement, null_field=None) for name, facing, movement in (
        ("zero-both", [0., 0., 0.], [0., 0., 0.]), ("zero-movement", [1., 0., 0.], [0., 0., 0.]),
        ("rotated-facing", vector(72.), vector(162.)), ("scaled-directions", vector(-50., 3.), vector(40., 8.)),
        ("pitched-directions", vector(30., 2., 7.), vector(-60., 4., -8.)))]
    rows += [dict(name="null-"+str(index), facing=[1., 0., 0.], movement=vector(yaw), null_field=field)
        for index, (field, yaw) in enumerate(zip(FIELDS, (0., 180., -90., 90.)))]
    return rows


PLAN = plan()


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["dash_selector_business_migrated"] is True,
        "Dash selector native report incomplete")
    for key in ("dash_activation_business_migrated", "dash_rpc_movement_tested", "fixture_activated_ability", "fixture_granted_ability",
            "gameplay_state_delivered_by_files", "full_acceptance", "packaged_runtime", "physical_input_tested"):
        require(report[key] is False, "unsupported Dash helper scope: "+key)
    for key in ("actual_granted_primary_instance", "ability_was_not_rooted", "original_profile_restored", "instance_configuration_restored",
            "cdo_configuration_unchanged", "native_specs_unchanged", "quiet_after_helper_calls"):
        require(report[key] is True, "Dash helper ownership/configuration differs: "+key)
    require(report["actual_ability_class"] == CLASS and report["caller_roots"] == dict(created=1, released=1) and len(report["cases"]) == len(PLAN),
        "Dash typed caller/class/matrix differs")
    seen = set()
    for row, expected in zip(report["cases"], PLAN):
        require(row["input"] == expected and row["configuration_restored"] is True and row["native_state_before"] == row["native_state_after"],
            "Dash input order/native gameplay state/configuration changed")
        bp, py = row["blueprint"], row["python"]
        require(bp["profile"] == "BlueprintFallback" and py["profile"] == "Python" and bp["result"] == py["result"] and
            bp["counters"] == dict(python_calls=0, fallback_calls=1) and py["counters"] == dict(python_calls=1, fallback_calls=0),
            "native second-BP Dash output/Profile/route differs")
        choice = py["last"]; index = 0 if choice["magnitude"] < 45. else 1 if choice["magnitude"] > 135. else 2 if choice["yaw"] < 0. else 3
        require(math.isfinite(choice["yaw"]) and math.isfinite(choice["magnitude"]) and choice["field"] == FIELDS[index] and
            choice["forward"] is (index == 0) and py["result"]["BiasForwardMovement"] is (index == 0) and
            py["result"]["DirectionalMontage"] == (None if expected["null_field"] == FIELDS[index] else report["original_montages"][FIELDS[index]]),
            "native Dash direction/bias/configured montage differs")
        seen.add(choice["field"])
    require(seen == set(FIELDS), "Dash native matrix did not cover all directions")
    return dict(status="passed", native_bp_python_selector_pairs=len(PLAN), actual_granted_primary_instance=True, dash_activation_rpc_movement_tested=False)


def network(reports):
    for peer, report in reports.items():
        validate(report); require(report["peer"] == peer and report["native_role"] == (3 if peer == "server" else 2), "Dash native peer/role differs")
    server = reports["server"]
    require(server["server_waited_for_client_process_exit"] is True and server["all_helper_owners_restored_before_release"] is True and
        server["other_authority_owner_unchanged"] is True, "Dash native two-owner release/isolation gate missing")
    require(len({reports[peer]["player_id"] for peer in ("A", "B0")}) == 2 and len({report["run_id"] for report in reports.values()}) == 1,
        "Dash two actual owners/run identity missing")
    return dict(status="passed", native_bp_python_selector_pairs_per_world=len(PLAN), peer_worlds=3, actual_owners=2, dash_activation_rpc_movement_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--report"); group.add_argument("--directory"); args = parser.parse_args()
    if args.directory:
        root = Path(args.directory); result = network({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})
    else: result = validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))
    print(json.dumps(result))
