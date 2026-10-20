"""Partial channel delivery, nullable target and independent cosmetic branch."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
CASES=('root-ps','child-pawn','nested-controller','plain-ps','foreign','null','wrong-channel','parent-channel')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native accolade relay failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','begin_play_replayed','production_subscription_replaced','native_relay_proxies_cancelled_by_fixture','health_properties_written'):require(r[k] is False,'accolade scope overclaim: '+k)
    require(r['natural_relays']>0 and [p['profile'] for p in r['profiles']]==list(PROFILES),'real map accolade comparison missing')
    for p in r['profiles']:
        require(p['native_listener_proxies']==1 and [c['name'] for c in p['cases']]==list(CASES),'partial native listener/matrix incomplete')
        for c in p['cases']:
            matched=c['name'] not in ('wrong-channel','parent-channel')
            require(c['fixture_entries']==int(matched) and c['natural_entries']==r['natural_relays']*int(matched),'native partial channel callback delivery differs')
            require(len(c['notifications'])==(r['natural_relays']+1)*int(matched),'native accolade notification count differs')
            for msg in c['notifications']:require(msg==c['expected'],'nullable player/verb/default text/object/channel payload differs')
        require(p['diagnostic_fallbacks']==0,'defined accolade cases fell back to original diagnostics')
        require(p['relay_proxy_gi_released_after_gc_and_message'] and p['engine_gc_frames']>=3,'original accolade listener did not release')
        if p['profile']=='Python':require(p['python_client_requests']==3 and p['python_cosmetic_broadcasts']==6 and p['python_player_helper_calls']==12,'authority and independent cosmetic sequence differs')
    for k in ('observer_scope_closed','owned_actors_destroyed','owned_components_destroyed','original_scores_restored','actual_tdm_target_score_restored','original_health_unchanged','diagnostic_probe_root_removed','production_profiles_restored'):require(r[k] is True,'accolade cleanup absent: '+k)
    return dict(status='passed',native_message_cases=16,typed_notification_messages=sum(len(c['notifications']) for p in r['profiles'] for c in p['cases']),full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
