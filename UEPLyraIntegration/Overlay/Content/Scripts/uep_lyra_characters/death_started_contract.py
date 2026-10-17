"""Real Health callback, native montage/sight state and weak native Delay gates."""
import argparse
import json
import math
from pathlib import Path
from .ragdoll_contract import validate as ragdoll_validate, counts as ragdoll_counts, native_body
from .equipment_hide_contract import counters as hide_counts
from .inventory_wait_contract import check_pooled_cues
from .initial_inventory_contract import require, CLASS

SCENARIOS = [(name, profile) for name in ("default", "single-montage", "empty-montages", "destroy-pending", "switch-pending") for profile in ("BlueprintFallback", "Python")]
SIGHT = "/Script/AIModule.AISense_Sight"


def check_entry(row, profile, *, resumed, current=None):
    current = current or profile; py = profile == "Python"; value = row["death_started_counters"]
    actor_path = row.get("actor_path", row.get("native_actor_path"))
    require(row["death_signal_observer"] == dict(created=1, closed=1, active=0, callbacks=1, errors=[]) and row["signal_actual_owning_actor"] == actor_path,
        "actual native Health delegate witness/payload/cleanup differs")
    expected = dict(python_calls=int(py), fallback_calls=int(not py), montage_calls=int(py), unregister_calls=int(py), missing_sense_noops=0,
        delay_requests=int(py), resumes=int(py and resumed), fallback_resumes=int(py and resumed and current == "BlueprintFallback"),
        ragdoll_forwards=int(py and resumed), hide_forwards=int(py and resumed), death_forwards=int(py and resumed))
    require(all(value[key] == wanted for key, wanted in expected.items()) and value["pending"] is (py and not resumed), "native death entry/continuation count differs")
    events = [item["event"] for item in value["trace"]]
    require(events == (["montage", "sight", "delay"]+(["resume", "ragdoll", "hide", "death"] if resumed else []) if py else ["fallback"]), "native death prefix/continuation ordering differs")
    require(row["health_delegate_manually_replayed"] is False and row["native_prefix_health"] == 0 and
        SIGHT in row["native_sight_sources_before"] and SIGHT not in row["native_prefix_sight_sources"] and SIGHT not in row["native_sight_sources_after"],
        "real lethal Health ingress/native sight removal not observed")
    expected_senses = sorted(value for value in row["native_sight_sources_before"] if value != SIGHT)
    require(sorted(row["native_prefix_sight_sources"]) == sorted(row["native_sight_sources_after"]) == expected_senses,
        "death sight unregister changed another native sense")
    configured, montage = row["configured_death_montages"], row["native_prefix_current_montage"]
    require(montage in configured if configured else montage is None, "native current death montage differs from actual configured array")
    if py:
        start = value["last_start"]; require(type(value["uuid"]) is int and 0 < value["uuid"] < 2**31 and
            start["owning_actor"] == actor_path and start["montage_count"] == len(configured) and
            start["montage"] == montage and .1 <= start["duration"] <= .600001 and
            (0 <= start["montage_index"] < len(configured) if configured else start["montage_index"] == 0), "native random montage/Delay input or actual Actor payload differs")
        if resumed:
            resume = value["last_resume"]; elapsed = resume["game_seconds"]-start["game_seconds"]; quantum = row["maximum_observed_world_delta"]
            require(math.isfinite(elapsed) and 0 < quantum < .5 and
                start["duration"]-quantum-.0001 <= elapsed <= start["duration"]+quantum+.0001 and resume["frame"] > start["frame"],
                "native death Delay did not resume at its game-clock/engine-frame boundary")
    else: require(value["uuid"] is None and value["last_start"] is value["last_resume"] is None, "original BP death entered Python scheduling")


def scope(report):
    require(report["death_started_business_migrated"] is True and report["death_receiver_called_by_fixture"] is False and
        report["death_native_delay_backend"] == "Delay" and report["death_python_ticker_or_rooting"] is False and
        report["empty_death_endpoint_retained"] is True, "death migration/native/empty-endpoint scope differs")


def validate(report):
    result = ragdoll_validate(report); scope(report)
    for row in report["equipment_hide_cases"][-2:]: check_entry(row, row["profile"], resumed=True)
    require(len(report["death_started_cases"]) == len(SCENARIOS), "native death lifecycle/Profile/montage matrix incomplete")
    for row, expected in zip(report["death_started_cases"], SCENARIOS):
        name, profile = expected; destroyed = name == "destroy-pending"; current = ("Python" if profile == "BlueprintFallback" else "BlueprintFallback") if name == "switch-pending" else profile
        require((row["death_case"], row["entry_profile"]) == expected and row["actual_character_class"] == CLASS and row["profile_before_resume"] == current,
            "native death case identity/Profile differs")
        require(row["native_lethal_gas_death"] is True and row["native_health_after"] == 0 and row["destroyed_pending"] is destroyed and row["callback_receiver_called_by_fixture"] is False,
            "native death producer/destruction scope differs")
        for key in ("actor_was_not_rooted", "owned_new_pawn_destroyed", "no_late_script_work_after_owned_destruction", "owned_team_observers_collected",
            "original_active_proxies_preserved", "montage_configuration_restored_before_destroy", "death_started_quiet_after_destroy"):
            require(row[key] is True, "native death owned cleanup/configuration differs: "+key)
        require(all(value is True for value in row["cleanup"].values()), "owned death resources not destroyed")
        check_pooled_cues(row); check_entry(row, profile, resumed=not destroyed, current=current)
        if destroyed:
            require(row["destroyed_owner_observed_for_game_seconds"] >= .75 and row["no_ragdoll_after_destroy"] is True and row["hide_quiet_after_destroy"] is True,
                "destroyed owner was not observed beyond the maximum native death Delay")
        else:
            native_body(row["natural_ragdoll_physical"]); ragdoll_counts(row["natural_ragdoll_counters"], current, 1)
            hide_counts(row["counters"], current, 1, row["instances_before"], len(row["spawned_actor_paths"]))
            require(row["native_all_spawned_actors_hidden"] is True, "real native post-death weapons not hidden")
        if name == "single-montage": require(len(row["configured_death_montages"]) == 1, "single native montage control missing")
        if name == "empty-montages": require(not row["configured_death_montages"], "empty native montage control missing")
    return dict(result, native_death_started_orchestration_accepted=True, native_death_started_pairs=5, native_destroyed_death_delay_stopped=True,
        native_pending_death_profile_switches=True, network_death_receiver_ingress_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
