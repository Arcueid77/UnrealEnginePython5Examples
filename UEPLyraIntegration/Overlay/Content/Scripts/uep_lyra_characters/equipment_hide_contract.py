"""Inherited native function routing and spawned weapon Actor state gates."""
import argparse
import json
from pathlib import Path
from .begin_play_contract import validate as begin_validate
from .initial_inventory_contract import require, CLASS
from .inventory_wait_contract import check_pooled_cues

SCENARIOS = [(name, calls, profile) for name, calls in (("equipped", 1), ("already-hidden", 1), ("repeat", 2), ("empty", 1), ("missing-manager", 1), ("native-death", 1)) for profile in ("BlueprintFallback", "Python")]


def counters(value, profile, calls, instances, actors, missing=False):
    py = profile == "Python"
    require(value == dict(python_calls=calls if py else 0, fallback_calls=0 if py else calls,
        missing_manager_noops=calls if py and missing else 0, instances=instances*calls if py else 0,
        hidden_actors=actors*calls if py else 0, null_actor_noops=0), "native inherited equipment-hide selected receiver/call counts differ")


def network_row(row, target, profile):
    require((row["target"], row["profile"]) == (target, profile) and row["actual_character_class"] == CLASS and row["instances"] > 0 and row["spawned_actor_paths"],
        "network equipment-hide actual target/equipment incomplete")
    for key in ("bp_reference_call", "native_all_hidden", "native_pawn_hidden_unchanged", "original_visibility_restored", "inventory_identity_restored", "profile_restored"):
        require(row[key] is True, "network native hide/restore differs: "+key)
    counters(row["counters"], profile, 1, row["instances"], len(row["spawned_actor_paths"]))


def scope(report):
    require(report["inherited_equipment_hide_migrated"] is True and report["ragdoll_physics_or_animation_migrated"] is False and
        report["equipment_hidden_fields_written_directly"] is False, "inherited equipment-hide migration scope differs")


def check_original_observers(row):
    before, after = set(row["original_active_observer_paths"]), set(row["final_active_observer_paths"])
    exempt = set()
    for cue in row["preexisting_native_cue_observers"]:
        require(cue["cue_class"] == "/ShooterCore/GameplayCues/GCNL_Spawning.GCNL_Spawning_C" and cue["cue"] and
            cue["observer"] in before and cue["observer"] not in exempt and cue["original_was_active"] is True and
            cue["fixture_never_cancels_or_writes"] is True, "preexisting native Cue lifecycle identity not proven")
        exempt.add(cue["observer"])
    require(row["preexisting_observers_explicitly_cancelled"] is False and row["original_character_observers_preserved"] is True and
        after-exempt == before-exempt and row["original_active_proxies_preserved"] is (before == after),
        "persistent original Character observer changed or unknown native proxy difference")


def validate(report):
    result = begin_validate(report); scope(report)
    require(report["native_ai_isolated_throughout_fixture"] is True and report["original_bot_identities_and_health_preserved"] is True and
        report["original_bots_before"] and report["original_bots_before"] == report["original_bots_after"], "native original bot identity/health controls changed")
    require(len(report["equipment_hide_cases"]) == len(SCENARIOS) and report["equipment_hide_caller_roots"] == dict(created=1, released=1), "inherited equipment-hide matrix/root cleanup incomplete")
    for row, expected in zip(report["equipment_hide_cases"], SCENARIOS):
        name, calls, profile = expected
        require((row["name"], row["calls"], row["profile"]) == expected and row["actual_character_class"] == CLASS, "native equipment-hide case identity/order differs")
        require(row["callback_manually_replayed"] is False and row["native_lethal_gas_death"] is (name == "native-death") and
            row["bp_reference_call"] is (name != "native-death"), "native inherited hide ingress/replay differs")
        for key in ("native_all_spawned_actors_hidden", "actor_was_not_rooted", "owned_new_pawn_destroyed", "no_late_script_work_after_owned_destruction",
                    "owned_team_observers_collected", "hide_quiet_after_destroy"):
            require(row[key] is True, "native equipment-hide effect/owned lifetime differs: "+key)
        require(all(value is True for value in row["cleanup"].values()), "owned equipment-hide cleanup incomplete")
        check_pooled_cues(row)
        check_original_observers(row)
        counters(row["counters"], profile, calls, row["instances_before"], len(row["spawned_actor_paths"]), name == "missing-manager")
        if name not in ("empty", "missing-manager"): require(row["spawned_actor_paths"] and row["instances_before"] > 0, "actual native spawned weapon Actors missing")
        else: require(not row["spawned_actor_paths"] and row["instances_before"] == 0, "empty/missing-manager control not actually empty")
        if name == "native-death":
            require(row["native_health_after"] == 0 and row["native_death_delay_observed"] is True and
                .1 <= row["native_death_elapsed_game_seconds"] < 1., "real native lethal GAS delayed death hide was not observed")
        else: require(row["native_pawn_hidden_unchanged"] is True and row["inventory_unchanged_by_hide"] is True, "equipment hide changed Pawn/inventory")
    return dict(result, inherited_equipment_hide_accepted=True, native_equipment_hide_pairs=6, real_lethal_death_hide_ingress=True, ragdoll_physics_or_animation_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
