"""Real native observer activations on both replicated Pawn identities in three worlds."""
import argparse
import json
from pathlib import Path
from .team_observer_contract import check_row, require

PLAN = [(name, peer, calls, profiles[peer]) for name, calls, profiles in (
    ("opposing", 1, dict(A="Python", B0="BlueprintFallback")), ("swapped", 1, dict(A="BlueprintFallback", B0="Python")),
    ("opposing-repeat", 2, dict(A="Python", B0="BlueprintFallback")), ("swapped-repeat", 2, dict(A="BlueprintFallback", B0="Python"))) for peer in ("A", "B0")]


def validate(server, a, b, *, listener=False):
    reports = {"server": server, "A": a, "B0": b}
    require(server["server_waited_for_client_process_exit"] is True and server["all_cleanup_frozen_before_release"] is True and len(set(server["player_ids"].values())) == 2, "native observer clients/cleanup/server-last incomplete")
    for peer, report in reports.items():
        authority = peer == "server"
        require(report["status"] == "passed" and not report.get("error") and report["run_id"] == server["run_id"] and report["peer"] == peer and
            report["native_net_mode"] == ("DedicatedServer" if authority else "Client") and len(report["cases"]) == len(PLAN), "native observer peer modes/matrix incomplete")
        for row, expected in zip(report["cases"], PLAN):
            name, target, calls, profile = expected
            require((row["name"], row["target"], row["calls"], row["profile"]) == expected and row["native_role"] == (3 if authority else (2 if target == peer else 1)), "native observer target/role differs")
            check_row(row, profile=profile, calls=calls, assigned=True, user=target == peer)
        cleanup = report["cleanup"]
        for key in ("original_actor_visual_camera_profiles_restored", "original_inventory_restored", "cdo_profile_restored", "original_active_proxies_preserved",
            "owned_observers_cancelled_and_deregistered", "older_owned_proxies_collected", "owned_bare_actor_startup_proxy_collected", "native_collection_checked_after_engine_ticks", "native_observation_markers_removed"):
            require(cleanup[key] is True, "native observer peer cleanup failed: "+key)
        require(cleanup["native_latest_cancelled_proxies_retained"] == 0, "native peer owned observer survived deferred GC")
        require(cleanup["device_roots_created"] == cleanup["device_roots_released"] == (0 if authority else 30) and
            cleanup["native_observation_markers"] == (0 if authority else 24) and cleanup["caller_roots_created"] == cleanup["caller_roots_released"] == 1, "native observer peer root/marker ownership differs")
        for key in ("callback_replayed", "team_properties_written", "observer_delegate_broadcast_by_fixture", "all_native_observers_cancelled", "replicated_team_changes_tested",
            "hardware_output_tested", "pixels_verified", "whole_character_migrated", "full_acceptance"):
            require(report[key] is False, "native observer peer overclaims "+key)
        require(report["listener_factory_orchestration_migrated"] is listener, "native listener peer migration scope differs")
        if not authority: require(report["player_id"] == server["player_ids"][peer], "native observer local identity differs")
    return dict(status="passed", native_observer_callbacks=36, same_bp_two_instances_three_worlds=True, native_proxy_cancellation_gc=True, replicated_team_changes_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate(*(json.loads((root/(name+".json")).read_text(encoding="utf-8-sig")) for name in ("server", "A", "B0")))))
