"""Real lethal GAS ingress, inherited native delay and owned lifetime controls."""
import argparse,json,math
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
KINDS=('parent','simple-base','simple','big','explorer-hero','explorer-pawn')
SCENARIOS=('default','single-montage','empty-montages','destroy-pending','switch-pending')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','whole_parent_business_migrated','health_properties_written','death_delegate_manually_replayed','python_delay_clock_added','original_multibody_physics_visuals_verified')
TRUE_FIELDS=('primary_player_inventory_health_and_physics_unchanged','existing_shooter_child_router_owner_preserved','owned_contexts_profiles_roots_and_selectors_restored','original_descendant_file_hashes_unchanged','original_physics_source_hashes_unchanged','shared_pawn_data_class_restored')

def validate(r):
    require(r['status']=='passed' and r['error'] is None,'parent death native fixture failed')
    for k in FALSE_FIELDS:require(r[k] is False,'parent death overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'parent death cleanup/provenance missing: '+k)
    expected=[(p,k,n) for p in ('BlueprintFallback','Python') for k in KINDS for n in (SCENARIOS if k=='parent' else ('default',))]
    require([(v['profile'],v['kind'],v['name']) for v in r['cases']]==expected,'parent death inherited/lifetime matrix incomplete')
    for v in r['cases']:
        py=v['profile']=='Python';destroyed=v['name']=='destroy-pending';counts=v['counts']
        require(v['native_lethal_gas_producer'] and v['native_health_after']==0 and v['native_delegate_callbacks']==1 and v['native_delegate_payload_matches_actor'] and v['target_function_is_parent_router'],'actual native parent Health ingress missing')
        require(v['original_montages_restored'] and v['owned_actor_not_rooted'] and v['owned_context_destroyed'] and v['source_sight_removed'] and v['other_senses_unchanged'],'native death prefix/config restoration differs')
        require(v['prefix_current_montage'] in v['configured_montages'] if v['configured_montages'] else v['prefix_current_montage'] is None,'native montage differs from configured source array')
        require(counts['python_calls']==int(py) and counts['fallback_calls']==int(not py) and counts['delay_requests']==int(py),'death entry/default native delay counts differ')
        require(counts['montage_calls']==counts['unregister_calls']==int(py) and counts['missing_sense_noops']==0,'native montage/sight prefix differs')
        require([v['event'] for v in counts['trace']]==(['montage','sight','delay']+([] if destroyed else ['resume','ragdoll','hide','death']) if py else ['fallback']),'death prefix/continuation order differs')
        if py:
            start=counts['last_start'];require(.1<=start['duration']<=.600001 and start['owning_actor']==v['actor_path'],'native random Delay input/payload differs')
        if destroyed:
            require(v['observed_after_destroy_game_seconds']>=.75 and v['no_late_work_after_destroy'] and counts['resumes']==0 and v['ragdoll_calls']==v['hide_calls']==0,'destroyed native latent target continued')
        else:
            require(v['ragdoll_calls']==v['hide_calls']==1 and v['all_owned_weapon_actors_hidden'] and v['native_ragdoll_collision_and_simulation'],'native death endpoint chain differs')
            elapsed=v['endpoint_game_seconds']-v['entry_game_seconds'];require(.1-v['maximum_world_delta']-.001<=elapsed<=.6+v['maximum_world_delta']+.1,'original random native delay boundary differs')
            if py:
                require(counts['resumes']==1 and counts['death_forwards']==counts['hide_forwards']==counts['ragdoll_forwards']==1,'native continuation forwarding missing')
                elapsed=counts['last_resume']['game_seconds']-counts['last_start']['game_seconds'];require(math.isfinite(elapsed) and abs(elapsed-counts['last_start']['duration'])<=v['maximum_world_delta']+.001,'Python native Delay did not honor native game clock')
        if v['name']=='switch-pending':require(v['profile_before_resume']!=v['profile'] and v['endpoint_profile_matches_switch'],'pending native continuation ignored Profile switch')
        if v['name']=='single-montage':require(len(v['configured_montages'])==1,'single montage control absent')
        if v['name']=='empty-montages':require(not v['configured_montages'],'empty montage control absent')
    return dict(status='passed',native_parent_death_cases=20,full_acceptance=False,whole_parent_business_migrated=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
