"""Real native instant trace payload, HasActor-only draw/end and retry behavior."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
CASES=('hit','miss','retry-while-miss-active','switched-reactivation-hit')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','physical_keyboard_tested','pixels_tested','target_data_callbacks_replayed','native_target_task_fields_written','production_ability_sets_modified')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Explorer marker native fixture failed')
    for key in FALSE_FIELDS:require(r[key] is False,'Explorer marker overclaim: '+key)
    for key in ('primary_player_inventory_and_health_unchanged','owned_contexts_target_actors_roots_and_selectors_restored'):require(r[key] is True,'Explorer marker cleanup missing: '+key)
    require([(c['profile'],c['name']) for c in r['cases']]==[(p,n) for p in ('BlueprintFallback','Python') for n in CASES],'native marker profile matrix incomplete')
    for c in r['cases']:
        require(c['native_target_actors_and_tasks_closed'],'marker target task or target actor leaked')
        if c['name']=='retry-while-miss-active':require(c['native_reactivation_rejected'] and c['activation_delta']==0 and c['data_delta']==0 and c['draw_delta']==0 and c['ability_still_active'],'marker no-hit active retry behavior differs');continue
        require(c['native_activation_succeeded'] and c['activation_delta']==1 and c['data_delta']==1 and c['has_endpoint'],'marker native instant task data missing')
        if c['name']=='miss':require(not c['has_actor'] and c['draw_delta']==0 and c['ability_still_active'],'marker miss must stay active without drawing')
        else:require(c['has_actor'] and c['expected_box_in_target_data'] and c['draw_delta']==1 and not c['ability_still_active'] and c['draw_center_matches_target_endpoint'] and c['current_profile_used'],'marker actor hit draw/end differs')
    return dict(status='passed',native_marker_cases=8,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
