"""Native inventory message -> native toast object/list/row -> expiry removal."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
CASES=('parent-ignored','zero-ignored','negative-ignored','positive-one','positive-large','missing-fragment','repeat-positive','removed-still-listens','reconstructed-two-listeners','switch-current-profile')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','timer_callback_replayed','python_subscription_roots_added','localized_text_roundtripped_through_python','fastarray_replication_claimed','inventory_private_properties_written')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Explorer item list fixture failed')
    for key in FALSE_FIELDS:require(r[key] is False,'Explorer item list overclaim: '+key)
    for key in ('original_native_listener_released_after_owned_gc','owned_proxies_inactive_after_gc_and_message','primary_player_inventory_and_health_unchanged','owned_widgets_actors_roots_and_selectors_restored'):require(r[key] is True,'Explorer item list cleanup missing: '+key)
    require([g['row_profile'] for g in r['groups']]==['BlueprintFallback','Python'],'native row Profile matrix incomplete')
    for group in r['groups']:
        require([c['name'] for c in group['cases']]==list(CASES),'native list message cases incomplete')
        require(group['native_proxy_counts']==[2,2] and len(group['proxy_paths'])==2 and all(len(set(v))==2 for v in group['proxy_paths']) and len(set(group['proxy_paths'][0])|set(group['proxy_paths'][1]))==4,'original per-widget native proxy ownership differs')
        for case in group['cases']:
            expected_items=0 if case['name'] in CASES[:3] else 2 if case['name'] in CASES[-2:] else 1;expected_callbacks=0 if case['name']==CASES[0] else 2 if case['name'] in CASES[-2:] else 1
            require(case['expected_items']==expected_items and case['expected_callbacks']==expected_callbacks,'native list case expectation differs from source matrix')
            require(case['states'][0]==case['states'][1] and case['callback_deltas']==[case['expected_callbacks']]*2,'native list message pair differs: '+case['name'])
            require(all(len(state)==case['expected_items'] for state in case['states']) and case['all_item_outers_match_own_list'],'native list factory/count/outer differs')
            for state in case['states']:
                for item in state:require(item['duration']==2. and item['text']==case['expected_text'] and item['icon']==case['expected_icon'] and item['native_format_identity_preserved'],'native toast text/icon/default duration differs')
        for key in ('native_entry_assignment_and_binding_observed','pending_row_and_list_profiles_used','native_two_second_expiry_removes_all_items','final_empty_list_collapsed','original_listener_refs_preserved'):require(group[key] is True,'native item list observation missing: '+key)
        require(group['expired_items']==[2,2] and all(v>=1.9 for v in group['expiry_elapsed']),'native toast timer expiry differs')
    return dict(status='passed',native_message_cases=20,list_row_profile_combinations=4,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
