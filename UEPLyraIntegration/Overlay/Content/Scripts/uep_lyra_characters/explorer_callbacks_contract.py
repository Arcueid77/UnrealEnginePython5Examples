"""Require genuine parts/GAS/sense/Reset/death producers on both Explorer classes."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
from .health_changed_contract import check_case,NAMES

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','whole_characters_migrated','health_properties_written','callback_replayed','component_delegate_broadcast_by_fixture','sense_report_called_by_fixture','inventory_properties_written')
TRUE_FIELDS=('original_player_inventory_and_health_unchanged','owned_objects_profiles_roots_and_tasks_restored','owned_native_bot_producers_and_observers_closed')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback'),'Explorer callback native fixture failed')
    for name in FALSE_FIELDS:require(r[name] is False,'Explorer callback scope overclaim: '+name)
    for name in TRUE_FIELDS:require(r[name] is True,'Explorer callback cleanup missing: '+name)
    require([row['kind'] for row in r['characters']]==['hero','pawn'],'both original Explorer classes required')
    for row in r['characters']:
        require(row['native_class'].endswith(('_Explorer.B_Hero_Explorer_C','_Explorer.B_Pawn_Explorer_C')),'Explorer class identity changed')
        require(row['parts_original_entries_and_actors_restored'],'native parts identity restoration missing')
        require([p['operation'] for p in row['parts']]==['add','remove','remove-again'],'native parts operation matrix incomplete')
        for p,count in zip(row['parts'],(1,1,0)):
            require(p['native_callback_count']==count and p['selected_receiver_calls']==count and p['native_delegate_payload_matches'] and p['native_device_count_matches'] and p['native_devices_retired'],'native parts callback/delivery/device differs')
        require([c['name'] for c in row['health']]==list(NAMES),'native GAS health matrix incomplete')
        for case,name in zip(row['health'],NAMES):check_case(case,(name,r['profile']),authority=True,actor_keys=('A','AI'))
        require(row['health_cleanup_restored'],'native GAS health/observer restoration incomplete')
        for name in ('reset','death'):
            event=row[name];require(event['native_producer_called'] and event['selected_event_calls']==1 and event['native_clear_calls']==1 and event['clear_after_matches_original_guard'] and event['old_actor_was_original_explorer'],'native lifecycle forwarding/clear observation missing: '+name)
    return dict(status='passed',profile=r['profile'],characters=2,parts_operations=6,native_health_cases=10,native_lifecycle_events=4,full_acceptance=False,whole_characters_migrated=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
