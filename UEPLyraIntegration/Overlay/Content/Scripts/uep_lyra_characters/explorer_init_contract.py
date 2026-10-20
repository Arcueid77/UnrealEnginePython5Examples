"""Native factory/listener isolation and actual deferred readiness acceptance."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','whole_characters_migrated','callback_replayed','python_wait_clock_added','private_inventory_properties_written','unrelated_proxies_cancelled')
TRUE_FIELDS=('original_player_inventory_and_health_unchanged','owned_objects_profiles_roots_and_tasks_restored','owned_native_proxies_and_observers_closed')
NAMES=('controller','inventory','quickbar','switch-pending','destroy-pending')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback'),'Explorer initialization runtime failed')
    for name in FALSE_FIELDS:require(r[name] is False,'Explorer initialization overclaim: '+name)
    for name in TRUE_FIELDS:require(r[name] is True,'Explorer initialization cleanup missing: '+name)
    require([row['kind'] for row in r['characters']]==['hero','pawn'],'both original Explorer classes required')
    for row in r['characters']:
        for name in ('natural_possession_factory_and_grant','two_listeners_create_two_native_proxies','initial_callbacks_match_native_team','native_team_change_and_cancel_isolation','native_no_team_callback_is_noop','named_actor_specific_callbacks_resolved'):
            require(row[name] is True,'native initialization observation missing: '+name)
        require([case['name'] for case in row['readiness']]==list(NAMES),'deferred native readiness matrix incomplete')
        for case in row['readiness']:
            require(case['grants_while_missing']==0 and case['native_wait_resumed_after_availability'] and case['owned_cleanup'],'native missing/ready/cleanup case differs')
            if case['name']=='destroy-pending':require(case['native_grants']==0 and case['no_late_work_after_destroy'],'destroyed pending actor resumed script work')
            else:require(case['native_readiness_released'] and case['native_grants']==(2 if case['stage']==0 else 1),'native repeated-request/coalescing behavior differs')
    return dict(status='passed',profile=r['profile'],characters=2,deferred_cases=10,whole_characters_migrated=False,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
