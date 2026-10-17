"""A legacy function forwarding contract, explicitly not real RepNotify ingress."""
import argparse
import json
from pathlib import Path
from .team_observer_contract import CLASS, PLAN, require


def check_row(row, *, profile, calls, user):
    py = profile == "Python"
    require(row["profile"] == profile and row["typed_bp_refresh_calls"] == calls and
        row["counters"] == dict(python_calls=calls*int(py), fallback_calls=calls*int(not py), team_forwards=calls*int(py)), "legacy selected forwarding branch differs")
    require(row["helper_payload"] == dict(team_id=0, display_asset=None), "legacy helper replaced literal zero/null with current-team inference")
    stats = row["team_counters"]
    require(stats["python_calls"] == calls*int(py) and stats["fallback_calls"] == calls*int(not py), "legacy entry did not call selected virtual team helper")
    require(row["native_team_state_unchanged"] is True and row["native_listener_proxy_set_unchanged"] is True and
        row["native_collection_checked_after_engine_ticks"] is True, "legacy call changed native teams/proxy lifetime")
    outline = row["visual"]["outline"]
    if outline is not None:
        require(outline["scalar"] == 0 and outline["vector"] == row["expected_outline_color"], "legacy native outline did not use exact zero/null fallback")
    expected = calls*int(user)
    require(row["native_device_properties_created"] == len(row["native_device_properties"]) == expected and row["native_scheduler_removed_owned_properties"] is True,
        "legacy native device evaluation/lifetime differs")
    for value in row["native_device_properties"]:
        counts = value["counters"]
        require(counts["evaluations"] == counts["valid_controllers"] == counts["colors_written"] == 1 and counts["fallback_evaluations"] == 0, "legacy native device did not actually evaluate/write")


def check_scope(report):
    require(report["legacy_repnotify_manually_called_by_typed_bp"] is True and report["callback_replayed"] is True and
        report["real_legacy_repnotify_ingress_tested"] is False, "legacy typed call incorrectly certified real replicated notification")
    for key in ("team_properties_written", "observer_delegate_broadcast_by_fixture", "all_native_observers_cancelled", "replicated_team_changes_tested",
        "hardware_output_tested", "pixels_verified", "whole_character_migrated", "full_acceptance"):
        require(report[key] is False, "legacy fixture overclaims "+key)


def check_cleanup(cleanup, *, network=False, authority=False):
    for key in ("original_actor_visual_camera_profiles_restored", "original_inventory_restored", "cdo_profile_restored", "original_active_proxies_preserved",
        "owned_observers_cancelled_and_deregistered", "older_owned_proxies_collected", "owned_bare_actor_startup_proxy_collected", "native_collection_checked_after_engine_ticks", "native_observation_markers_removed", "owned_bare_actor_and_startup_proxy_destroyed"):
        require(cleanup[key] is True, "legacy fixture cleanup failed: "+key)
    roots, markers = ((0, 0) if authority else (30, 24)) if network else (22, 16)
    require(cleanup["native_latest_cancelled_proxies_retained"] == 0 and cleanup["device_roots_created"] == cleanup["device_roots_released"] == roots and
        cleanup["native_observation_markers"] == markers and cleanup["caller_roots_created"] == cleanup["caller_roots_released"] == 1, "legacy roots/proxy/marker cleanup differs")


def validate(report):
    require(report["status"] == "passed" and not report.get("error") and report["retained_character_class"] == CLASS and report["native_net_mode"] == "Standalone" and len(report["cases"]) == len(PLAN), "legacy standalone matrix incomplete")
    for row, expected in zip(report["cases"], PLAN):
        name, target, calls, profile = expected
        require((row["name"], row["target"], row["calls"], row["profile"]) == expected, "legacy plan differs")
        check_row(row, profile=profile, calls=calls, user=target == "owner")
    for index in range(0, len(PLAN), 2):
        a, b = report["cases"][index:index+2]
        require(a["visual"] == b["visual"] and [value["color"] for value in a["native_device_properties"]] == [value["color"] for value in b["native_device_properties"]], "legacy BP/Python native result differs")
    check_cleanup(report["cleanup"]); check_scope(report)
    return dict(status="passed", typed_bp_legacy_calls=8, real_repnotify_ingress_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
