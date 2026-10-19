"""Native equipped input, targeting/damage, RNG and failure-message acceptance."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

PROFILES=("BlueprintFallback","Python")
WEAPONS={"pistol":"/ShooterCore/Weapons/Pistol/GA_Weapon_Fire_Pistol.GA_Weapon_Fire_Pistol_C",
    "rifle":"/ShooterCore/Weapons/Rifle/GA_Weapon_Fire_Rifle_Auto.GA_Weapon_Fire_Rifle_Auto_C",
    "shotgun":"/ShooterCore/Weapons/Shotgun/GA_Weapon_Fire_Shotgun.GA_Weapon_Fire_Shotgun_C"}
PLAN=tuple((weapon,profile,field) for weapon in WEAPONS for profile in PROFILES for field in ((False,True) if weapon=="pistol" else (False,)))
NORMALS=((1.,0.,0.),(-1.,0.,0.),(0.,1.,0.),(0.,-1.,0.),(1.,.5,0.),(1.,-.5,0.),(-1.,.5001,0.),(-1.,-.5001,0.),(0.,0.,0.))


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native shared fire run failed")
    for field in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested",
                  "activation_handler_replayed","target_data_callback_replayed","montage_callback_replayed","timer_callback_replayed",
                  "health_properties_written","ammo_properties_written","timer_properties_written"):
        require(report[field] is False,"shared fire scope overclaim: "+field)
    for field in ("original_player_health_unchanged","original_inventory_ammo_restored","original_control_rotation_restored",
                  "observer_profiles_restored","all_test_actors_destroyed","native_global_seed_api_used"):
        require(report[field] is True,"shared fire native witness/cleanup missing: "+field)
    require(len(report["montage_pairs"])==len(WEAPONS)*len(NORMALS)*2*8,"native montage RNG pair matrix incomplete")
    require(all(row["same_asset"] and row["same_next_native_random"] for row in report["montage_pairs"]),"original montage branch/RNG draw count differs")
    require(Counter((r["weapon"],r["profile"],r["field_enabled"]) for r in report["shots"])==Counter(PLAN),"native input shot matrix incomplete")
    for row in report["shots"]:
        require(row["native_class"]==WEAPONS[row["weapon"]] and row["native_source_object_matches"] and row["input_press_count"]==1 and row["input_released"],"native firing input/class/equipment differs")
        require(row["native_activation_observed"] and row["native_target_callbacks"]==1 and row["target_count"]>=1 and row["blocking_hits"]>=1,"native activation/target data not observed")
        require(row["ammo_before"]-row["ammo_after"]==1 and row["target_health_before"]>row["target_health_after"]>=0. and row["native_enemy_hit"],"native commit/cost/authority damage not observed")
        require(row["weapon_actor_fire_calls"]==1 and row["native_tasks_observed"]>=1 and row["native_montage_playing"] and row["native_ability_ended"],"native firing Cue/presentation/task/end missing")
        require(row["field_actor_count"]==(row["blocking_hits"] if row["field_enabled"] else 0) and row["field_actor_poses_match"],"optional authority field Actor spawn count/ImpactPoint differs")
        require(row["native_completion_callbacks"]>=1 and row["no_handler_errors"],"original weak montage/timer completion did not execute")
    require(Counter((r["weapon"],r["profile"]) for r in report["failure_cases"])==Counter((w,p) for w in WEAPONS for p in PROFILES),"native failure-message matrix incomplete")
    for row in report["failure_cases"]:
        require(row["actual_native_message_dispatch"] and row["foreign_avatar_noop"] and row["allowed_message_disabled_flag"] and row["native_failure_montage_observed"],"native failure payload/guard/task state differs")
        require(row["repeat_throttled"] and row["native_timer_reenabled_flag"] and .98<=row["reenable_elapsed"]<1.6,"original failure throttle native timer differs")
        require(row["profile_switch_did_not_create_listener"] and row["source_listener_added_once"],"per-grant native listener lifecycle changed")
    require(Counter((row["profile"],row["kind"]) for row in report["lifecycle_cases"])==Counter((p,k) for p in PROFILES for k in ("complete","cancel","interrupt","null-montage")),"native original montage callback lifecycle matrix incomplete")
    for row in report["lifecycle_cases"]:
        names=[value["name"] for value in row["observed_native_callbacks"]]
        require(row["native_input_used"] and row["native_ability_ended"] and row["expected_native_callback"] in names,"original native montage callback not observed")
        require(row["native_activation_montage"]==(row["kind"]!="null-montage") and row["intervention_used"]==(row["kind"] in ("cancel","interrupt")),"native montage activation/intervention differs")
        if row["kind"]!="null-montage":require(("FireComplete" in names)==(report["native_clear_ability_timers_cvar"]==0),"native GAS timer cleanup policy changed")
    for kind in ("complete","cancel","interrupt","null-montage"):
        pairs=[[value["name"] for value in row["observed_native_callbacks"]] for row in report["lifecycle_cases"] if row["kind"]==kind]
        require(pairs[0]==pairs[1],"native callback/timer ordering differs between Profiles: "+kind)
    return dict(status="passed",native_equipped_input_shots=len(PLAN),native_rng_pairs=len(report["montage_pairs"]),native_failure_message_profiles=6,native_montage_callback_lifecycle_cases=8,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
