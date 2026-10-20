"""Native listener/snapshot/typed-message/lifetime evidence for inventory grids."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

CASES=('add','repeat-add','increase','decrease','remove','zero-equality-add','negative-equality-add','removed-widget-still-listens','reconstructed-two-listeners','switch-pending-listeners')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callback_replayed','python_subscription_roots_added','fastarray_replication_claimed','inventory_private_properties_written','original_proxies_cancelled_by_fixture')
TRUE_FIELDS=('natural_construct_snapshots_match_native_inventory','exact_parent_channel_ignored','source_unfiltered_foreign_inventory_messages_preserved','native_reconstruction_clears_and_resnapshots','two_original_native_proxies_per_reconstructed_widget','native_gc_releases_owned_listener_gi_references','owned_proxies_inactive_after_gc_and_message','original_native_listener_gi_references_preserved','primary_player_inventory_and_health_unchanged','owned_actor_widgets_roots_and_profile_selectors_restored')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Explorer grid native fixture failed')
    for k in FALSE_FIELDS:require(r[k] is False,'Explorer grid overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'Explorer grid required observation missing: '+k)
    require([c['name'] for c in r['cases']]==list(CASES),'Explorer grid message matrix incomplete')
    for row in r['cases']:
        require(row['states'][0]==row['states'][1]==row['expected'] and row['callback_deltas']==[row['expected_callbacks']]*2,'native grid state or callback count differs: '+row['name'])
    require(r['native_proxy_counts']==[2,2] and r['owned_proxy_gi_refs_after_gc']==0,'native grid proxy ownership differs')
    groups=r['native_proxy_paths_per_widget'];require(len(groups)==2 and all(len(set(group))==2 for group in groups) and not set(groups[0])&set(groups[1]),'native per-widget proxy identity evidence incomplete')
    require(r['switched_callback_profiles']==[True,True],'native grid listener retained a stale Profile')
    return dict(status='passed',native_message_cases=len(CASES),full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
