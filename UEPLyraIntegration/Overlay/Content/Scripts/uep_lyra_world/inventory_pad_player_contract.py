"""Exact standalone real-player inventory/equipment/fire proof, not networking."""
import math
CASES = ("parent-player-pickup-fire", "mesh-player-pickup-fire", "parent-player-full", "mesh-player-full")


def validate(report):
    if report.get("status") != "passed" or report.get("error") is not None or report.get("schema_version") != 1:
        raise RuntimeError("real-player inventory lane incomplete")
    for flag in ("network_acceptance", "full_acceptance", "packaged_runtime", "overlap_handler_called_by_probe",
                 "ammo_properties_written", "inventory_properties_written", "manual_lifecycle_event"):
        if report.get(flag) is not False:
            raise RuntimeError("unsupported player inventory claim: "+flag)
    if report.get("net_mode") != "Standalone" or report.get("original_player_restored") is not True:
        raise RuntimeError("real player domain/rollback missing")
    restore = report.get("player_restore", {})
    if restore.get("inventory_identity_equal") is not True or restore.get("movement") != restore.get("expected_movement"):
        raise RuntimeError("real player restoration evidence differs")
    for field in ("position_max_error", "aim_max_error"):
        value = restore.get(field)
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value < .01:
            raise RuntimeError("real player transform not restored")
    if report.get("actors_created") != 8 or report.get("actors_destroyed") != 8:
        raise RuntimeError("player inventory fixture pad leak")
    if [row.get("name") for row in report.get("cases", [])] != list(CASES):
        raise RuntimeError("player inventory cases differ")
    for row in report["cases"]:
        if row.get("same_class") is not True or row.get("passed") is not True or row["python"] != row["blueprint"]:
            raise RuntimeError("player inventory BP/Python result differs")
        value = row["python"]
        if type(row.get("native_input_frames")) is not list or len(row["native_input_frames"]) != 2:
            raise RuntimeError("both native input traces required")
        if "pickup-fire" in row["name"]:
            if (value["item_delta"] != 1 or value["native_equipment_instigator_matches"] is not True or
                    not value["equipment_class"] or value["magazine_before"]-value["magazine_after"] != 1):
                raise RuntimeError("native inventory/equipment/GAS firing proof missing")
            if any(type(number) is not int or number <= 0 for number in row["native_input_frames"]):
                raise RuntimeError("native input not driven on both profiles")
        elif value["item_delta"] != 0 or value["inventory_unchanged"] is not True:
            raise RuntimeError("native full-slot rejection differs")
        if row.get("native_rollbacks") != [True, True]:
            raise RuntimeError("player inventory not restored after each profile")
    final = report.get("policy_shutdown", {})
    if final.get("errors") != [] or final.get("authority_grants", 0) < 2 or final.get("full_slots", 0) < 2:
        raise RuntimeError("player inventory policy branch missing/error")
    return {"status": "passed", "case_count": 4, "bounded_runtime_acceptance": True,
            "native_player_inventory_equipment_fire": True, "network_acceptance": False, "full_acceptance": False}


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
