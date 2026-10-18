"""Native blocking movement -> Hit routing; non-detonating branches only."""
import argparse
import json
import math
from pathlib import Path

CLASS="/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C"
PLAN=tuple((name,profile) for name in ("invalid-wall","same-team") for profile in ("BlueprintFallback","Python"))


def require(value,message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native Hit report failed")
    for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","hit_callback_replayed","health_properties_written","raw_velocity_written",
        "enemy_hit_detonation_tested","native_rpc_detonate_body_migrated","audio_playback_tested","quantitative_flight_physics_tested"):
        require(report[key] is False,"Hit scope overclaim: "+key)
    for key in ("native_blocking_sweep_used","all_pawn_health_unchanged","test_actors_destroyed","bot_pose_restored","production_classes_restored"):
        require(report[key] is True,"native Hit witness/cleanup missing: "+key)
    require(report["observation_errors"]==[] and report["quiet_ticks"]>=20 and len(report["cases"])==len(PLAN),"native Hit matrix/quiet interval incomplete")
    for row,(name,profile) in zip(report["cases"],PLAN):
        require((row["name"],row["profile"])==(name,profile) and row["class"]==CLASS and row["native_hits"]==1 and row["actor_destroyed"] is True,"actual native blocking Hit count/class differs")
        event=row["event"]
        require(event["profile"]==profile and event["other"]==row["expected_other"] and event["comparison"]==(2 if name=="invalid-wall" else 0),"native other Actor/team branch differs")
        require(event["native_generated_callback"] is True and event["my_component"]==row["mesh"] and event["other_component"] is not None,"actual native component Hit payload missing")
        require(len(event["location"])==3 and all(math.isfinite(value) for value in event["location"]),"native Hit location invalid")
        require(event["fuse_exists_before"] is True and event["fuse_exists_after"] is True,"same/invalid contact must not cancel native fuse")
        py=profile=="Python";wanted=dict(python_hits=int(py),fallback_hits=int(not py),team_queries=int(py),invalid_team_subsystem_defaults=0,
            different_team_hits=0,other_team_hits=int(py),native_timer_clears=0,handle_writes=0,native_detonate_requests=0,native_sound_requests=int(py))
        require(event["stats"]==wanted,"actual production Hit non-detonating branch counts differ")
    return dict(status="passed",actual_native_blocking_hit_trials=4,same_team_hits=2,invalid_team_hits=2,enemy_hit_detonation_tested=False,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True);args=parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
