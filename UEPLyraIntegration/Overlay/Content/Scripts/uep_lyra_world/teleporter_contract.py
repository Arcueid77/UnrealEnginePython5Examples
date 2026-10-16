"""Bounded physical teleporter proof, separate from network/visible acceptance."""
import argparse
import json
import math
from pathlib import Path

PLAN = ("default-launch", "no-launch", "free-direction", "relative-offset",
        "relative-upper", "relative-lower", "no-controller")
UNSUPPORTED = ("full_acceptance", "network_acceptance", "packaged_runtime", "player_modified",
               "collision_handler_called_by_probe", "native_teleport_called_by_probe",
               "native_launch_called_by_probe", "velocity_written_after_entry", "audible_parity_tested",
               "grenade_runtime_tested", "multi_destination_runtime_tested")


def require(value, message):
    if not value:
        raise RuntimeError(message)


def equal(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b) < .01
    return a == b


def validate(report):
    require(report["status"] == "passed", "teleporter native report failed")
    require(all(report[k] is False for k in UNSUPPORTED), "unsupported teleporter acceptance claim")
    require(report["native_physics_fixture_configured"] is True and report["native_collision_pairs"] == len(PLAN)*2,
            "native teleporter physical entry evidence missing")
    require(report["actors_created"] == report["actors_destroyed"] == 54 and
            report["scopes_created"] == report["scopes_closed"] == 14, "teleporter fixture cleanup incomplete")
    require(report["original_replication_flag"] is False and report["original_signatures_preserved"] is True,
            "teleporter original class transport differs")
    require(len(report["cases"]) == len(PLAN), "teleporter native matrix incomplete")
    for row, name in zip(report["cases"], PLAN):
        require(row["name"] == name and row["passed"] is True and row["same_class"] is True,
                "teleporter case identity differs")
        require(equal(row["python"], row["blueprint"]), "teleporter BP/Python differs")
        for result in (row["blueprint"], row["python"]):
            require(result["events"].count("begin") == 1 and result["events"].count("end") == 1,
                    "teleporter physical begin/end missing or duplicated")
            require(result["destination_selected"] is True and result["receiving_pawn"] is True and
                    result["class_preserved"] is True and result["receiver_box_destroyed"] is True,
                    "teleporter target/type/receiver differs")
            require(result["position_error"] < .01 and result["rotation_error"] < .01 and
                    result["control_error"] < .01 and result["velocity_error"] < .01,
                    "native teleporter transform/control/launch differs")
            require(result["launched"] is (name != "no-launch"), "teleporter launch flag differs")
        count = row["python_counters"]
        require(count["constructions"] == 2 and count["begins"] == 1 and count["destinations"] == 1 and
                count["character_entries"] == 1 and count["teleports"] == 1 and count["pawn_audio"] == 1,
                "teleporter Python business bypassed or replayed")
        require(count["launches"] == int(name != "no-launch") and
                count["rotations"] == int(name not in ("free-direction", "no-controller")),
                "teleporter Python native call count differs")
    require(report["policy_shutdown"]["errors"] == [], "teleporter Python policy raised")
    return dict(status="passed", bounded_runtime_acceptance=True, cases=len(PLAN), network_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
