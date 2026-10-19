"""Natural first/repeat firing must use default automatically registered audio."""
import argparse
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

ROUTERS={
    "math":("/Game/UEPMixins/BP_WeaponAudioMathRouter.BP_WeaponAudioMathRouter_C","_uep_audio_math"),
    "dispatch":("/Game/UEPMixins/BP_WeaponAudioDispatchRouter.BP_WeaponAudioDispatchRouter_C","_uep_audio_dispatch"),
    "whiz":("/Game/UEPMixins/BP_WeaponAudioWhizRouter.BP_WeaponAudioWhizRouter_C","_uep_audio_whiz"),
    "early":("/Game/UEPMixins/BP_WeaponAudioEarlyRouter.BP_WeaponAudioEarlyRouter_C","_uep_audio_early")}
REQUIRED={"dispatch":("SendWeaponFire_python","SetWeaponSoundParams_python"),"whiz":("python_calls",),"early":("python_calls",)}


def counters(snapshot,key):return snapshot.get(key,{}).get("counters",{})
def delta(before,after,key,field):return int(counters(after,key).get(field,0))-int(counters(before,key).get(field,0))


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","natural cold firing run failed")
    for key in ("full_acceptance","network_acceptance","physical_input_tested","audio_playback_tested","pixels_tested","manual_audio_registration","audio_helpers_preloaded_by_probe","audio_profiles_changed_by_probe","cue_profiles_changed_by_probe","cue_handler_replayed","health_properties_written","ammo_properties_written"):
        require(report[key] is False,"cold audio scope/fixture overclaim: "+key)
    for key in ("original_player_health_unchanged","original_inventory_ammo_restored","original_control_rotation_restored","observer_profiles_restored","all_test_actors_destroyed","default_field_property_preserved"):
        require(report[key] is True,"natural firing cleanup/default mismatch: "+key)
    require(len(report["shots"])==len(report["cold_shots"])==2,"actual first/repeat input shots missing")
    for index,(shot,row) in enumerate(zip(report["shots"],report["cold_shots"])):
        require(row["index"]==index and row["kind"]==("first" if index==0 else "repeat") and shot["weapon"]==report["selected_weapon"],"cold shot sequence differs")
        require(shot["profile"]=="Python" and shot["input_press_count"]==1 and shot["input_released"] and shot["native_target_callbacks"]==1 and shot["target_count"]>=1,"native default firing/input/target data missing")
        require(shot["ammo_before"]-shot["ammo_after"]==1 and shot["target_health_before"]>shot["target_health_after"]>=0 and shot["native_enemy_hit"],"actual native cost/enemy damage missing")
        require(shot["weapon_actor_fire_calls"]==1 and shot["native_ability_ended"] and shot["native_tasks_observed"]>=1 and shot["native_montage_playing"],"actual firing presentation/completion missing")
        before,after=row["before"],row["after"]
        require(delta(before,after,"cue","python_calls")==1,"actual default Cue Python handler did not execute once")
        for key,fields in REQUIRED.items():
            require(after.get(key,{}).get("registered") and after[key]["selected_profile"]=="Python","default audio helper was not registered: "+key)
            for field in fields:require(delta(before,after,key,field)==1,"natural audio helper Python dispatch missing: "+key+"."+field)
        require(all(item["selected_profile"]=="Python" for item in after.values() if item.get("registered")),"probe changed a default audio/Cue Profile")
    return dict(status="passed",weapon=report["selected_weapon"],actual_input_shots=2,actual_default_cue_entries=2,actual_audio_dispatch_entries=8,manual_audio_registration=False,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
