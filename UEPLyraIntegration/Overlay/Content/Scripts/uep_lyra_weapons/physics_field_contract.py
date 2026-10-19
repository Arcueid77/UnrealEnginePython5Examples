"""Actual parent forwarding, initialized MIDs, solver callbacks and inactive glow."""
import argparse
import json
from pathlib import Path
from .hero_burst_cue_contract import require

PLAN=(('native-parent-field',False,False),('native-strain-profile-switch',True,True))


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone','native physics field run failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','break_callbacks_replayed','tick_callbacks_replayed','native_timer_properties_written','health_properties_written','identical_random_physics_fragments_claimed'):require(report[k] is False,'physics scope overclaim: '+k)
    for k in ('owned_actors_destroyed','original_health_unchanged','production_profiles_restored'):require(report[k] is True,'physics cleanup absent: '+k)
    require([r['name'] for r in report['pairs']]==[p[0] for p in PLAN],'actual parent/strain matrix incomplete')
    for row,plan in zip(report['pairs'],PLAN):
        require(row['initial_sphere_begin_entries']==[1,1] and row['initial_material_entries']==[1,1],'one natural bind/material setup required')
        require(row['natural_samples']>=2 and row['all_shaders_and_current_glow_unchanged'],'disconnected original shatter Tick was activated')
        require(all(n>0 for n in row['chaos_event_counts']) and row['chaos_payloads_valid'] and row['break_handler_counts']==row['chaos_event_counts'],'actual native Chaos component/payload/handler differs')
        for state in row['initial_states']:require(state['material_valid']==[True,True] and state['material_slots_match'] and state['notify_breaks'] and state['target']==1. and state['current']==0.,'native source MID/default initialization differs')
        for state in row['final_states']:require(state['root_broken'] and state['target']==0. and state['material_slots_match'],'native collection break did not reach source target-only assignment')
        for evidence in row['field_evidence']:
            require(evidence['python_construction']+evidence['fallback_construction']==1 and evidence['python_begin']+evidence['fallback_begin']==1,'natural project constructor/BeginPlay forwarding differs')
            if plan[2]:require(evidence['python_tick']>0 and evidence['fallback_tick']>0 and evidence['last_delta']>0,'natural Tick did not follow both live Profiles')
        require(row['profile_switch_observed']==plan[2] and row['parent_trigger_calls']==(0 if plan[1] else 2),'native trigger/Profile case differs')
        if plan[2]:require(row['final_profiles']==['Python','BlueprintFallback'],'native Chaos callback ignored Profile switch')
    return dict(status='passed',native_pairs=2,native_field_actors=4,native_shatter_actors=4,full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
