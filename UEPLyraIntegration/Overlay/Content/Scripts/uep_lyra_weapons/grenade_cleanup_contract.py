"""Independent actual native one-shot timer/collision-ignore transition gate."""
import argparse
import json
import math
from pathlib import Path

CLASS="/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C"
PLAN=tuple((name,profile) for name in ("character","non-character-pawn","no-instigator") for profile in ("BlueprintFallback","Python"))


def require(value,message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native Grenade cleanup report failed")
    for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","cleanup_callback_replayed","timer_state_written","health_properties_written","raw_velocity_written","quantitative_movement_parity_tested","fuse_detonate_damage_business_migrated"):
        require(report[key] is False,"native cleanup scope overclaim: "+key)
    for key in ("original_native_timer_used","test_grenade_collision_disabled","production_classes_restored","all_pawn_health_unchanged","source_capsule_ignores_restored"):
        require(report[key] is True,"native cleanup witness missing: "+key)
    require(report["observation_errors"]==[] and report["remaining_test_actors"]==0 and len(report["cases"])==len(PLAN),"native cleanup matrix/teardown incomplete")
    for row,(name,profile) in zip(report["cases"],PLAN):
        require((row["name"],row["profile"])==(name,profile) and row["class"]==CLASS and row["quiet_ticks"]>=20,"native cleanup identity/quiet matrix differs")
        require(row["actual_timer_callback_count"]==1 and row["actor_destroyed"] is True and row["native_grenade_alive_until_cleanup"] is True,"actual one-shot callback/lifetime missing")
        event=row["event"];before,after=event["before"],event["after"]
        require(event["profile"]==profile and event["native_timer_callback"] is True,"production native timer did not select required Profile")
        require(math.isfinite(event["elapsed"]) and math.isfinite(row["max_observed_frame"]) and
            .16-.000001<=event["elapsed"]<=.16+max(.05,2.*row["max_observed_frame"]),"actual native 0.16-second timer timing differs")
        require(before["rotation_follows_velocity"] is False and after["rotation_follows_velocity"] is True,"native projectile rotation flag transition missing")
        instigator=row["instigator"]
        require(after["mesh_ignores"]==sorted(value for value in before["mesh_ignores"] if value!=instigator),"native mesh unignore removed wrong Actors")
        if name=="character":
            require(row["instigator_is_character"] is True and row["actor"] in before["capsule_ignores"],"original BeginPlay did not establish actual reverse capsule ignore")
            require(after["capsule_ignores"]==sorted(value for value in before["capsule_ignores"] if value!=row["actor"]),"native character capsule unignore differs")
        else: require(row["instigator_is_character"] is False and before["capsule_ignores"] is None and after["capsule_ignores"] is None,"non-Character cast path differs")
        if name=="no-instigator": require(instigator is None,"native null Instigator path missing")
        elif name=="character": require(instigator is not None and instigator in before["mesh_ignores"],"original native initial mesh ignore missing")
        else: require(instigator is not None and instigator not in before["mesh_ignores"],"original BeginPlay character-only ignore setup differs")
        py=profile=="Python";expected=dict(python_calls=int(py),fallback_calls=int(not py),capsule_unignores=int(py and name=="character"),
            non_character_skips=int(py and name!="character"),mesh_unignores=int(py),rotation_writes=int(py),invalid_capsule_noops=0,invalid_mesh_noops=0,invalid_movement_noops=0)
        require(event["stats"]==expected,"selected production cleanup branch counts differ")
    return dict(status="passed",native_actors=6,actual_native_timer_callbacks=6,native_collision_rotation_transitions=6,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True);args=parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
