"""Native BeginPlay/factory/callback/profile-switch/weak-target evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .weapon_actor_helpers_contract import CLASSES,PROFILES,require

OWNERS=("pawn","unassigned-pawn","none","actor")


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native weapon BeginPlay failed")
    for key in ("full_acceptance","network_acceptance","packaged_runtime","health_properties_written","begin_play_replayed","team_callback_replayed","python_callback_retained","production_proxy_cancelled_by_script"):
        require(report[key] is False,"weapon BeginPlay scope overclaim: "+key)
    for key in ("original_team_restored","original_pawn_health_unchanged","test_actors_destroyed","test_owned_proxies_cancelled","production_profiles_restored","original_active_proxies_preserved"):
        require(report[key] is True,"native BeginPlay cleanup missing: "+key)
    require(report["observation_errors"]==[],"native team observer failed")
    require(Counter((r["class"],r["profile"],r["owner"]) for r in report["cases"])==Counter((c,p,o) for c in CLASSES for p in PROFILES for o in OWNERS),"native BeginPlay class/profile/owner matrix incomplete")
    for row in report["cases"]:
        require(row["actual_native_begin_count"]==1 and row["actor_destroyed"],"actual native BeginPlay or destruction missing")
        if row["owner"] in ("none","actor"):
            require(row["native_proxies_added"]==0 and row["events"]==[] and row["owner_field_is_null"],"invalid owner branch should not bind/write")
        elif row["owner"]=="unassigned-pawn":
            require(row["owner_matches"] and row["native_proxies_added"]==1 and row["proxy_inactive_after_initial_broadcast"],"unassigned native Pawn factory/auto-cancel missing")
            require(len(row["events"])==1 and row["events"][0]["assigned"] is False and row["events"][0]["team"]==-1 and row["events"][0]["stencil_delta"]==row["events"][0]["color_delta"]==0,"native initial no-team branch differs")
        else:
            require(row["owner_matches"] and row["native_proxies_added"]==1 and row["proxy_active_after_actor_destroy"] and row["no_dead_actor_callbacks"],"native weak target/factory lifetime differs")
            require(len(row["events"])==4 and row["profile_switch_did_not_create_proxy"],"native notification/profile switch matrix differs")
            for index,(event,team) in enumerate(zip(row["events"],(row["original_team"],row["other_team"],row["original_team"],row["other_team"]))):
                expected_profile=row["other_profile"] if index==2 else row["profile"]
                require(event["profile"]==expected_profile and event["team"]==team and event["assigned"] is (team!=-1),"actual native team payload/profile differs")
                wanted=0 if team==-1 else 1
                require(event["stencil_delta"]==event["color_delta"]==wanted,"callback helper sequence/no-team no-op differs")
    return dict(status="passed",actual_native_weapon_begins=24,actual_native_team_notifications=30,weak_destroyed_targets_verified=6,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
