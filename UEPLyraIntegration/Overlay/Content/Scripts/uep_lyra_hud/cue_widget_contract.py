"""Native base/child widget state and real Cue-manager lifetime evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path

PROFILES = ("BlueprintFallback", "Python")
CLASSES = ("base", "match", "waiting")
CASES = ("local", "none", "foreign", "orphan", "bot", "missing-widget", "repeat-start")
SKIPS = ("foreign", "orphan", "bot")


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_mode"] == "Standalone", "native widget Cue run failed")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "pixels_tested", "audio_playback_tested",
            "native_remote_controller_branch_tested", "message_widget_business_migrated", "cue_manager_callbacks_replayed", "health_properties_written"):
        require(report[field] is False, "Cue widget scope overclaim: "+field)
    for field in ("all_owned_widgets_removed", "all_owned_regular_actors_destroyed", "all_owned_cue_actors_recycled", "health_unchanged", "player_array_restored",
            "base_providers_restored", "widget_observer_restored", "probe_unrooted", "music_dependency_fields_restored", "abstract_base_verified_through_concrete_fixture"):
        require(report[field] is True, "Cue widget restoration absent: "+field)
    require(report["native_end_cue_owner"] == "/Script/GameplayAbilities.GameplayCueNotify_Actor", "Cue cleanup must use the unchanged native end/recycle API")
    recycled = report["native_recycled_cue_actor_states"]
    require(len(recycled) == 42 and len({r["path"] for r in recycled}) == 42 and all(r["hidden"] and r["owner_none"] and r["tick_disabled"] for r in recycled), "actual native pool terminal states missing")
    rows = report["cases"]
    require(Counter((r["class"],r["profile"],r["name"]) for r in rows) == Counter((c,p,n) for c in CLASSES for p in PROFILES for n in CASES), "native Cue widget matrix incomplete")
    for row in rows:
        name = row["name"]; seeded = name not in ("local", "none")
        require(row["actual_start_entries"] == (2 if seeded else 1) and row["actual_remove_entries"] == 2 and
            row["native_event_returns"] == ([False,None,False,False] if seeded else [False,False,False]) and row["explicit_second_business_event"] == seeded, "native Cue event/gate ABI or dispatch differs")
        require(row["native_looping_sound_slots"] == row["actual_native_spawn_audio_slots"] == 1, "original native looping sound slot was removed, duplicated or not executed")
        require(row["pre_remove"]["controller_is_local"] == (name != "none") and row["retained_fields_after_removal"], "source local controller/cache retention differs")
        expected_creates = 2 if name == "repeat-start" else 1
        require(row["created_widgets"] == expected_creates and row["actual_interface_entries"] == (expected_creates if row["class"] == "match" else 0), "actual native creation/interface call count differs")
        if name == "missing-widget":
            require(not row["pre_remove"]["widget_valid"] and row["old_widget_visible_after_removal"], "null creation must overwrite cache without removing previous widget")
        else:
            require(row["pre_remove"]["widget_valid"] and row["pre_remove"]["in_viewport"] and row["pre_remove"]["widget_owner_is_local"] and row["removed_widget_not_visible"], "actual native screen ownership/removal differs")
        if name in SKIPS: require(row["same_seed_widget"] and not row["old_widget_visible_after_removal"], "skipped instigator branch changed or leaked the retained widget")
        if name == "repeat-start": require(not row["same_seed_widget"] and row["old_widget_visible_after_removal"], "source repeated start must replace cache without removing old widget")
    for cls in CLASSES:
        for name in CASES:
            paired = [r for r in rows if r["class"] == cls and r["name"] == name]
            require(paired[0]["pre_remove"] == paired[1]["pre_remove"], "native original/Python Cue widget state differs: "+cls+"/"+name)
            require(paired[0]["interface_payloads"] == paired[1]["interface_payloads"], "original/Python actual interface payload differs")
    manager = report["manager_cases"]
    require(Counter(r["class"] for r in manager) == Counter(("match", "waiting")), "real Cue manager child matrix incomplete")
    for row in manager:
        require(row["selected_profile"] == "Python" and row["actual_manager_start_entries"] == 1 and row["actual_manager_remove_entries"] == 1,
            "actual manager must dispatch the default Python base gates")
        require(row["bp_library_caller"] and row["native_target_has_no_asc"] and row["widget_added"] and row["widget_removed"] and row["source_cached_reference_preserved"] and row["borrowed_a_matrix_actor_returned_to_native_pool"], "native non-replicated Cue manager ownership/removal/reuse differs")
        require(row["duplicate_add_respected_native_guard"] and row["native_looping_sound_slots"] == row["actual_native_spawn_audio_slots"] == 1, "native duplicate-WhileActive guard or original sound slot differs")
    return dict(status="passed", paired_base_and_child_cases=21, native_matrix_cases=42, native_matrix_start_entries=72,
        native_matrix_remove_entries=84, native_while_active_calls=42, explicit_second_business_events=30, real_blueprint_cue_manager_children=2, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
