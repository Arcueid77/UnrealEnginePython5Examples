"""Native team orchestration and owned scheduler evidence; no rendered/hardware claim."""
import argparse
import json
from pathlib import Path
from .emote_audio_contract import CLASS
from .outline_contract import near
from uep_lyra_abilities.auto_respawn_helpers_contract import require

DEVICE = "/ShooterCore/Game/B_TeamColor_DeviceProperty.B_TeamColor_DeviceProperty_C"
PAIRS = (("current", "current", "current", 1, "owner"), ("fallback", "none", "current", 1, "owner"),
    ("stencil-one", "current", 1, 1, "owner"), ("stencil-seven", "current", 7, 1, "owner"),
    ("max-none", "none", 255, 1, "owner"), ("repeat", "current", "current", 3, "owner"),
    ("unpossessed-valid", "current", 7, 1, "unpossessed"), ("unpossessed-none", "none", 255, 1, "unpossessed"))
PLAN = [(name, profile, source, team, calls, target) for name, source, team, calls, target in PAIRS for profile in ("BlueprintFallback", "Python")]


def validate(report):
    require(report["status"] == "passed" and not report.get("error") and len(report["cases"]) == len(PLAN), "team orchestration native matrix incomplete")
    require(report["retained_character_class"] == CLASS and report["current_display_asset_valid"] is True and
        report["natural_startup_python_dispatch"]["python_calls"] >= 1 and report["natural_startup_python_dispatch"]["fallback_calls"] == 0,
        "natural native team callback/retained Character/default display differs")
    total_properties = 0
    for index, row in enumerate(report["cases"]):
        name, profile, source, team, calls, target = PLAN[index]
        actual_team = report["original_team_id"] if team == "current" else team
        require((row["name"], row["profile"], row["source"], row["team_id"], row["calls"], row["target"]) ==
            (name, profile, source, actual_team, calls, target) and row["bp_reference_call"] is True, "team native call/parameter plan differs")
        stats, nested = row["counters"], row["outline_counters"]
        require(stats["python_calls"] == (calls if profile == "Python" else 0) and stats["fallback_calls"] == (calls if profile == "BlueprintFallback" else 0) and
            all(stats[key] == (calls if profile == "Python" else 0) for key in ("color_queries", "outline_calls", "stencil_calls")) and
            stats["display_applies"] == (calls if profile == "Python" and source == "current" else 0) and
            stats["invalid_platform_noops"] == (calls if profile == "Python" and not row["platform_user_valid"] else 0) and
            stats["device_activation_attempts"] == (calls if profile == "Python" and row["platform_user_valid"] else 0), "team selected native operations differ")
        require(nested["python_calls"] == (calls if profile == "Python" else 0) and nested["fallback_calls"] == (calls if profile == "BlueprintFallback" else 0),
            "team-to-outline nested BP/Python dispatch differs")
        actual = row["actual"]; require(bool(actual["primitives"]), "native team stencil primitives missing")
        expected_stencil = 0 if row["locally_controlled"] and row["player_controlled"] else actual_team
        require(all(value["stencil"] == expected_stencil for value in actual["primitives"]), "native stencil result differs from unchanged parent BP policy")
        if row["locally_controlled"]:
            require(actual["outline"] is not None and len(actual["outline"]["vector"]) == len(row["expected_color"]) == 4 and near(actual["outline"]["scalar"], float(actual_team)) and
                all(near(a, b) for a, b in zip(actual["outline"]["vector"], row["expected_color"])), "native team outline values differ")
        else: require(actual["outline"] is None, "nonlocal team callback created an outline")
        expected_count = calls if row["platform_user_valid"] else 0
        require(report["native_device_subsystem_available"] is True or row["platform_user_valid"] is False,
            "absent native device subsystem cannot accept a valid platform user")
        require(row["native_device_properties_created"] == len(row["native_device_properties"]) == expected_count and
            row["native_scheduler_removed_owned_properties"] is True, "native platform/device scheduler count/lifetime differs")
        for device in row["native_device_properties"]:
            counts = device["counters"]
            require(device["native_type"] == DEVICE and counts["evaluations"] == counts["valid_controllers"] == counts["colors_written"] == 1 and
                counts["fallback_evaluations"] == 0 and device["color"]["enabled"] is True and device["color"]["reset"] is False,
                "native scheduled device property did not execute actual default Python software policy")
        total_properties += expected_count
        require(row["original_visual_camera_profile_restored"] is True, "native team visual/camera/Profile state not restored")
    for index in range(0, len(PLAN), 2):
        a, b = report["cases"][index:index+2]
        require(a["actual"] == b["actual"] and a["expected_color"] == b["expected_color"] and
            [device["color"] for device in a["native_device_properties"]] == [device["color"] for device in b["native_device_properties"]],
            "original/Python team material/stencil/device software state differs")
    require(report["native_observation_markers"] == (len(PLAN)*2 if report["native_device_subsystem_available"] else 0) and report["native_observation_markers_removed"] is True and
        report["native_handle_queries_read_only"] is True and report["native_active_set_written"] is False,
        "native bounded observation markers/readonly query scope differs")
    require(report["device_roots_created"] == report["device_roots_released"] == total_properties+report["native_observation_markers"] and
        report["caller_roots_created"] == report["caller_roots_released"] and report["owned_unpossessed_actor_destroyed"] is True and
        report["original_visual_camera_profile_cdo_inventory_restored"] is True, "native team cleanup/root/identity scope differs")
    for key in ("hardware_output_tested", "pixels_verified", "whole_character_migrated", "full_acceptance", "device_mapping_written", "callbacks_replayed", "all_device_properties_removed"):
        require(report[key] is False, "team report overclaims "+key)
    return dict(status="passed", native_bp_python_pairs=8, native_nested_outline_and_stencil=True,
        native_device_scheduler_properties=total_properties, hardware_output_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
