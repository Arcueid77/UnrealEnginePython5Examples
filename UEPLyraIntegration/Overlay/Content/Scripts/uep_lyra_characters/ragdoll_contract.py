"""Native body state and actual additive velocity-change semantics, not pixels."""
import argparse
import json
import math
from pathlib import Path
from .equipment_hide_contract import validate as hide_validate
from .initial_inventory_contract import require, CLASS
from .inventory_wait_contract import check_pooled_cues

SCENARIOS = [(name, calls, profile) for name, calls in (("stationary", 1), ("moving", 1), ("zero-strength", 1), ("repeat", 2)) for profile in ("BlueprintFallback", "Python")]


def impulse(velocity, strength):
    square = sum(value*value for value in velocity)
    return [value+(value/math.sqrt(square)*strength if square >= .0001 else 0.) for value in velocity]


def native_body(value):
    require(value["mesh"] and value["bone"] and value["collision_profile"] == "Ragdoll" and value["simulating"] is True and
        len(value["velocity"]) == 3 and all(math.isfinite(n) for n in value["velocity"]), "native Ragdoll skeletal body/profile not observed")


def counts(values, profile, calls):
    py = profile == "Python"
    for key, expected in dict(python_calls=calls if py else 0, fallback_calls=0 if py else calls,
        collision_calls=calls if py else 0, simulation_calls=calls if py else 0, impulse_calls=calls if py else 0, missing_mesh_noops=0).items():
        require(values[key] == expected, "native Ragdoll selected receiver/count differs: "+key)
    require(values["trace"] == ["collision", "simulation", "impulse"]*calls if py else values["trace"] == [], "native Ragdoll API order differs")
    if py:
        last = values["last_call"]
        require(len(last["velocity"]) == len(last["impulse"]) == 3 and all(math.isfinite(n) for n in last["velocity"]+last["impulse"]) and
            last["collision_profile"] == "Ragdoll" and last["include_self"] is True and last["velocity_change"] is True and last["normalize_tolerance"] == .0001 and
            all(abs(a-b) < .0001 for a, b in zip(last["impulse"], impulse(last["velocity"], last["strength"]))), "native Ragdoll policy parameters/formula differ")


def scope(report):
    require(report["ragdoll_orchestration_migrated"] is True and report["native_physics_or_animation_implementation_changed"] is False and
        report["physics_properties_written_directly"] is False, "Ragdoll project/native implementation boundary differs")


def validate(report):
    result = hide_validate(report); scope(report)
    require(len(report["ragdoll_cases"]) == len(SCENARIOS) and report["ragdoll_caller_roots"] == dict(created=1, released=1), "native Ragdoll matrix/caller cleanup incomplete")
    for row, expected in zip(report["ragdoll_cases"], SCENARIOS):
        name, calls, profile = expected
        require((row["name"], row["calls"], row["profile"]) == expected and row["actual_character_class"] == CLASS and row["physics_properties_written_directly"] is False,
            "native Ragdoll case identity/scope differs")
        for key in ("bp_reference_call", "native_pawn_hidden_unchanged", "inventory_unchanged", "actor_was_not_rooted", "owned_strength_restored_before_destroy",
            "owned_new_pawn_destroyed", "no_late_script_work_after_owned_destruction", "owned_team_observers_collected", "original_active_proxies_preserved", "ragdoll_quiet_after_destroy"):
            require(row[key] is True, "native Ragdoll ownership/side effects differ: "+key)
        require(all(value is True for value in row["cleanup"].values()), "owned Ragdoll cleanup failed")
        native_body(row["native_after"]); counts(row["counters"], profile, calls); check_pooled_cues(row)
        native_body(row["native_after_physics_step"])
        prepared = name != "stationary"
        require(len(row["input_velocity"]) == 3 and all(math.isfinite(n) for n in row["input_velocity"]), "native Ragdoll input vector invalid")
        require(row["native_launch_producer"] is prepared and row["known_physics_velocity_prepared_via_native_api"] is prepared and
            row["single_body_constraint_free_native_control"] is prepared and row["fixture_gravity_and_damping_disabled_via_native_api"] is prepared and
            row["native_physics_frames_elapsed"] >= 2, "native Ragdoll producer/fixture/physics step scope differs")
        if prepared:
            require(row["input_velocity"][0] > 100. and row["native_before"]["simulating"] is True and row["native_before"]["velocity"] == [3., 4., 5.], "native moving/known-body inputs not actually established")
            wanted = [initial+calls*change for initial, change in zip(row["native_before"]["velocity"], impulse(row["input_velocity"], row["strength"]))]
            require(all(abs(a-b) < .02 for a, b in zip(row["native_after_physics_step"]["velocity"], wanted)), "actual next-physics-step bVelChange impulse differs from original BP formula")
        require((row["strength"] == 0.) is (name == "zero-strength"), "native zero-strength/default input differs")
    for row in report["equipment_hide_cases"][-2:]:
        counts(row["natural_ragdoll_counters"], row["profile"], 1); native_body(row["natural_ragdoll_physical"])
    return dict(result, native_ragdoll_orchestration_accepted=True, native_ragdoll_pairs=4, natural_native_death_ragdoll_pairs=1, native_physics_or_animation_implementation_changed=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
