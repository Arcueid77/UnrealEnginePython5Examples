"""Natural Interact -> collect/sit -> original montage and inventory effects."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
MODES=('normal','interrupt','switch','cancel')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','physical_keyboard_tested','ability_callbacks_replayed','montage_callbacks_replayed','native_task_private_properties_written','authority_false_runtime_executed','production_ability_sets_modified','whole_collect_cue_business_migrated')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Explorer interaction actions fixture failed')
    for key in FALSE_FIELDS:require(r[key] is False,'Explorer actions overclaim: '+key)
    for key in ('primary_player_inventory_and_health_unchanged','owned_contexts_tasks_roots_and_selectors_restored'):require(r[key] is True,'Explorer actions cleanup missing: '+key)
    require(r['native_cue_recycling_enabled'] and r['native_cue_timer_cleanup_enabled'],'native Cue recycling or cleanup was disabled')
    require([(c['profile'],c['kind'],c['mode']) for c in r['cases']]==[(p,k,m) for p in ('BlueprintFallback','Python') for k in ('collect','sit') for m in MODES],'native interaction action matrix incomplete')
    for c in r['cases']:
        for key in ('native_interact_trace_and_nearby_grant','native_gas_event_activation','original_event_target_and_instigator_received','native_montage_playing_observed','inventory_effect_matches_source','collect_collision_lifespan_or_sit_target_preserved','native_tasks_and_montage_closed','current_completion_profile_matches','no_authority_duration_message','native_duration_transport_half_second_verified'):require(c[key] is True,'native action observation missing: '+key)
        require(c['new_item_count']==int(c['kind']=='collect'),'native pickup count differs')
        if c['kind']=='collect':require(c['new_stack_counts']==[2],'native pickup template stack count differs')
        if c['mode']!='cancel':require(c['native_montage_end_callbacks']>=1,'original native montage callback missing')
        if c['kind']=='collect' and c['mode']=='normal':require(c['native_target_expired_after_three_seconds'],'original target lifespan was not observed')
    require([p['profile'] for p in r['cue_pool_profiles']]==['BlueprintFallback','Python'],'collect Cue pool adapter Profile proof missing')
    for p in r['cue_pool_profiles']:
        require(p['cues'],'native collect Cue pool observation missing')
        for c in p['cues']:require(c['alive'] and c['hidden'] and c['owner_cleared'] and c['splines']==0 and c['lifespan']==0. and c['release_delta']>=1 and c['lifecycle']['python_release']+c['lifecycle']['fallback_release']>=1,'collect Cue was not cleanly returned to its native pool')
    return dict(status='passed',native_action_cases=16,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
