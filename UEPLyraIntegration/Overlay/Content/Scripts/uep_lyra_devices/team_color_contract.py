"""Native software device-color differential gate, never physical LED proof."""
import argparse
import json
from pathlib import Path

PLAN = ("native-one-shot", "native-repeat", "native-looping", "same-instance-profile-switch", "native-paused-loop", "public-invalid-user")


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_default_profile_observed"] and
        report["original_player_restored"] and report["owned_handles_removed"] and
        report["roots_created"] == report["roots_removed"] == 3+len(PLAN)*2, "native device default/ownership/restore invalid")
    require(report["same_instance_native_reactivation_tested"] is False, "unreflected instance activation must not be claimed")
    require(report["invalid_user_public_bp_entry_used"] and not report["invalid_user_submitted_to_scheduler"], "invalid-user fixture source misrepresented")
    for flag in ("direct_python_handler_replayed", "native_apply_called_by_probe", "hardware_output_tested", "full_acceptance", "network_acceptance",
        "packaged_runtime", "animation_assets_modified", "device_mapping_written", "cdo_profile_written"):
        require(report[flag] is False, "unsupported device color claim: "+flag)
    require([row["name"] for row in report["cases"]] == list(PLAN), "native device matrix incomplete")
    for row in report["cases"]:
        invalid, switched = row["name"] == "public-invalid-user", row["name"] == "same-instance-profile-switch"
        looped = row["name"] in ("native-looping", "native-paused-loop") or switched
        for side in ("blueprint", "python"):
            value = row[side]; counts = value["counters"]
            require(value["native_type_preserved"] and value["native_profile_selected"] and value["original_player_restored"] and
                value["native_class"] == "/ShooterCore/Game/B_TeamColor_DeviceProperty.B_TeamColor_DeviceProperty_C" and
                value["native_scheduler_used"] == (not invalid) and
                value["native_activation_count"] == (0 if invalid else (2 if row["name"] == "native-repeat" else 1)), "native device scheduler/type/profile source invalid")
            require(value["same_instance_profile_switch_preserved"] == switched and value["native_pause_observed"] == (row["name"] == "native-paused-loop"),
                "native device profile/pause lifetime not exercised")
            if invalid: require(value["after"] == value["before"], "invalid user changed original device data")
            else: require(value["after"] == report["native_default_color"] and value["after"]["enabled"] and not value["after"]["reset"], "native team color differs from default scheduler")
            if switched:
                require(counts["evaluations"] >= 3 and counts["fallback_evaluations"] >= 3 and
                    counts["colors_written"] == counts["valid_controllers"] == counts["evaluations"], "same native instance did not evaluate both Profiles")
            elif side == "python":
                require(counts["fallback_evaluations"] == 0 and counts["evaluations"] >= (3 if looped else (2 if row["name"] == "native-repeat" else 1)) and
                    counts["colors_written"] == counts["valid_controllers"] == (0 if invalid else counts["evaluations"]), "native Python device decisions differ")
                if not looped: require(counts["evaluations"] == (2 if row["name"] == "native-repeat" else 1), "native one-shot device evaluated more than expected")
            else: require(counts["evaluations"] == 0 and counts["colors_written"] == 0 and
                counts["fallback_evaluations"] >= (3 if looped else (2 if row["name"] == "native-repeat" else 1)), "original BP device path bypassed")
        require(row["blueprint"]["after"] == row["python"]["after"], "original BP/Python device color differs")
    policy = report["policy_shutdown"]
    require(policy["errors"] == [] and policy["active_count"] == policy["script_subscriptions_created"] == 0, "device policy error/subscription leak")
    return dict(status="passed", bounded_software_device_acceptance=True, pairs=len(PLAN), hardware_output_tested=False,
        invalid_user_source="public BP entry, not scheduler")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
