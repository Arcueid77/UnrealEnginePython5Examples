"""Independent original/Python native Grenade activation/aim acceptance gate."""
import argparse
import json
import math
from pathlib import Path

CLASS="/ShooterCore/Input/Abilities/GA_Grenade.GA_Grenade_C"
PROJECTILE="/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C"
PLAN=tuple((name,profile) for name in ("miss","near","far") for profile in ("BlueprintFallback","Python"))


def require(condition,message):
    if not condition: raise RuntimeError(message)


def close(actual,expected,tolerance=0.001):
    require(len(actual)==len(expected) and all(math.isfinite(float(a)) and math.isfinite(float(b)) and abs(a-b)<=tolerance for a,b in zip(actual,expected)),"native numeric witness differs: "+str((actual,expected)))


def expected(row):
    view=row["before"]
    point=[a+5.*b+25.*c for a,b,c in zip(view["actor_location"],view["forward"],view["up"])]
    trace=view["trace"]
    if trace["distance"]<45.: return point,view["control"]
    target=trace["location"] if trace["hit"] else trace["end"]
    x,y,z=[a-b for a,b in zip(target,point)]
    return point,[0.,math.degrees(math.atan2(z,math.hypot(x,y))),math.degrees(math.atan2(y,x))]


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native Grenade activation report missing")
    for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","activation_event_replayed","task_callbacks_replayed","ability_granted_by_fixture","health_properties_written","inventory_properties_written","ability_spec_properties_written","projectile_actor_business_migrated","explosion_damage_tested","denied_body_native_tested"):
        require(report[key] is False,"Grenade activation scope overclaim: "+key)
    for key in ("observers_restored","listener_closed","profile_restored","specs_preserved","config_preserved","native_pose_restored","native_control_restored","actual_granted_primary_instance"):
        require(report[key] is True,"Grenade activation cleanup/identity missing: "+key)
    require(report["request_entry"]=="ASC.TryActivateAbilityByClass" and report["observation_errors"]==[],"native Grenade input/observer failed")
    require(report["native_class"]==CLASS and report["remaining_test_projectiles"]==0 and report["remaining_fixture_actors"]==0,"native class/fixture restoration failed")
    require(len(report["cases"])==len(PLAN),"six actual Grenade original/Python cases required")
    for row,(name,profile) in zip(report["cases"],PLAN):
        require((row["name"],row["profile"])==(name,profile),"Grenade native cases reordered")
        for key in ("native_request_accepted","native_repeat_rejected","native_cost_ready","native_cooldown_ready","all_pawn_health_unchanged","persistent_handle_preserved","specs_preserved","config_preserved","projectile_destroyed_by_fixture","montage_continues_after_end","native_montage_completed"):
            require(row[key] is True,"native Grenade witness missing: "+key)
        require(row["native_callback_count"]==1 and row["quiet_ticks"]>=20 and row["native_role"]==3,"native activation count/authority/quiet interval wrong")
        require(row["active_after"] is False and row["tasks_after"]==0,"original Grenade must End immediately, not wait for montage")
        require(math.isfinite(row["cooldown"]) and row["cooldown"]>0 and row["cooldown"]==row["native_cooldown"],"native cooldown write differs")
        trace=row["before"]["trace"]
        require(trace["hit"]==(name!="miss"),"native trace fixture branch differs")
        require(math.isfinite(trace["distance"]) and trace["distance"]>=0,"invalid trace distance")
        if name=="near": require(0.<trace["distance"]<45.,"native near trace missing")
        if name=="far": require(trace["distance"]>45.,"native far trace missing")
        point,direction=expected(row);close(row["location"],point);close(row["direction"],direction)
        require(len(row["projectiles"])==1 and len(row["messages"])==1,"exactly one actual projectile and typed duration message required")
        projectile=row["projectiles"][0];message=row["messages"][0]
        require(projectile["class"]==PROJECTILE and projectile["instigator"]==row["pawn"] and projectile["owner"] is None,"native projectile type/Instigator/Owner differs")
        close(projectile["location"],point);close(projectile["rotation"],direction);close(projectile["scale"],[1.,1.,1.])
        require(message["instigator"]==row["pawn"] and message["channel"]=="Ability.Grenade.Duration.Message" and message["duration"]==row["cooldown"],"typed native duration payload differs")
        require(message["native_active"] is True and message["native_montage_task_count"]==1,"native message must occur after montage task starts and before immediate End")
        stats=row["stats"];python=profile=="Python"
        wanted=dict(python_calls=int(python),fallback_calls=int(not python),cost_checks=int(python),cooldown_checks=int(python),commits=int(python),denied=0,aim_queries=int(python),
            near_control_rotation=int(python and trace["distance"]<45.),hit_aim=int(python and trace["distance"]>=45. and trace["hit"]),miss_aim=int(python and trace["distance"]>=45. and not trace["hit"]),
            projectiles=int(python),cooldown_writes=int(python),montage_tasks=int(python),duration_messages=int(python),native_ends=int(python),invalid_receiver_defaults=0)
        require(stats==wanted,"actual selected production handler counts differ")
    # Both sides independently meet the original numeric/native contracts. A
    # matching wrong implementation or a synthetic activation cannot pass.
    return dict(status="passed",native_profile_trials=len(PLAN),native_projectiles=len(PLAN),full_acceptance=False,network_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True);args=parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")))))
