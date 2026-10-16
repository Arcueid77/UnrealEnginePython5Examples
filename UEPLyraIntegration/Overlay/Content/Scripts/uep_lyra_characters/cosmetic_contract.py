"""Native cosmetic component lifecycle comparisons; random streams not replayed."""
import argparse
import json
from pathlib import Path

MANNY = "/Game/Characters/Cosmetics/B_Manny.B_Manny_C"
QUINN = "/Game/Characters/Cosmetics/B_Quinn.B_Quinn_C"
PLAN = (("single-manny", (MANNY,)), ("single-quinn", (QUINN,)),
        ("two-parts", (MANNY, QUINN)), ("three-parts", (QUINN, MANNY, QUINN)))


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None, "native cosmetic report failed")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "animation_assets_modified",
                  "part_actors_spawned_by_python", "part_arrays_written", "beginplay_handler_replayed", "rng_seed_or_result_written"):
        require(report[field] is False, "unsupported native cosmetic claim: "+field)
    require([row["name"] for row in report["cases"]] == [name for name, parts in PLAN], "native selection matrix incomplete")
    trials = []
    for row, (_, parts) in zip(report["cases"], PLAN):
        for side in ("blueprint", "python"):
            value = row[side]; trials.append(value)
            require(value["chosen_class"] == parts[value["native_actor_count"] % len(parts)], "native actor-count choice differs")
        require(row["blueprint"]["chosen_class"] == row["python"]["chosen_class"], "original/Python deterministic choice differs")
    random = report["random_trials"]
    require(16 <= len(random) <= 64 and len(random) % 2 == 0, "native random branch trials incomplete")
    for side in ("BlueprintFallback", "Python"):
        values = [row["chosen_class"] for row in random if row["profile"] == side]
        require(set(values) == {MANNY, QUINN}, "native random original/Python did not exercise both choices")
    trials.extend(random)
    for value in trials:
        part = value["native_part"]
        require(value["native_type_preserved"] and value["native_beginplay_observed"] and value["native_owner_preserved"] and
                value["native_cleanup_restored_original_ids"] and value["profile_roundtrip_preserved_part"] and
                part["cls"] == part["actor_class"] == value["chosen_class"] and part["actor"] and part["child"] and
                part["collision_mode"] == 0 and part["actor_collision"] is False and part["attached_pawn"] == value["pawn"],
                "native cosmetic spawn/attachment/lifetime proof missing")
        count = value["counters"]["random_selections" if value["kind"] == "random" else "selections"]
        require(count == int(value["profile"] == "Python"), "native BeginPlay did not execute selected Profile exactly once")
    require(report["policy_shutdown"]["errors"] == [] and report["original_player_restored"], "native cosmetic policy error/fixture leak")
    return dict(status="passed", bounded_runtime_acceptance=True, deterministic_pairs=len(PLAN), random_trials=len(random),
        random_sequence_replay_claimed=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
