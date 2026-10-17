"""Native part producers, exact receiver/nested routing and owned cleanup."""
import argparse
import json
from pathlib import Path
from .emote_audio_contract import CLASS
from uep_lyra_abilities.auto_respawn_helpers_contract import require

TEMP_CLASS = "/Script/Engine.Actor"
PLAN = [(name, profile, target, switch) for name, target, switch in (("owner-basic", "owner", False),
    ("owner-switch", "owner", True), ("unassigned-basic", "unassigned", False)) for profile in ("BlueprintFallback", "Python")]


def check_operation(row, *, profile, active, found, user, callbacks=1):
    expected_calls = callbacks if active else 0; py = profile == "Python"; stats = row["counters"]
    require(row["profile"] == profile and row["native_callback_count"] == expected_calls and row["native_operation_called"] is True and row["native_delegate_payload_matches"] is True,
        "native parts operation/selected callback count differs")
    require(stats == dict(python_calls=expected_calls*int(py), fallback_calls=expected_calls*int(not py), team_queries=expected_calls*int(py),
        team_updates=expected_calls*int(py and found), no_team_noops=expected_calls*int(py and not found)), "selected bound receiver policy counts differ")
    nested = row["team_counters"]
    require(nested["python_calls"] == expected_calls*int(py and found) and nested["fallback_calls"] == expected_calls*int(not py and found),
        "native component callback did not traverse selected virtual team helper")
    if py and expected_calls:
        require(row["last_query"] == row["native_team_query"], "Python receiver native team inputs differ from independent query")
    expected_properties = expected_calls*int(found and user)
    require(row["native_device_properties_created"] == len(row["native_device_properties"]) == expected_properties and
        row["native_scheduler_removed_owned_properties"] is True, "native callback device scheduler count/lifetime differs")
    for item in row["native_device_properties"]:
        counts = item["counters"]
        require(counts["evaluations"] == counts["valid_controllers"] == counts["colors_written"] == 1 and counts["fallback_evaluations"] == 0,
            "native scheduled callback property did not execute its actual Python policy")


def validate(report):
    require(report["status"] == "passed" and not report.get("error") and report["retained_character_class"] == CLASS and
        len(report["cases"]) == len(PLAN), "native parts standalone matrix incomplete")
    require(report["natural_startup_python_dispatch"]["python_calls"] >= 1 and report["natural_startup_python_dispatch"]["fallback_calls"] == 0,
        "natural native part creation did not enter Python receiver")
    properties = 0
    for case, expected in zip(report["cases"], PLAN):
        name, initial, target, switch = expected
        require((case["name"], case["initial_profile"], case["target"], case["switch"]) == expected and case["native_authority"] is True,
            "native parts case/authority plan differs")
        found, user = target == "owner", target == "owner"
        require(case["native_team_query"]["part_of_team"] is found and case["platform_user_valid"] is user,
            "real owner/unassigned native team/platform context differs")
        require(len(case["operations"]) == 3, "native add/remove/repeated-remove matrix incomplete")
        for index, row in enumerate(case["operations"]):
            profile = ("Python" if initial == "BlueprintFallback" else "BlueprintFallback") if switch and index else initial
            require(row["operation"] == ("add", "remove", "remove-again")[index], "native parts operation order differs")
            check_operation(row, profile=profile, active=index < 2, found=found, user=user)
            require(row["part_entries"] == len(case["original_parts"])+(1 if index == 0 else 0) and
                row["temporary_actors"] == (1 if index == 0 else 0), "native part entry/actual spawned Actor lifetime differs")
            properties += row["native_device_properties_created"]
        require(case["original_part_entries_and_actor_identities_restored"] is True and case["owned_temporary_actors_destroyed"] is True,
            "native cosmetic entry/child Actor identity scope not restored")
    for index in range(0, len(PLAN), 2):
        a, b = report["cases"][index:index+2]
        for left, right in zip(a["operations"], b["operations"]):
            require(left["visual"] == right["visual"] and [item["color"] for item in left["native_device_properties"]] ==
                [item["color"] for item in right["native_device_properties"]], "original/Python native cosmetic/software visual state differs")
    require(report["original_player_visual_camera_profile_cdo_inventory_restored"] is True and report["owned_unassigned_actor_destroyed"] is True and
        report["native_observation_markers_removed"] is True and report["device_roots_created"] == report["device_roots_released"] == properties+report["native_observation_markers"] and
        report["native_observation_markers"] == len(PLAN)*6, "native parts original state/device marker/root cleanup differs")
    require(report["delegate_fixture_shutdown"] == dict(created=1, closed=1, bindings_created=2, bindings_closed=2, active=0, deliveries=12, errors=[]),
        "independent native component observer scope/delivery count differs")
    for key in ("callback_replayed", "component_delegate_broadcast_by_fixture", "all_parts_removed_by_fixture", "parts_properties_written", "hardware_output_tested", "pixels_verified", "full_acceptance", "whole_character_migrated"):
        require(report[key] is False, "native parts report overclaims "+key)
    return dict(status="passed", native_part_cycles=6, native_part_operations=18, native_callback_entries=12,
        native_device_properties=properties, native_component_callback_and_team_branch=True, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
