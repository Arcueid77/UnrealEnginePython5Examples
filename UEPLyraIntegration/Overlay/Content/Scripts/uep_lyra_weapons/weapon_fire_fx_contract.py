"""Native Niagara parameter/cache and original retriggerable-delay evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

PROFILES=("BlueprintFallback","Python")
CASES=("cold","reuse","disabled","replace-inactive")


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native fire FX run failed")
    for field in ("full_acceptance","network_acceptance","packaged_runtime","pixels_tested","audio_playback_tested","timer_properties_written","latent_callback_replayed","health_properties_written"):
        require(report[field] is False,"fire FX scope overclaim: "+field)
    for field in ("native_warmup_ready","all_test_actors_destroyed","original_pawn_health_unchanged","production_classes_restored"):
        require(report[field] is True,"native fire FX witness/cleanup missing: "+field)
    require(Counter((r["profile"],r["name"]) for r in report["cases"])==Counter((p,n) for p in PROFILES for n in CASES),"native Niagara matrix incomplete")
    for row in report["cases"]:
        require(row["actual_selected_fire_dispatch"] and len(row["components"])==3,"native FX dispatch/components missing")
        for index,item in enumerate(row["components"]):
            require(item["valid"] and item["trigger_parameter"]==row["triggers"][index],"actual Niagara bool override differs")
            if row["name"]=="cold":require(item["relative_rotation"]==[0.,0.,90.] and item["attached_to_root"] and row["triggers"][index] is True,"original native spawn rotation/attachment/first trigger differs")
            if row["name"]=="reuse":require(row["same_cached"][index] and row["triggers"][index] is False,"active Niagara component not reused/toggled")
            if row["name"]=="disabled":require(row["same_cached"][index] and row["triggers"][index] is False,"disabled effect changed existing state")
        if row["name"]=="replace-inactive":require(row["same_cached"]==[True,False,True] and row["triggers"]==[True,True,True],"inactive cache not replaced with reset trigger")
        require(all(abs(a-b)<.0001 for a,b in zip(row["direction_parameter"],row["expected_direction"])) and row["tracer_array"]==row["impacts"],"actual native direction/array data differs")
    require(len(report["timer_cases"])==2,"native latent timing matrix incomplete")
    for row in report["timer_cases"]:
        require(row["native_retrigger_observed"] and row["survived_original_deadline"] and row["destroyed_after_retrigger"] and row["destroy_elapsed"]>=4.,"original retriggerable three-second delay replaced")
        require(row["valid_inactive_kept_actor_alive"] and row["native_repeat_cleanup_observed"] and row["destroyed_after_component_removal"],"cleanup must test valid component rather than active state")
    return dict(status="passed",actual_native_niagara_trials=8,actual_native_delay_profiles=2,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
