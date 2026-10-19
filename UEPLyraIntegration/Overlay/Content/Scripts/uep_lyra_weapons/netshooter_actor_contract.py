"""Native ray geometry/RNG, reliable entry, real overlap and natural life gates."""
import argparse
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

PROFILES=("BlueprintFallback","Python")
COUNTS=(-1,0,2,12)


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native NetShooter Actor run failed")
    for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested",
                "health_properties_written","natural_hit_callback_replayed","overlap_callback_replayed","life_callback_replayed","rpc_function_overridden"):
        require(report[key] is False,"NetShooter scope overclaim: "+key)
    require(report["controlled_hit_method_entries"] and report["production_profiles_restored"] and report["all_test_actors_destroyed"] and report["original_player_health_unchanged"],"native NetShooter control/cleanup proof missing")
    require(len(report["ray_pairs"])==len(COUNTS),"native NetShooter ray matrix incomplete")
    for row in report["ray_pairs"]:
        require(row["number"] in COUNTS and row["same_components"] and row["same_start"] and row["same_next_native_random"],"original NetShooter ray/component/RNG semantics differ")
        for side in ("blueprint","python"):
            value=row[side];require(value["native_hit_body_count"]==1 and value["duplicate_hit_do_once_blocked"] and value["native_rpc_flags_preserved"],"native authority/DoOnce/RPC state changed")
            require(value["ray_components"]==len(value["spawn_events"]) and value["ray_components"]<=max(0,row["number"]+1),"native inclusive-loop/ray count differs")
            for event in value["spawn_events"]:
                require(event["native_geometry_matches"] and event["native_template_matches"] and event["sphere_hidden"],"actual native strand geometry/template/hide differs")
    require(len(report["natural_cases"])==2 and {row["profile"] for row in report["natural_cases"]}==set(PROFILES),"real projectile hit matrix incomplete")
    for row in report["natural_cases"]:
        require(row["native_hit_body_count"]==1 and row["native_moving_samples"]>=2 and row["initial_speed"]==2500. and row["gravity_scale"]==.5,"original native projectile hit/movement missing")
        require(row["ray_components_before_end"]>=1 and row["destroyed_by_native_life_delay"] and row["life_elapsed"]+row["hit_frame_delta"]>=11.98,"original native LifeTime Delay/destruction missing")
    require(len(report["overlap_cases"])==2 and {row["profile"] for row in report["overlap_cases"]}==set(PROFILES),"real native strand overlap matrix incomplete")
    for row in report["overlap_cases"]:
        require(row["native_overlap_callbacks"]>=1 and row["native_source_matches_instigator"] and row["native_rpc_body_count"]==1 and row["native_template_matches"],"native ray overlap/weak binding/source/RPC body missing")
        require(row["health_after"]<row["health_before"] and row["native_health_damage_observed"],"original native level0 effect did not damage the target")
    return dict(status="passed",native_ray_pairs=4,natural_projectile_cases=2,native_overlap_profiles=2,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
