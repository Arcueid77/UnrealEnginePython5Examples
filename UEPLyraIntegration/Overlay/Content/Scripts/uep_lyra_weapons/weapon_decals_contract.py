"""Reject native decal cache/array/latent claims without concrete readbacks."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

PROFILES=("BlueprintFallback","Python")
CASES=("cold","reuse-shorter","empty","replace-inactive","grow")
SURFACES=((0,1,2),(3,),(),(2,0),(1,2,3,0,2))
EXPECTED_SURFACES=((0,1,2,0),(3,1,2,0),(3,1,2,0),(2,0,2,0),(1,2,3,0,2))
TRIGGERS=(True,False,True,True,False)


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native decal run failed")
    for field in ("full_acceptance","network_acceptance","packaged_runtime","pixels_tested","audio_playback_tested",
                  "timer_properties_written","latent_callback_replayed","health_properties_written"):
        require(report[field] is False,"decal scope overclaim: "+field)
    for field in ("native_warmup_ready","all_test_actors_destroyed","all_test_components_destroyed",
                  "original_pawn_health_unchanged","production_classes_restored","original_view_restored","original_signature_restored"):
        require(report[field] is True,"native decal witness/cleanup missing: "+field)
    require(Counter((r["profile"],r["name"]) for r in report["cases"])==Counter((p,n) for p in PROFILES for n in CASES),"native decal matrix incomplete")
    for row in report["cases"]:
        index=CASES.index(row["name"])
        require(row["actual_selected_fire_dispatch"] and row["component_valid"],"native decal dispatch/component absent")
        require(row["same_cached"]==(row["name"] not in ("cold","replace-inactive")),"decal active/inactive cache decision differs")
        require(row["trigger"] is TRIGGERS[index] and row["trigger_parameter"] is row["trigger"],"native decal trigger reset/toggle differs")
        require(row["input_surfaces"]==list(SURFACES[index]) and row["surface_types"]==list(EXPECTED_SURFACES[index]) and
                row["native_surfaces"]==row["surface_types"],"native Array_Set grow/retained tail semantics differ")
        require(row["position_array_kind"]=="NiagaraDataInterfaceArrayPosition" and row["native_positions"]==row["positions"] and
                row["native_normals"]==row["normals"] and row["native_hit_count"]==len(row["positions"]),"native decal array/type/count data differs")
        require(row["world_location"]==[0.,0.,0.] and row["world_rotation"]==[0.,0.,0.] and row["world_scale"]==[1.,1.,1.] and
                row["unattached"] and row["native_auto_destroy"],"original world-origin decal spawn semantics differ")
    require(Counter(r["profile"] for r in report["timer_cases"])==Counter(PROFILES),"native decal timer matrix incomplete")
    for row in report["timer_cases"]:
        require(row["native_retrigger_observed"] and row["survived_original_deadline"] and row["destroyed_after_retrigger"] and
                4.<=row["destroy_elapsed"]<5.5,"original decal retriggerable three-second deadline differs")
        require(row["valid_inactive_kept_actor_alive"] and row["native_repeat_cleanup_observed"] and row["destroyed_after_component_removal"],"decal cleanup validity/repeat behavior differs")
        callbacks=row["hold_callback_elapsed"]
        require(4.<=row["native_callback_elapsed"]<5.5 and len(callbacks)==2 and callbacks[0]>=3. and callbacks[1]-callbacks[0]>=3.,"actual native latent callback times missing")
    return dict(status="passed",actual_native_niagara_trials=10,actual_native_delay_profiles=2,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
