"""DropWeapon original authority inventory deletion/cycle, not pickup spawning."""
import argparse
import json
from pathlib import Path

# RemoveItemFromSlot resets the active index to -1 before native CycleForward.
# Keep the original pistol in slot 0: it is selected even when slot 2 is filled.
PLAN = (("rifle-to-pistol", 1, 1, 0), ("rifle-with-shotgun", 2, 1, 0), ("shotgun-wrap", 2, 2, 0), ("empty-slot-cycle", 0, 1, 0))


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report, authority=True):
    require(report["status"] == "passed" and report["error"] is None and report["original_player_restored"] and report["fixture_native_authority_inventory_api"],
        "DropWeapon native fixture/restore missing")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed",
        "ability_activation_called_by_probe", "inventory_or_slots_written_as_properties", "world_pickup_spawned"):
        require(report[field] is False, "unsupported DropWeapon claim: "+field)
    require([row["name"] for row in report["cases"]] == [row[0] for row in PLAN], "DropWeapon matrix incomplete")
    for row, (_, extra, initial, expected) in zip(report["cases"], PLAN):
        for side in ("blueprint", "python"):
            value = row[side]
            require(value["native_type_preserved"] and value["original_item_identities_preserved"] and value["removed_item_absent"] and
                value["dropped_slot_empty"] and value["native_ability_inactive"] and value["fixture_original_restored"] and
                value["active_slot"] == expected and value["input_injections"] == 1 and value["no_late_activation"], "DropWeapon native source/inventory/input/end/restore differs")
        require(row["blueprint"]["inventory_model"] == row["python"]["inventory_model"], "DropWeapon original/Python native inventory/equipment differs")
        counts = row["python"]["counters"]
        require(counts["activations"] == counts["native_ends"] == 1 and
            counts["authority_branches"] == counts["cycles"] == int(authority) and counts["items_removed"] == int(authority and extra > 0) and
            counts["client_branches"] == int(not authority), "DropWeapon Python/native role path not reached")
    require(report["policy_shutdown"]["active_count"] == 0 and report["policy_shutdown"]["errors"] == [], "DropWeapon retained active state/error")
    return dict(status="passed", bounded_runtime_acceptance=True, pairs=len(PLAN), original_delete_not_world_pickup=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
