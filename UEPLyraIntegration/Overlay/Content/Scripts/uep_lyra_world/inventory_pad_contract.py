"""Fail closed on the exact test-owned inventory/physical-overlap lane."""
import math

CASES = ("parent-construction", "mesh-construction", "mesh-native-tick", "mesh-profile-roundtrip",
    "parent-empty-pickup", "mesh-empty-pickup", "parent-full-no-grant", "mesh-full-no-grant",
    "parent-no-controller", "mesh-no-controller", "parent-native-destroy", "mesh-native-destroy")


def equal(actual, original):
    if type(actual) in (int, float) and type(original) in (int, float):
        return math.isfinite(actual) and math.isfinite(original) and abs(actual-original) < .001
    if type(actual) is dict and type(original) is dict:
        return set(actual) == set(original) and all(equal(actual[key], original[key]) for key in actual)
    if type(actual) is list and type(original) is list:
        return len(actual) == len(original) and all(equal(a, b) for a, b in zip(actual, original))
    return type(actual) is type(original) and actual == original


def validate(report):
    if report.get("schema_version") != 1 or report.get("status") != "passed" or report.get("error") is not None:
        raise RuntimeError("inventory native differential incomplete")
    for flag in ("full_acceptance", "network_acceptance", "production_placement_tested", "production_equipment_gas_tested",
                 "remote_audio_tested", "packaged_runtime", "manual_lifecycle_event", "overlap_handler_called_by_probe",
                 "inventory_properties_written_by_probe", "native_exception_gate_tested"):
        if report.get(flag) is not False:
            raise RuntimeError("unsupported inventory acceptance claim: "+flag)
    if report.get("fixture_native_inventory_setup") is not True or report.get("test_owned_controller_pawn_services") is not True or report.get("numeric_tolerance") != .001:
        raise RuntimeError("native inventory fixture domain missing")
    cases = report.get("cases", [])
    if [row.get("name") for row in cases] != list(CASES):
        raise RuntimeError("inventory case inventory differs")
    for row in cases:
        if row.get("passed") is not True or row.get("same_class") is not True or not equal(row.get("python"), row.get("blueprint")):
            raise RuntimeError("inventory native/BP comparison differs")
    for name in ("mesh-native-tick", "mesh-profile-roundtrip"):
        row = next(row for row in cases if row["name"] == name)
        if not all(side["yaw_change"] > 1.0 for side in (row["python"], row["blueprint"])):
            raise RuntimeError("missing automatic native mesh rotation")
    count = report.get("actors_created")
    if type(count) is not int or count <= 0 or report.get("native_test_actors_destroyed") != count:
        raise RuntimeError("native inventory test actors retained")
    final = report.get("policy_shutdown", {})
    if final.get("errors") != []:
        raise RuntimeError("inventory policy errors at shutdown")
    for key, minimum in (("constructions", 1), ("mesh_constructions", 1), ("mesh_ticks", 1), ("overlaps", 8),
                         ("authority_grants", 4), ("full_slots", 2), ("no_controller", 2), ("destroy_requests", 2)):
        if type(final.get(key)) is not int or final[key] < minimum:
            raise RuntimeError("native inventory policy branch not exercised: "+key)
    return {"status": "passed", "case_count": len(CASES), "bounded_runtime_acceptance": True, "full_acceptance": False}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
