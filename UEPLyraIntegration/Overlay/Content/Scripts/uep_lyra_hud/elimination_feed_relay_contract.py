"""Exact native messages, typed field order and original listener lifetime."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
CASES=('enemy','swapped','self','pawnless','wrong-channel','child-channel')
FIELDS=dict(Attacker='Attacker_2_AD99B0C64BF60688397909B26B2586B0',Attackee='Attackee_4_FC6EC57F491F306C48AA9CA1963CB21A',AttackerTeamID='AttackerTeamID_22_008260AC469FBA80E74290938D52EB7F',AttackeeTeamID='AttackeeTeamID_28_7FEE05EB44F8DDE22E4D8E9D281D9B8D',InstigatorTags='InstigatorTags_25_A844DE044F25C9A1A39EC8B7A46FE7F4',TargetChannel='TargetChannel_10_847A113C4C7145E34ABA278917694664')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native elimination relay failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','begin_play_replayed','production_subscription_replaced','native_relay_proxies_cancelled_by_fixture','health_properties_written'):
        require(r[k] is False,'relay scope overclaim: '+k)
    require(r['natural_relays']>0 and [x['profile'] for x in r['profiles']]==list(PROFILES),'real map relay/source-Python comparison incomplete')
    for row in r['profiles']:
        require(row['native_listener_proxies']==1 and [c['name'] for c in row['cases']]==list(CASES),'natural listener/case matrix incomplete')
        for c in row['cases']:
            matched=c['name'] not in ('wrong-channel','child-channel')
            require(c['fixture_entries']==int(matched),'native exact match differs')
            require(c['natural_entries']==r['natural_relays']*int(matched),'natural map relay did not use Python')
            require(len(c['notifications'])==(r['natural_relays']+1)*int(matched),'native typed notification count differs')
            for message in c['notifications']:require(message==c['expected'],'native attacker/attackee/name/team/tag/slot payload differs')
        require(row['diagnostic_fallbacks']==0,'defined relay cases used original diagnostics')
        require(row['relay_proxy_gi_released_after_gc_and_message'] and row['engine_gc_frames']>=3,'original relay proxy lifetime differs')
        if row['profile']=='Python':require(row['python_multicast_requests']==row['python_cosmetic_broadcasts']==4,'Python server/cosmetic branch count differs')
    for k in ('observer_scope_closed','owned_actors_destroyed','owned_components_destroyed','original_scores_restored','actual_tdm_target_score_restored','original_health_unchanged','diagnostic_probe_root_removed','production_profiles_restored'):require(r[k] is True,'relay cleanup absent: '+k)
    return dict(status='passed',native_message_cases=12,typed_notification_messages=sum(len(c['notifications']) for p in r['profiles'] for c in p['cases']),full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
