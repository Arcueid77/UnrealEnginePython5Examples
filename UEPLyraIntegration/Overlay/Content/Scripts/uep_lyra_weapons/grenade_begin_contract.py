"""Independent native BeginPlay/Actor-owned timers and natural cleanup gate."""
import argparse
import json
import math
from pathlib import Path
from .grenade_cleanup_contract import validate as cleanup_validate,PLAN,require


def validate(report,expected_mode="Standalone",expect_trail=True):
    cleanup_validate(report,expected_mode=expected_mode)
    if expected_mode=="DedicatedServer":
        require(report["headless_runtime_requested"] is True and expect_trail is False and report["native_local_or_remote_player_controllers"]==0,"explicit actual no-player native headless lane required")
        ready=report["headless_readiness"];source=report["headless_selected_source"]
        require(ready["native_mode"]=="DedicatedServer" and ready["experience"] is True and ready["playing"] is True and ready["stable_seconds"]>=.5 and
            source["actor"]==source["player_state_pawn"]==source["asc_avatar"] and source["role"]==3 and source["health"]==100.,"actual stable canonical authority bot source missing")
    require(report["python_timer_entry"]=="KismetSystemLibrary.K2_SetTimer" and report["native_named_actor_timer_binding"] is True and report["native_destroyed_actor_timers_naturally_expired"] is True,"actual native Actor timer binding/natural expiry missing")
    require(report["native_detonate_callback_observed"] is False and math.isfinite(report["timer_drain_elapsed"]) and
        abs(report["timer_drain_elapsed"]-report["timer_drain_expected_remaining"])<=max(.05,2.*report["timer_drain_max_frame"]),"native timer expiry timing or unverified RPC callback claim differs")
    require(report["begin_play_replayed"] is False and len(report["begin_cases"])==len(PLAN),"six native BeginPlay observations required")
    for row,(name,profile),cleanup in zip(report["begin_cases"],PLAN,report["cases"]):
        require((row["name"],row["profile"])==(name,profile) and row["actor"]==cleanup["actor"] and row["native_begin_count"]==1,"native BeginPlay identity/count differs")
        before,after=row["event"]["before"],row["event"]["after"]
        require(before["fuse_handle_exists"] is False and before["fuse_named_exists"] is False and before["cleanup_named_exists"] is False,"timers must not exist before actual BeginPlay")
        for key in ("fuse_handle_exists","fuse_handle_active","fuse_named_exists","cleanup_named_exists"): require(after[key] is True,"actual native timer missing after BeginPlay: "+key)
        require(math.isfinite(after["fuse_property"]) and after["fuse_property"]==2. and abs(after["fuse_handle_remaining"]-2.)<=.0001 and
            abs(after["fuse_named_remaining"]-after["fuse_handle_remaining"])<=.0001 and abs(after["cleanup_named_remaining"]-.16)<=.0001,"actual opaque fuse handle/named Actor timer does not match original durations")
        require(row["cleanup_timer_gone_after_callback"] is True and row["fuse_handle_exists_before_destroy"] is True and row["fuse_handle_gone_after_destroy"] is False,"original native one-shot and deferred destroyed-Actor handle state differs")
        require(0.<row["fuse_remaining_before_destroy"]<2.,"real native fuse did not remain active while cleanup ran")
        py=profile=="Python";character=name=="character"
        wanted=dict(python_calls=int(py),fallback_calls=int(not py),material_requests=int(py),invalid_material_noops=0,
            character_capsule_ignores=int(py and character),character_mesh_ignores=int(py and character),non_character_skips=int(py and not character),
            invalid_capsule_noops=0,invalid_mesh_noops=0,vfx_calls=int(py),detonate_timers=int(py),timer_handle_writes=int(py),cleanup_timers=int(py))
        require(row["event"]["stats"]==wanted,"actual selected BeginPlay production sequence counts differ")
        require(after["vfx_helper_calls"]==1 and after["trail_valid"] is expect_trail,"native BeginPlay VFX helper/native render branch differs")
        if not expect_trail:
            require(after["actor_team_color"]==before["actor_team_color"],"native no-render helper must preserve old color")
            stats=after["vfx_stats"]
            require(stats["python_calls"]==int(py) and stats["fallback_calls"]==int(not py) and stats["native_spawns"]==int(py) and
                stats["invalid_spawn_noops"]==int(py) and all(stats[key]==0 for key in ("trail_writes","team_queries","red_choices","blue_choices","color_writes","parameter_writes")),"native headless invalid-spawn branch differs")
        if character:
            require(row["actor"] not in before["capsule_ignores"] and row["actor"] in after["capsule_ignores"] and row["instigator"] in after["mesh_ignores"],"native initial reverse ignores missing")
        else: require(after["mesh_ignores"]==before["mesh_ignores"] and after["capsule_ignores"] is None,"native non-Character BeginPlay must skip both ignores")
    return dict(status="passed",actual_begin_play_callbacks=6,actual_actor_owned_fuse_timers=6,native_cleanup_timer_callbacks=6,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True);parser.add_argument("--headless",action="store_true");args=parser.parse_args()
    print(json.dumps(validate(json.loads(Path(args.report).read_text(encoding="utf-8-sig")),expected_mode="DedicatedServer" if args.headless else "Standalone",expect_trail=not args.headless)))
