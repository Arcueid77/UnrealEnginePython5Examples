"""Fail-closed launcher native proof; host models alone cannot satisfy this."""
import argparse
import json
import math
from pathlib import Path

PLAN = (("parent-default", "parent", False), ("push-forward", "push", True),
        ("push-target", "push", True), ("up-vertical", "up", True),
        ("push-fall-filter", "push", False), ("up-fall-filter", "up", False),
        ("push-ai-filter", "push", False), ("up-ai-filter", "up", False))

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def equal(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b) < .01
    return a == b

def validate(report):
    require(report["status"] == "passed", "launcher native report failed")
    for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "collision_handler_called_by_probe",
                 "native_launch_called_by_probe", "velocity_written_after_entry", "player_modified", "cue_visual_parity_tested"):
        require(report[flag] is False, "unsupported launcher claim: "+flag)
    require(report["native_physics_fixture_configured"] is True and report["native_collision_pairs"] == 16,
            "native launcher collision/physics evidence missing")
    require(report["actors_created"] == report["actors_destroyed"] == 36 and report["scopes_created"] == report["scopes_closed"] == 16,
            "launcher native fixture cleanup incomplete")
    require(report["original_replication_flags"] == [False]*3 and report["rpc_signature_preserved"] is True,
            "launcher native type/replication/RPC differs")
    require(len(report["cases"]) == len(PLAN), "launcher native matrix incomplete")
    for row, (name, kind, launch) in zip(report["cases"], PLAN):
        require(row["name"] == name and row["passed"] is True and row["same_class"] is True,
                "launcher native case identity differs")
        require(equal(row["python"], row["blueprint"]), "launcher original BP/Python differs")
        for result in (row["python"], row["blueprint"]):
            require(result["collision_begins"] == 1 and result["pawn_selected"] is True and result["launched"] is launch,
                    "launcher collision/selected Pawn/native launch differs")
            require(result["velocity_error"] < .01 and result["class_preserved"] is True,
                    "launcher native velocity/type differs")
            if "fall" in name:
                require(result["fall_condition_observed"] is True, "launcher falling filter was not actually exercised")
            if "ai" in name:
                require(result["native_ai_controller"] is True, "launcher native AI guard not exercised")
        counts = row["python_counters"]
        require(counts["constructions"] == 1 and counts["begins"] == 1 and counts["launches"] == int(launch),
                "launcher Python business bypassed/replayed")
        require(counts[kind+"_overlaps"] == (0 if "ai" in name else 1), "launcher Python wrong child dispatch")
        require(counts["cues"] == int(launch or kind == "parent"), "launcher Python emitted cue for rejected launch")
    require(report["policy_shutdown"]["errors"] == [], "launcher Python policy raised")
    return {"status": "passed", "bounded_runtime_acceptance": True, "cases": len(PLAN), "network_acceptance": False}

if __name__ == "__main__":
    parser = argparse.ArgumentParser();parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
