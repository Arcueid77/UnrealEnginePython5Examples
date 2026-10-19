"""Actual native struct/array/channel readbacks and original impact lifetime gates."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

PROFILES=("BlueprintFallback","Python")
BUCKET_CASES=("mixed","sparse-grow","empty","shorter")
ARRAY_CASES=("cold","near","equal","far","inactive-far","null-cache","changed-template-far","invalid-template","character","concrete","glass","expired-other-cache")
REUSED={"far","inactive-far","changed-template-far","invalid-template"}
BUCKET_SURFACES=((3,0,3,1),(6,6,2),(),(1,))
BUCKET_LENGTHS=(5,7,7,7)


def validate(report):
    require(report["status"]=="passed" and report["error"] is None and report["native_mode"]=="Standalone","native impacts run failed")
    for field in ("full_acceptance","network_acceptance","packaged_runtime","pixels_tested","audio_playback_tested",
                  "timer_properties_written","latent_callback_replayed","health_properties_written","data_channel_buffers_written_by_fixture"):
        require(report[field] is False,"impact scope overclaim: "+field)
    for field in ("native_warmup_ready","all_test_actors_destroyed","all_test_components_destroyed","original_pawn_health_unchanged",
                  "production_classes_restored","original_view_restored","original_signature_restored","function_locals_not_actor_properties"):
        require(report[field] is True,"native impact witness/cleanup missing: "+field)
    require(Counter((r["profile"],r["name"]) for r in report["bucket_cases"])==Counter((p,n) for p in PROFILES for n in BUCKET_CASES),"native impact bucket matrix incomplete")
    for row in report["bucket_cases"]:
        index=BUCKET_CASES.index(row["name"]);require(len(row["buckets"])==BUCKET_LENGTHS[index],"native bucket reset/grow differs")
        require(row["input_arrays_unchanged"] and row["native_struct_type"]=="/Game/Effects/Blueprints/SurfaceImpacts.SurfaceImpacts","native bucket struct/input identity differs")
        for surface,bucket in enumerate(row["buckets"]):
            ids=[i for i,s in enumerate(BUCKET_SURFACES[index]) if s==surface]
            require(bucket["positions"]==[row["points"][i] for i in ids] and bucket["normals"]==[row["normals"][i] for i in ids],"actual native bucket arrays differ")
    require(Counter((r["profile"],r["name"]) for r in report["cases"])==Counter((p,n) for p in PROFILES for n in ARRAY_CASES),"native impact cache matrix incomplete")
    for row in report["cases"]:
        require(row["component_valid"] and row["same_cached"]==(row["name"] in REUSED),"original inverted-distance/valid cache decision differs")
        if row["name"]=="invalid-template":
            require(row["before_parameters"]==row["native_parameters"] and row["before_location"]==row["world_location"],"invalid template did not preserve existing native cache state")
            continue
        data=row["native_parameters"]
        require(data["position_array_kind"]=="NiagaraDataInterfaceArrayPosition" and data["positions"]==row["points"] and
                data["normals"]==row["normals"] and data["number_of_hits"]==len(row["points"]),"native impact typed-array/count readbacks differ")
        require(data["muzzle_valid"] and data["muzzle"]==row["muzzle"] and row["world_location"]==row["points"][0] and row["active"],"native impact world pose/muzzle/activation differs")
        require(data["muzzle_storage_kind"]==("Vector" if row["name"]=="character" else "Position"),"original native Position setter vector fallback differs")
        require(row["asset_is_current_template"]==(row["name"]!="changed-template-far"),"cached template equality incorrectly added or wrong surface template selected")
        require(row["unattached"] and row["world_rotation"]==[0.,0.,0.] and row["world_scale"]==[1.,1.,1.],"native impact spawn transform differs")
    require(Counter((r["profile"],r["channels"]) for r in report["fire_cases"])==Counter((p,c) for p in PROFILES for c in (False,True)),"native impact Fire/selector matrix incomplete")
    for row in report["fire_cases"]:
        expected=[dict(method="SpawnFromDataChannels" if row["channels"] and surface in (2,3) else "SpawnFromArrays",surface=surface) for surface in range(4)]
        require(row["routes"]==expected and row["selected_fire_dispatch"] and row["input_arrays_cleared"],"actual nested impact Fire/selection/input clear differs")
        for bucket in row["buckets"]:
            require(bucket["positions"] and len(bucket["positions"])==len(bucket["normals"]),"Fire cleared output buckets instead of only input arrays")
        require(row["cached_surfaces"]==([0,1] if row["channels"] else [0,1,2,3]),"Data Channel route incorrectly populated per-surface component cache")
    require(Counter(r["profile"] for r in report["channel_cases"])==Counter(PROFILES),"actual native channel publication matrix incomplete")
    for row in report["channel_cases"]:
        require(row["native_reader"] and row["reader_count"]>=4 and len(row["published"] )==4,"native channel publication not observed")
        expected=sorted(row["expected"],key=lambda value:value["position"])
        require(sorted(row["published"],key=lambda value:value["position"])==expected and all(value["valid"] for value in row["published"]),"actual native channel Position/Vector/Enum/muzzle rows differ")
    require(Counter(r["profile"] for r in report["timer_cases"])==Counter(PROFILES),"impact native latent timing matrix incomplete")
    for row in report["timer_cases"]:
        require(row["native_retrigger_observed"] and row["survived_original_deadline"] and row["destroyed_after_retrigger"] and
                4.<=row["destroy_elapsed"]<5.5 and 4.<=row["native_callback_elapsed"]<5.5,"original impact retriggerable delay differs")
        callbacks=row["hold_callback_elapsed"]
        require(row["valid_inactive_kept_actor_alive"] and row["native_repeat_cleanup_observed"] and row["destroyed_after_component_removal"] and
                row["native_has_valid_systems"] and len(callbacks)==2 and callbacks[0]>=3. and callbacks[1]-callbacks[0]>=3.,"native impact validity flag/repeat/removal cleanup differs")
    return dict(status="passed",native_bucket_trials=8,native_niagara_cache_trials=24,native_fire_selector_trials=4,native_published_channel_rows=8,native_delay_profiles=2,full_acceptance=False)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--report",required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
