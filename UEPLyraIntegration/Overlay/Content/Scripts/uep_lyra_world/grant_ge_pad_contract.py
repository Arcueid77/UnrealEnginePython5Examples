"""Native instant-heal and retained Timeline proof, not networking/release."""
import math
CASES = ("construction", "native-tick", "physical-instant-heal", "physical-end-charge", "native-timeline-progress", "native-finish")

def equal(left, right):
    if type(left) in (int, float) and type(right) in (int, float):
        return math.isfinite(left) and math.isfinite(right) and abs(left-right) < .1
    if type(left) is dict and type(right) is dict:
        return set(left) == set(right) and all(equal(left[key], right[key]) for key in left)
    if type(left) is list and type(right) is list:
        return len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    return type(left) is type(right) and left == right

def validate(report):
    if report.get("status") != "passed" or report.get("error") is not None:
        raise RuntimeError("grant-GE native lane incomplete")
    for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "manual_lifecycle_event", "handler_called_by_probe",
                 "timeline_driven_by_probe", "attributes_written_by_probe", "culture_switch_tested"):
        if report.get(flag) is not False:
            raise RuntimeError("unsupported grant-GE claim: "+flag)
    if report.get("full_default_duration_tested") is not True or report.get("fixture_duration") != 15.0 or report.get("original_default_duration") != 15.0:
        raise RuntimeError("native default cooldown not certified")
    if report.get("fixture_scope_closed") is not True or report.get("effect_duration_policy") != 0:
        raise RuntimeError("native instant-GE/collision scope evidence missing")
    if report.get("native_player_restored") is not True or report.get("actors_created") != 2 or report.get("actors_destroyed") != 2:
        raise RuntimeError("grant-GE native cleanup missing")
    if [row.get("name") for row in report.get("cases", [])] != list(CASES):
        raise RuntimeError("grant-GE cases differ")
    for row in report["cases"]:
        if row.get("passed") is not True or row.get("same_class") is not True or not equal(row["python"], row["blueprint"]):
            raise RuntimeError("grant-GE BP/Python differs")
    for side in ("python", "blueprint"):
        values = {row["name"]: row[side] for row in report["cases"]}
        if abs(values["native-tick"]["yaw_rate"]-50.0) >= .1:
            raise RuntimeError("native Tick rotation missing")
        if report.get("native_baseline_health") != 75.0 or not values["physical-instant-heal"]["health"] > 75.0 or values["physical-instant-heal"]["mesh_hidden"] is not True:
            raise RuntimeError("native instant-heal pickup missing")
        if values["physical-end-charge"] != {"active": False, "text": "Charging", "tick": False, "light": False, "mesh_hidden": True}:
            raise RuntimeError("native end/charge behavior differs")
        if not all(values["native-timeline-progress"].values()):
            raise RuntimeError("native Timeline was not observed while actor Tick paused")
        final = values["native-finish"]
        if not (final["active"] and final["tick"] and final["light"] and not final["mesh_hidden"] and final["percent"] == 0.0):
            raise RuntimeError("native Timeline finish did not restore pad")
        sample = report["timeline_samples"][side]
        if not all(type(sample[key]) in (int, float) and math.isfinite(sample[key]) for key in ("position", "actual", "native_expected")) or not 0 < sample["actual"] < 1 or abs(sample["actual"]-sample["native_expected"]) > .002:
            raise RuntimeError("native curve/material sample missing")
        duration = report["cooldown_seconds"][side]
        if type(duration) not in (float, int) or not math.isfinite(duration) or not 14.9 <= duration <= 15.5:
            raise RuntimeError("default cooldown native elapsed time differs")
    final = report["policy_shutdown"]
    if final["errors"] or any(final[key] <= 0 for key in ("constructions", "begins", "ends", "actives", "updates", "finishes", "ticks")):
        raise RuntimeError("Python grant-GE path bypassed/error")
    return {"status": "passed", "case_count": 6, "bounded_runtime_acceptance": True, "full_acceptance": False}

if __name__ == "__main__":
    import argparse, json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
