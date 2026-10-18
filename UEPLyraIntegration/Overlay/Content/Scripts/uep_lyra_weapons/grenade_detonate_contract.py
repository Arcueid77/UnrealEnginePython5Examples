"""Independent checks for native RPC/fuse/Hit -> explosion body parity."""
import argparse
import json
import math
from pathlib import Path

CLASS = "/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C"
PLAN = tuple((name, profile) for name in ("empty-rpc", "enemy-rpc", "occluded-rpc", "friendly-rpc", "empty-fuse", "enemy-hit")
             for profile in ("BlueprintFallback", "Python"))


def require(value, message):
    if not value:
        raise RuntimeError(message)


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_mode"] == "Standalone", "native explosion report failed")
    for key in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "health_properties_written",
                "rpc_function_overridden", "body_callback_replayed", "particle_completion_replayed", "audio_playback_tested", "quantitative_flight_tested"):
        require(report[key] is False, "explosion scope overclaim: "+key)
    require(report["production_classes_restored"] and report["test_actors_destroyed"] and report["view_target_restored"] and report["observation_errors"] == [], "explosion observers/cleanup failed")
    require(len(report["cases"]) == len(PLAN), "native explosion matrix incomplete")
    for row, (name, profile) in zip(report["cases"], PLAN):
        require((row["name"], row["profile"], row["class"]) == (name, profile, CLASS), "native explosion identity differs")
        require(row["body_calls"] == 1 and row["repeat_body_calls"] == 1, "native RPC DoOnce did not suppress duplicate body")
        require(row["rpc_flags_preserved"] and row["hidden"] and not row["movement_active"], "native RPC/visual/movement result differs")
        require(row["native_role"] == 3 and row["actor_destroyed"] and row["native_trail_valid"], "native authority/trail/cleanup witness missing")
        require(row["other_pawn_health_unchanged"], "explosion changed an unintended Pawn")
        require(row["native_overlap_pawns_before"] == ([] if name.startswith("empty") else [row["victim"]]), "native target isolation differs")
        require(row["stats"]["python_bodies"] == int(profile == "Python") and row["stats"]["fallback_bodies"] == int(profile == "BlueprintFallback"), "actual selected body routing differs")
        if profile == "Python":
            require(row["stats"]["cues"] == 1 and row["stats"]["overlaps"] == 1 and row["stats"]["trail_bindings"] == 1, "Python native cue/overlap/weak-binding path incomplete")
            require(row["stats"]["traces"] == (0 if name.startswith("empty") else 1), "native overlap/trace target count differs")
        if not name.startswith("empty"):
            require(row["context_hit"]["actor"] == row["expected_hit_actor"] and math.isfinite(row["context_hit"]["distance"]), "native GAS hit context differs")
        if name in ("enemy-rpc", "enemy-hit"):
            require(row["team_comparison"] == 1 and row["health_before"] > row["health_after"] >= 0, "actual native enemy GAS damage missing")
        elif name in ("friendly-rpc", "occluded-rpc"):
            require(row["health_before"] == row["health_after"] > 0, "native team/occluder damage control differs")
        else:
            require(row["all_health_unchanged"], "empty explosion changed Pawn health")
        if name == "empty-fuse":
            require(row["trigger"] == "native-actor-timer" and row["rpc_requested_by_fixture"] is False, "natural fuse replaced by direct request")
            require(row["fuse_seconds"] <= row["body_elapsed"] < row["fuse_seconds"]+1., "native fuse did not fire at original world time")
        if name == "empty-rpc":
            require(row["native_trail_active_before_rpc"], "completion scenario did not begin with an active native system")
            require(row["controlled_native_niagara_completion"] and row["native_finish_callbacks"] == [row["finished_component"]], "native weak Niagara delegate did not invoke exact Actor destroy event once")
        if name == "enemy-hit":
            require(row["native_hits"] == 1 and row["hit_other_is_target"] and row["fuse_before_hit"] and not row["fuse_after_hit"], "native enemy blocking contact/fuse clear missing")
            require(row["trigger"] == "native-blocking-sweep" and not row["rpc_requested_by_fixture"], "enemy hit replaced by direct RPC request")
    for first, second in zip(report["cases"][::2], report["cases"][1::2]):
        require(first["name"] == second["name"], "profile pairing differs")
        require(math.isclose(first["health_before"]-first["health_after"], second["health_before"]-second["health_after"], abs_tol=0.05), "original/Python native damage differs")
    return dict(status="passed", native_explosion_trials=len(PLAN), native_enemy_damage_trials=4,
                original_rpc_do_once_verified=True, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
