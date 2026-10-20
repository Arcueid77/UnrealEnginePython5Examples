"""Preserve Spawned timing, parent order and native next-tick visibility lifetime."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','whole_characters_migrated','callback_replayed','python_visibility_clock_added','health_properties_written','pixels_tested')
TRUE_FIELDS=('original_player_inventory_and_health_unchanged','owned_objects_profiles_roots_and_tasks_restored','owned_native_proxies_and_observers_closed')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback'),'Explorer startup runtime failed')
    for name in FALSE_FIELDS:require(r[name] is False,'Explorer startup overclaim: '+name)
    for name in TRUE_FIELDS:require(r[name] is True,'Explorer startup cleanup missing: '+name)
    require([row['kind'] for row in r['characters']]==['hero','pawn'],'both original Explorer classes required')
    for row in r['characters']:
        require(row['natural_begin_once'] and row['natural_next_frame_show'] and row['original_spawned_registration'],'native Explorer BeginPlay/Spawned visibility missing')
        require(row['required_state']=='InitState.Spawned' and row['static_parent']=='/Game/Characters/Character_Default.Character_Default_C','Explorer parent/state replaced')
        require([c['name'] for c in row['visibility_cases']]==['repeat','switch-pending','destroy-pending'],'native visibility lifetime matrix incomplete')
        for case in row['visibility_cases']:
            require(case['native_registration_called'] and case['not_shown_synchronously'],'native InitState/next-tick entry missing')
            if case['name']=='destroy-pending':require(case['no_late_script_work_after_destroy'],'destroyed Actor resumed visibility work')
            else:require(case['received_callbacks']==2 and case['native_next_frame_show'],'native repeated visibility callback/timing differs')
    return dict(status='passed',profile=r['profile'],characters=2,visibility_cases=6,whole_characters_migrated=False,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
