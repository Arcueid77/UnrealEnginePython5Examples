"""Native null Niagara results retain the original BP cache/dedup semantics."""
import argparse,json
from pathlib import Path
from .hero_burst_cue_contract import require
FALSE=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_spawn_function_replaced','spawn_return_value_injected','health_properties_written','timeline_callbacks_replayed')

def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone' and report['null_rhi'],'Native NullRHI comparison required')
    for name in FALSE:require(report[name] is False,'Null effect shortcut/overclaim: '+name)
    require([r['profile'] for r in report['cases']]==['BlueprintFallback','Python'],'Both native source profiles required')
    for row in report['cases']:
        require(row['selected_spawn_entries']==2 and row['other_spawn_entries']==0,'Actual selected native entries required')
        require(row['initial']==row['repeat']==dict(array_count=2,map_count=2,array_all_null=True,map_all_null=True,expected_mesh_keys=True,ignored_mesh_absent=True),'Native null cache/repeated discovery differs')
        require(row['removal_cleared_caches'],'Native removal left null effect caches')
        if row['profile']=='Python':require(row['spawn_attempts']==2 and row['existing_meshes']==2 and row['diagnostic_fallbacks']==0,'Null cache retried spawning or fell through to BP')
    require(report['mixin_profile_method_counts']==dict(BlueprintFallback=8,Python=8),'Public spawning declaration changed')
    for name in ('owned_actors_destroyed','owned_effects_removed','owned_watchers_cancelled','original_health_unchanged','production_profiles_restored'):
        require(report[name] is True,'Null spawning cleanup missing: '+name)
    return dict(status='passed',original_python_pairs=1,native_null_results=4,repeat_native_cache_cases=2,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
