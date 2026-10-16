"""Independent, bounded Character BP-call -> local GAS -> native equipment gate."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from .emote_audio_contract import CLASS

SELECT = "InputTag.Ability.Quickslot.SelectSlot"
OTHER = "InputTag.Ability.Jump"
DEFINITIONS = ["/ShooterCore/Weapons/"+name+"/ID_"+name+".ID_"+name+"_C" for name in ("Pistol", "Rifle", "Shotgun")]
PAIRS = (("slot-one", 0, 1, SELECT, 1, False), ("slot-two", 0, 2, SELECT, 2, False),
    ("repeat-selected", 1, 1, SELECT, 1, False), ("unrelated-tag", 0, 1, OTHER, 0, False),
    ("empty-slot", 0, 2, SELECT, 0, True), ("slot-zero", 2, 0, SELECT, 0, False))
PLAN = [(name, profile, initial, index, tag, expected, empty) for name, initial, index, tag, expected, empty in PAIRS
    for profile in ("BlueprintFallback", "Python")]+[("python-negative", "Python", 0, -1, SELECT, 0, False),
        ("python-past-end", "Python", 0, 99, SELECT, 0, False)]


def check_trial(row, index):
    name, profile, initial, slot, tag, expected, empty = PLAN[index]
    require((row["name"], row["profile"], row["initial"], row["slot"], row["tag"], row["empty_slot"]) ==
        (name, profile, initial, slot, tag, empty), "Character slot plan/order differs")
    require(row["native_character_class"] == CLASS and row["bp_reference_call"] is True and row["inventory"]["active"] == expected and
        row["inventory"]["equipment_instigator_matches"] is True and row["inventory_items_unchanged"] is True,
        "Character BP call/native equipment result differs")
    model = row["inventory"]
    require(model["items"] == sorted(DEFINITIONS) and model["slots"] == DEFINITIONS[:2]+[None if empty else DEFINITIONS[2]] and
        model["definition"] == DEFINITIONS[expected] and model["equipment_class"] == DEFINITIONS[expected].replace("/ID_", "/B_WeaponInstance_").replace(".ID_", ".B_WeaponInstance_"),
        "Character slot identical-but-wrong native inventory/equipment model")
    counters = row["counters"]
    require(counters["python_calls"] == (profile == "Python") and counters["fallback_calls"] == (profile == "BlueprintFallback"),
        "Character slot call did not enter exactly the selected Profile")
    sent = not empty and 0 <= slot < 3
    require(len(row["events"]) == int(sent) and row["callback_errors"] == [] and
        row["native_tasks_before"] == row["native_tasks_after"] == 3 and row["task_scope_closed"] is True,
        "Character slot native payload observer/task lifetime differs")
    if profile == "Python":
        require(counters["events_sent"] == int(sent) and counters["invalid_index_noops"] == int(not 0 <= slot < 3) and
            counters["empty_slot_noops"] == int(empty) and counters["missing_controller_noops"] == counters["missing_quickbar_noops"] == 0,
            "Character slot decision counters differ")
    if sent:
        event, = row["events"]
        require(event["tag"] == tag and event["magnitude"] == float(slot) and event["instigator_null"] is True and
            event["target_null"] is True and event["optional_objects_null"] is True,
            "Character slot native GameplayEvent payload changed")


def validate(report):
    require(report["status"] == "passed" and not report.get("error"), "Character slot report failed")
    require(len(report["cases"]) == len(PLAN), "Character slot cases missing")
    for index, row in enumerate(report["cases"]): check_trial(row, index)
    for index in range(0, len(PAIRS)*2, 2):
        require(report["cases"][index]["inventory"] == report["cases"][index+1]["inventory"] and
            report["cases"][index]["events"] == report["cases"][index+1]["events"], "Original/Python native Character slot result differs")
    require(report["scopes_created"] == report["scopes_closed"] == len(PLAN) and report["active_observation_scopes"] == 0 and
        report["original_fields_profile_cdo_restored"] is True and report["original_inventory_restored"] is True and
        report["native_quickslot_ability_active_with_three_tasks"] is True,
        "Character slot resources/original native state not restored")
    for key in ("physical_keyboard_tested", "python_handler_replayed", "inventory_properties_written", "native_rpc_bypassed",
            "gameplay_event_replication_claimed", "whole_character_migrated", "full_acceptance"):
        require(report[key] is False, "Character slot report overclaims "+key)
    return dict(status="passed", native_bp_reference_call=True, native_gameplay_event_observed=True,
        cases=len(PLAN), original_python_pairs=len(PAIRS), python_only_invalid_index_cases=2, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
