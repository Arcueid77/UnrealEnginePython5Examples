"""Actual server lethal GAS -> native owner/foreign OnRep death -> Python."""
import argparse
import json
import math
from pathlib import Path
from .lifecycle_contract import validate_network as lifecycle
from .initial_inventory_contract import require, CLASS
from .ragdoll_contract import native_body, counts as ragdoll_counts
from .equipment_hide_contract import counters as hide_counts
from .death_started_contract import scope, SIGHT


def witness(value, profile, role):
    py = profile == "Python"; actor = value["actor"]; count = value["death"]
    require(value["profile"] == profile and value["native_class"] == CLASS and value["native_role"] == role and value["health_before"] > 0,
        "death network witness Profile/class/native role/readiness differs")
    for key in ("actor_was_not_rooted", "old_actor_invalid", "quiet_after_destroy", "profile_restored_or_actor_destroyed", "evidence_after_destroy_is_pod"):
        require(value[key] is True, "death network lifetime/cleanup differs: "+key)
    require(value["fixture_replayed_callback"] is value["fixture_changed_animation_physics"] is False and value["quiet_game_seconds"] >= .75,
        "death network callback replay/physics mutation/late quiet window differs")
    require(value["observer"] == dict(created=1, closed=1, active=0) and value["observer_errors"] == [] and len(value["signals"]) == 1,
        "real death signal/observer lifetime differs")
    signal, = value["signals"]
    require(signal["owning_actor"] == actor and signal["native_death_state"] == 1 and signal["montage"] in value["configured_montages"],
        "actual replicated Health death payload/state/montage differs")
    expected_senses = [item for item in value["senses_before"] if not (item == SIGHT and value["perception_systems"])]
    require(sorted(signal["senses"]) == sorted(expected_senses), "native death sense behavior differs from this world's perception system")
    expected = dict(python_calls=int(py), fallback_calls=int(not py), montage_calls=int(py), unregister_calls=int(py), missing_sense_noops=0,
        delay_requests=int(py), resumes=int(py), fallback_resumes=0, ragdoll_forwards=int(py), hide_forwards=int(py), death_forwards=int(py))
    require(all(count[key] == wanted for key, wanted in expected.items()) and count["pending"] is False,
        "real replicated death did not enter/complete exactly the selected receiver")
    require([item["event"] for item in count["trace"]] == (["montage", "sight", "delay", "resume", "ragdoll", "hide", "death"] if py else ["fallback"]),
        "replicated death prefix/continuation order differs")
    if py:
        start, resume, quantum = count["last_start"], count["last_resume"], value["maximum_world_delta"]
        elapsed = resume["game_seconds"]-start["game_seconds"]
        require(type(count["uuid"]) is int and 0 < count["uuid"] < 2**31 and .1 <= start["duration"] <= .600001 and
            start["owning_actor"] == actor and start["montage"] == signal["montage"] and start["montage_count"] == len(value["configured_montages"]) and
            0 <= start["montage_index"] < start["montage_count"] and resume["frame"] > start["frame"] and math.isfinite(elapsed) and 0 < quantum < .5 and
            start["duration"]-quantum-.0001 <= elapsed <= start["duration"]+quantum+.0001, "replicated native death Delay/montage/UUID differs")
    else: require(count["uuid"] is count["last_start"] is count["last_resume"] is None, "BP death scheduled a Python continuation")
    body = value["body"]; require(body is not None and body["equipment_instances"] >= 1 and body["weapon_paths"] and
        len(body["weapon_paths"]) == len(body["weapon_hidden"]) and all(body["weapon_hidden"]), "actual post-death replicated weapons were not hidden")
    native_body(body["physical"]); ragdoll_counts(value["ragdoll"], profile, 1)
    hide_counts(value["hide"], profile, 1, body["equipment_instances"], len(body["weapon_paths"]))


def validate(reports):
    result = lifecycle(reports)
    for peer, report in reports.items():
        scope(report)
        require(report["network_death_receiver_ingress_tested"] is True and report["ragdoll_physics_replication_tested"] is False and
            report["foreign_dying_replica_observed"] is True and report["authority_pawns_relocated_for_native_relevancy"] is True,
            "network death ingress/physics/relevancy fixture scope differs")
        if peer == "server":
            require(report["native_relevancy_teleports"] and {item["peer"] for item in report["native_relevancy_teleports"]} == {"A", "B0"} and
                all(item["native_api"] == "K2_TeleportTo" and item["succeeded"] is True and len(item["actual_location"]) == 3 and
                    all(math.isfinite(n) for n in item["actual_location"]) for item in report["native_relevancy_teleports"]), "native relevance fixture setup missing")
        for row in report["cases"]: witness(row["death_replication"], row["profile"], 3 if peer == "server" else 2)
        for row in report.get("foreign_cases", []): witness(row["death_replication"], row["death_replication"]["profile"], 1)
        total = len(report["cases"])+len(report.get("foreign_cases", []))
        require(report["death_replication_fixture_shutdown"] == dict(created=total, closed=total, active=0), "network death witness scope leaked")
    for row in reports["server"]["cases"]:
        other = "B0" if row["target"] == "A" else "A"
        own = next(item for item in reports[row["target"]]["cases"] if item["position"] == row["position"])
        foreign = next(item for item in reports[other]["foreign_cases"] if item["position"] == row["position"])
        witnesses = [item["death_replication"] for item in (row, own, foreign)]
        require(all(item["profile"] == row["profile"] and item["player_id"] == reports["server"]["player_ids"][row["target"]] for item in witnesses),
            "authority/owner/foreign death witnesses do not identify the same replicated player/Profile")
    return dict(result, network_death_receiver_ingress_tested=True, actual_death_receiver_observations=36,
        native_replica_local_ragdoll_hide_observed=True, ragdoll_physics_replication_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
