"""Native Actor/attached Niagara parameter-store differential report gate."""
import argparse
import json
import math
from pathlib import Path

CLASS="/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C"
TRAIL="/Game/Effects/Particles/Explosion/NS_Grenade_Trail.NS_Grenade_Trail"
PLAN=tuple((name,profile) for name in ("other-team","team1","no-instigator") for profile in ("BlueprintFallback","Python"))


def require(value,message):
    if not value: raise RuntimeError(message)
def close(a,b):
    require(len(a)==len(b) and all(math.isfinite(float(x)) and abs(x-y)<=.000001 for x,y in zip(a,b)),"actual native Niagara color/transform differs")


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native Grenade VFX report failed")
    for field in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","actor_collision_fuse_explosion_damage_migrated","projectile_physics_tested","projectile_replication_tested","particle_rendering_tested","health_properties_written","team_properties_written","begin_play_replayed"):
        require(report[field] is False,"Grenade VFX scope overclaim: "+field)
    for field in ("native_deferred_spawn_finish","original_blueprint_begin_calls_helper","repeat_ordinary_helper_call_by_fixture","grenade_actors_destroyed_before_world_tick","profile_classes_restored","all_pawn_health_unchanged","native_warmup_ready","warmup_actor_destroyed"):
        require(report[field] is True,"native Grenade VFX witness missing: "+field)
    require(report["observation_errors"]==[] and report["remaining_test_actors"]==0 and report["quiet_ticks"]>=20 and len(report["cases"])==len(PLAN),"native VFX matrix/cleanup incomplete")
    require(report["warmup_actual_active_ticks"]>=3,"common native Niagara readiness not observed before paired trials")
    for row,(name,profile) in zip(report["cases"],PLAN):
        require((row["name"],row["profile"])==(name,profile) and row["class"]==CLASS,"native Actor type/Profile differs")
        wanted_team=row["team_id"]
        require((wanted_team>=0 and wanted_team!=1 if name=="other-team" else wanted_team==(1 if name=="team1" else -1)) and row["actor_destroyed"] is True,"actual native team/actor cleanup missing")
        color=[1.,.05,.01,1.] if name=="team1" else [.01,.15,1.,1.]
        require(row["initial"]["component"]!=row["repeated"]["component"],"original helper must spawn another component,not reuse old trail")
        for index,step in enumerate((row["initial"],row["repeated"]),1):
            require(step["helper_calls"]==index and step["matching_components"]==index and step["asset"]==TRAIL and step["parent"]==row["mesh"],"native Begin/helper count/asset/attachment differs")
            # Native SpawnSystemAttached deliberately stores bAutoActivate=False,
            # then explicitly Activates when the request argument is True.
            require(step["auto_destroy"] is False and step["active"] is True and step["auto_activate"] is False,"native Niagara lifecycle options differ")
            close(step["relative_location"],[0.,0.,0.]);close(step["relative_rotation"],[0.,0.,0.]);close(step["relative_scale"],[1.,1.,1.])
            close(step["actor_team_color"],color);close(step["parameter_store_color"],color)
            require(step["parameter_name"] in ("Team_Color","User.Team_Color") and step["parameter_offset"]>=0 and step["parameter_offset"]+16<=step["parameter_data_bytes"],"actual native parameter bytes not read")
            py=profile=="Python";stats=step["stats"]
            wanted=dict(python_calls=index if py else 0,fallback_calls=0 if py else index,native_spawns=index if py else 0,invalid_spawn_noops=0,trail_writes=index if py else 0,
                team_queries=index if py else 0,missing_team_subsystem_defaults=0,red_choices=index if py and name=="team1" else 0,blue_choices=index if py and name!="team1" else 0,
                color_writes=index if py else 0,parameter_writes=index if py else 0,invalid_trail_noops=0)
            require(stats==wanted,"native selected production VFX branch counts differ")
        if profile=="Python": require(row["repeated"]["last_team_id"]==wanted_team,"Python did not read actual native team")
    return dict(status="passed",native_actors=len(PLAN),native_helper_calls=len(PLAN)*2,actual_parameter_store_reads=len(PLAN)*2,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True);args=parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
