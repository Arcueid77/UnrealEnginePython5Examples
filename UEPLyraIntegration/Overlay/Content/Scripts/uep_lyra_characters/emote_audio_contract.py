"""Native second-BP Interface reference, mixed-instance and GC semantic gate."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.auto_respawn_helpers_contract import require

CLASS = "/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin_C"
PLAN = [(name, profile, profile, kind) for name, kind in (("null", "null"), ("component-a", "a"),
    ("repeat-reference", "a"), ("replace-reference", "b")) for profile in ("BlueprintFallback", "Python")]+[
    ("bp-write-python-read", "BlueprintFallback", "Python", "a"), ("python-write-bp-read", "Python", "BlueprintFallback", "b"),
    ("bp-clear-python-read", "BlueprintFallback", "Python", "null"), ("python-clear-bp-read", "Python", "BlueprintFallback", "null")]


def expected_counts(writer, reader):
    return dict(python_sets=int(writer == "Python"), fallback_sets=int(writer == "BlueprintFallback"),
        python_gets=int(reader == "Python"), fallback_gets=int(reader == "BlueprintFallback"))


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["retained_character_class"] == CLASS and
        report["second_bp_interface_message_caller"] is True and report["two_native_same_class_actors"] is True and
        report["primary_actor"] != report["secondary_actor"], "real retained-class second-BP Interface evidence missing")
    for key in ("hardware_sound_verified", "audio_playback_called_by_fixture", "animation_notify_modified", "character_subclass_created", "full_acceptance", "whole_character_migrated"):
        require(report[key] is False, "unsupported Character Interface claim: "+key)
    require([(r["name"], r["writer"], r["reader"], r["kind"]) for r in report["cases"]] == PLAN, "native Interface round-trip matrix incomplete")
    a, b = report["native_component_paths"]
    require(a and b and a != b, "two distinct real AudioComponent references required")
    for row in report["cases"]:
        expected = None if row["kind"] == "null" else a if row["kind"] == "a" else b
        require(row["field_after_write"] == row["bp_read_result"] == expected and row["reference_identity_matches"] is True and
            row["native_actor_type_preserved"] is True and row["counters"] == expected_counts(row["writer"], row["reader"]),
            "Interface return/reference/selected-Profile dispatch differs")
    require(len(report["mixed_instances"]) == 2, "same-BP mixed-instance Profile pair missing")
    for index, row in enumerate(report["mixed_instances"]):
        profiles = ("Python", "BlueprintFallback") if index == 0 else ("BlueprintFallback", "Python")
        require((row["primary_profile"], row["secondary_profile"]) == profiles and row["primary_result"] == a and row["secondary_result"] == b and
            row["primary_counters"] == expected_counts(profiles[0], profiles[0]) and row["secondary_counters"] == expected_counts(profiles[1], profiles[1]) and
            row["both_native_types_preserved"] is True, "same BP instances shared an incorrect Profile/component")
    gc = report["native_gc"]
    require(gc == dict(native_collect_garbage_called=True, both_components_valid=True, primary_result=a, secondary_result=b),
        "actual native GC reference lifetime not observed")
    require(report["non_targets"] == [dict(target="null", result_is_null=True, character_counters_unchanged=True),
        dict(target="non-interface-controller", result_is_null=True, character_counters_unchanged=True)], "native Interface non-target/default branch differs")
    require(report["native_components_created"] == report["native_components_destroyed"] == 2 and report["original_fields_restored"] is True and
        report["original_profiles_restored"] is True and report["cdo_unchanged"] is True and report["inventory_unchanged"] is True,
        "native component ownership/restoration incomplete")
    return dict(status="passed", native_second_bp_interface_roundtrip=True, cases=len(PLAN), same_class_mixed_instances=True,
        native_gc_lifetime=True, hardware_sound_verified=False, whole_character_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
