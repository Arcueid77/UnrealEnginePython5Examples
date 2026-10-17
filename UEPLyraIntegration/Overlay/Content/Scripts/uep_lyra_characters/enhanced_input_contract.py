"""Retained EnhancedInput receivers -> native GAS events/equipment acceptance."""
import argparse
import json
from pathlib import Path
from .quickbar_input_contract import CLASS, SELECT, DEFINITIONS, require

BACK = "InputTag.Ability.Quickslot.CycleBackward"
FORWARD = "InputTag.Ability.Quickslot.CycleForward"
ACTIONS = {
    "slot-0": ("IA_QuickSlot1", "InpActEvt_IA_QuickSlot1_K2Node_EnhancedInputActionEvent_4", 0, SELECT),
    "slot-1": ("IA_QuickSlot2", "InpActEvt_IA_QuickSlot2_K2Node_EnhancedInputActionEvent_3", 1, SELECT),
    "slot-2": ("IA_QuickSlot3", "InpActEvt_IA_QuickSlot3_K2Node_EnhancedInputActionEvent_2", 2, SELECT),
    "back": ("IA_QuickSlot_CycleBackward", "InpActEvt_IA_QuickSlot_CycleBackward_K2Node_EnhancedInputActionEvent_1", 0, BACK),
    "forward": ("IA_QuickSlot_CycleForward", "InpActEvt_IA_QuickSlot_CycleForward_K2Node_EnhancedInputActionEvent_0", 0, FORWARD)}
# name/action/initial/expected/empty slot. Cycle nodes really leave index at zero.
CASES = (("select-zero", "slot-0", 2, 0, None), ("select-one", "slot-1", 0, 1, None),
    ("select-two", "slot-2", 0, 2, None), ("cycle-back", "back", 0, 2, None),
    ("cycle-forward", "forward", 2, 0, None), ("repeat-selected", "slot-1", 1, 1, None),
    ("empty-select", "slot-2", 0, 0, 2), ("empty-default-cycle", "forward", 1, 1, 0))
PLAN = [(*case, profile) for case in CASES for profile in ("BlueprintFallback", "Python")]


def check_trial(row, expected):
    name, action, initial, selected, empty, profile = expected
    asset, _, slot, tag = ACTIONS[action]; sent = empty is None
    function = row["native_bound_receiver"]; prefix = "InpActEvt_"+asset+"_K2Node_EnhancedInputActionEvent_"
    require((row["name"], row["action"], row["initial"], row["empty_slot"], row["profile"]) == (name, action, initial, empty, profile), "EnhancedInput native trial plan differs")
    require(row["native_character_class"] == CLASS and row["native_input_subsystem_used"] is True and row["positive_native_injections"] == 1 and function.startswith(prefix) and function[len(prefix):].isdigit(),
        "actual native EnhancedInput injection/retained receiver missing")
    counts = row["input_counters"]
    require(counts == dict(python_calls=int(profile == "Python"), fallback_calls=0, **{key: int(profile == "Python" and key == action) for key in ACTIONS}) and
        row["native_original_input_fallback"] is (profile == "BlueprintFallback") and row["receiver_is_native_router"] is True,
        "input did not enter exactly one selected bound receiver")
    nested = row["helper_counters"]
    require(nested["python_calls"] == int(profile == "Python") and nested["fallback_calls"] == int(profile != "Python"), "input did not traverse selected virtual Quickbar helper")
    if profile == "Python":
        require(nested["events_sent"] == int(sent) and nested["empty_slot_noops"] == int(not sent) and
            nested["invalid_index_noops"] == nested["missing_controller_noops"] == nested["missing_quickbar_noops"] == 0, "input helper raw constant/default-index decision differs")
    model = row["inventory"]
    require(model["active"] == selected and model["items"] == sorted(DEFINITIONS) and model["slots"] == [None if index == empty else value for index, value in enumerate(DEFINITIONS)] and
        model["definition"] == DEFINITIONS[selected] and model["equipment_instigator_matches"] is True and
        model["equipment_class"] == DEFINITIONS[selected].replace("/ID_", "/B_WeaponInstance_").replace(".ID_", ".B_WeaponInstance_"), "input native equipment result differs")
    require(row["inventory_items_unchanged"] is True and row["native_tasks_before"] == row["native_tasks_after"] == 3 and
        row["task_scope_closed"] is True and row["callback_errors"] == [] and row["no_repeated_or_release_handler"] is True, "native input task/inventory/release lifetime differs")
    require(len(row["events"]) == int(sent), "independent native GAS event count differs")
    if sent:
        require(row["events"] == [dict(tag=tag, magnitude=float(slot), instigator_null=True, target_null=True, optional_objects_null=True)], "input raw native gameplay tag/payload/default index differs")


def report_cleanup(report):
    require(report["scopes_created"] == report["scopes_closed"] == len(PLAN) and report["active_observation_scopes"] == 0 and
        report["original_fields_profile_cdo_restored"] is True and report["original_inventory_restored"] is True and
        report["native_quickslot_ability_active_with_three_tasks"] is True, "native input cleanup/ability lifetime failed")
    for key in ("physical_keyboard_tested", "python_handler_replayed", "bp_receiver_called_by_fixture", "inventory_properties_written", "native_rpc_bypassed",
        "gameplay_event_replication_claimed", "whole_character_migrated", "full_acceptance"):
        require(report[key] is False, "input report overclaims "+key)


def validate(report):
    require(report["status"] == "passed" and not report.get("error") and len(report["cases"]) == len(PLAN), "EnhancedInput standalone incomplete")
    require(set(report["native_input_bindings"]) == set(ACTIONS) and len(set(report["native_input_bindings"].values())) == 5, "native compiled input binding snapshot incomplete")
    require(report["native_profile_method_counts"] == dict(Python=17, BlueprintFallback=12), "native original fallback/profile method set differs")
    for row, expected in zip(report["cases"], PLAN):
        require(row["native_bound_receiver"] == report["native_input_bindings"][row["action"]], "runtime bound receiver differs from actual native binding table")
        check_trial(row, expected)
    for index in range(0, len(PLAN), 2):
        a, b = report["cases"][index:index+2]
        require(a["inventory"] == b["inventory"] and a["events"] == b["events"], "original/Python actual input result differs")
    report_cleanup(report)
    return dict(status="passed", native_enhanced_input_trials=len(PLAN), original_python_pairs=len(CASES), physical_keyboard_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
