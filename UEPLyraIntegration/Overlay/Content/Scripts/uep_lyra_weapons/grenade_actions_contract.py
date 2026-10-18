"""Independent native ordinary-entry teleport/destroy transition gate."""
import argparse
import json
import math
from pathlib import Path

CLASS="/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C"
PLAN=tuple((name,profile) for name in ("unit-forward","nonunit-forward","zero-speed","invalid-trail") for profile in ("BlueprintFallback","Python"))


def require(value,message):
    if not value: raise RuntimeError(message)
def close(a,b,tolerance=.0001):
    require(len(a)==len(b) and all(math.isfinite(float(x)) and math.isfinite(float(y)) and abs(x-y)<=tolerance for x,y in zip(a,b)),"native Actor action numeric result differs")


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native Actor action report failed")
    for field in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","begin_play_replayed","native_completion_delegate_replayed","health_properties_written","raw_velocity_written","quantitative_flight_physics_tested","native_trail_completion_tested","fuse_detonate_damage_migrated"):
        require(report[field] is False,"Actor action scope overclaim: "+field)
    for field in ("ordinary_action_entries_called_by_fixture","test_grenade_collision_disabled","all_pawn_health_unchanged","production_classes_unchanged","native_warmup_ready","warmup_actor_destroyed"):
        require(report[field] is True,"native Actor action witness missing: "+field)
    require(report["native_zero_velocity_entry"]=="ProjectileMovement.SetVelocityInLocalSpace" and report["remaining_test_actors"]==0 and report["quiet_ticks"]>=20 and len(report["cases"])==len(PLAN),"Actor action matrix/cleanup incomplete")
    require(report["warmup_actual_active_ticks"]>=3,"native common system/PSO readiness required")
    for row,(name,profile) in zip(report["cases"],PLAN):
        require((row["name"],row["profile"])==(name,profile) and row["class"]==CLASS and row["native_destroyed"] is True,"native Actor identity/destroy entry missing")
        before,after=row["before"],row["after"];speed=math.sqrt(sum(value*value for value in before["velocity"]))
        require(math.isfinite(after["conserved"]) and abs(after["conserved"]-speed)<=.0001,"original speed must be saved before validity guard")
        close(after["rotation"],before["rotation"])
        invalid=name=="invalid-trail"
        if invalid:
            require(before["trail_valid"] is False and after["trail_valid"] is False,"actual destroyed-trail branch missing")
            close(after["location"],before["location"]);close(after["velocity"],before["velocity"])
            require(after["matching_components"]==before["matching_components"] and after["movement_active"]==before["movement_active"],"invalid trail must stop before teleport/activate/VFX")
        else:
            require(before["trail_valid"] is True and before["trail_active"] is True and after["trail_valid"] is True and before["trail"]!=after["trail"] and type(row["old_trail_active_after"]) is bool,"native original trail/new VFX replacement differs")
            close(after["location"],row["destination"]);close(after["velocity"],[value*speed/2. for value in row["forward"]])
            require(after["movement_active"] is True and after["matching_components"]==before["matching_components"]+1,"native movement activation/new trail count missing")
        if name=="zero-speed": close(before["velocity"],[0.,0.,0.])
        if name=="nonunit-forward": require(abs(math.sqrt(sum(value*value for value in row["forward"]))-2.)<.0001,"non-normalized forward case missing")
        py=profile=="Python";wanted=dict(teleport_python=int(py),teleport_fallback=int(not py),speed_reads=int(py),conserved_writes=int(py),missing_movement_reads=0,
            invalid_trail_noops=int(py and invalid),trail_deactivations=int(py and not invalid),native_locations=int(py and not invalid),movement_activations=int(py and not invalid),
            velocity_writes=int(py and not invalid),missing_movement_writes=0,vfx_calls=int(py and not invalid),destroy_python=int(py),destroy_fallback=int(not py),native_destroy_calls=int(py))
        require(row["stats"]==wanted,"selected Actor action production branch counts differ")
        require(row["vfx_helper_calls"]==(1 if invalid else 2),"teleport did not call actual current VFX helper exactly once")
    for original,python in zip(report["cases"][::2],report["cases"][1::2]):
        # Native Deactivate may keep IsActive until particles complete; never
        # substitute DeactivateImmediate or pretend this proves completion.
        require(original["old_trail_active_after"]==python["old_trail_active_after"],"native old-trail state differs on common-ready paired trials")
    return dict(status="passed",native_actor_trials=8,native_teleport_entries=8,native_destroy_entries=8,invalid_trail_guards=2,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True);args=parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
