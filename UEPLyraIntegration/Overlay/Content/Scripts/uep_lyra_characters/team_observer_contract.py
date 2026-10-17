"""Native original BP listener factory/result receiver and owned proxy lifetime."""
import argparse
import json
from pathlib import Path
from .emote_audio_contract import CLASS
from uep_lyra_abilities.auto_respawn_helpers_contract import require

PLAN = [(name, target, calls, profile) for name, target, calls in (("owner-once", "owner", 1), ("owner-repeat", "owner", 2),
    ("unassigned-once", "unassigned", 1)) for profile in ("BlueprintFallback", "Python")]


def check_row(row, *, profile, calls, assigned, user):
    py = profile == "Python"; counts = row["counters"]
    require(row["profile"] == profile and row["typed_bp_listen_calls"] == calls and row["native_proxies_created"] == calls and
        row["native_proxies_active_before_cancel"] is True and row["native_proxies_inactive_after_cancel"] is True and
        row["native_collection_checked_after_engine_ticks"] is True and row["native_older_current_proxies_collected"] is True and
        row["native_previous_proxy_released_after_next_factory"] is True and row["native_latest_cancelled_proxy_retained"] == 0 and
        row["native_retained_proxy_inactive"] is True, "native original BP listener/proxy lifetime differs")
    require(counts == dict(python_calls=calls*int(py), fallback_calls=calls*int(not py), team_updates=calls*int(py and assigned), no_team_noops=calls*int(py and not assigned)),
        "selected native observer receiver branch/counter differs")
    require(row["payload"] == row["native_team_query"] and row["payload"]["team_set"] is assigned, "native observer payload differs from independent native team query")
    nested = row["team_counters"]
    require(nested["python_calls"] == calls*int(py and assigned) and nested["fallback_calls"] == calls*int(not py and assigned), "native observer did not traverse selected virtual team helper")
    expected = calls*int(assigned and user)
    require(row["native_device_properties_created"] == len(row["native_device_properties"]) == expected and row["native_scheduler_removed_owned_properties"] is True,
        "native initial-team callback device scheduler differs")
    for value in row["native_device_properties"]:
        stats = value["counters"]
        require(stats["evaluations"] == stats["valid_controllers"] == stats["colors_written"] == 1 and stats["fallback_evaluations"] == 0, "native team callback property did not execute its actual policy")


def validate(report):
    require(report["status"] == "passed" and not report.get("error") and report["retained_character_class"] == CLASS and len(report["cases"]) == len(PLAN), "native team observer standalone incomplete")
    for row, expected in zip(report["cases"], PLAN):
        name, target, calls, profile = expected
        require((row["name"], row["target"], row["calls"], row["profile"]) == expected, "native team observer case plan differs")
        check_row(row, profile=profile, calls=calls, assigned=target == "owner", user=target == "owner")
    for index in range(0, len(PLAN), 2):
        a, b = report["cases"][index:index+2]
        require(a["visual"] == b["visual"] and [value["color"] for value in a["native_device_properties"]] == [value["color"] for value in b["native_device_properties"]], "original/Python native observer software result differs")
    cleanup = report["cleanup"]
    for key in ("original_actor_visual_camera_profiles_restored", "original_inventory_restored", "cdo_profile_restored", "original_active_proxies_preserved",
        "owned_observers_cancelled_and_deregistered", "older_owned_proxies_collected", "owned_bare_actor_startup_proxy_collected",
        "native_collection_checked_after_engine_ticks", "native_observation_markers_removed", "owned_bare_actor_and_startup_proxy_destroyed"):
        require(cleanup[key] is True, "native observer cleanup failed: "+key)
    require(cleanup["native_latest_cancelled_proxies_retained"] == 0, "native owned observer survived deferred GC")
    require(cleanup["native_observation_markers"] == 16 and cleanup["device_roots_created"] == cleanup["device_roots_released"] == 22 and
        cleanup["caller_roots_created"] == cleanup["caller_roots_released"] == 1, "native observer marker/caller ownership differs")
    for key in ("callback_replayed", "team_properties_written", "observer_delegate_broadcast_by_fixture", "all_native_observers_cancelled",
        "replicated_team_changes_tested", "listener_factory_orchestration_migrated", "hardware_output_tested", "pixels_verified", "whole_character_migrated", "full_acceptance"):
        require(report[key] is False, "native observer report overclaims "+key)
    return dict(status="passed", typed_bp_listener_calls=8, native_observer_callbacks=8, native_owned_proxies_cancelled=8,
        native_latest_cancelled_proxy_retained=cleanup["native_latest_cancelled_proxies_retained"], native_device_properties=6, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
