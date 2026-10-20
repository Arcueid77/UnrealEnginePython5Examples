"""Native localized construction, behavior selection and delayed Controller forwarding."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','whole_characters_migrated','callback_replayed','python_wait_clock_added','private_inventory_properties_written','native_text_recreated_from_python_strings')
TRUE_FIELDS=('original_player_inventory_and_health_unchanged','owned_objects_profiles_roots_and_tasks_restored','owned_native_proxies_and_observers_closed','owned_behavior_bot_closed')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback'),'Explorer behavior native fixture failed')
    for name in FALSE_FIELDS:require(r[name] is False,'Explorer behavior overclaim: '+name)
    for name in TRUE_FIELDS:require(r[name] is True,'Explorer behavior cleanup missing: '+name)
    require(r['hero_empty_motion_override_and_parent_constructor_retained'],'Hero empty/forwarding scope review missing')
    row=r['pawn']
    for name in ('natural_false_constructor_label_and_parent','natural_true_constructor_label_and_parent','false_behavior_keeps_state_tree_and_stopped_brain','true_behavior_destroys_state_tree_and_uses_input_ai_controller','native_nil_controller_path_preserved','natural_possession_grant_behavior_controller_order'):
        require(row[name] is True,'native Pawn behavior observation missing: '+name)
    require([c['name'] for c in row['late_behavior']]==['controller','switch-pending'],'native late-controller behavior cases incomplete')
    for case in row['late_behavior']:
        require(case['grants_while_missing']==0 and case['native_grants']==2 and case['owned_cleanup'] and case['latest_controller_argument_matches'] and case['state_tree_destroyed_after_grant'] and case['native_behavior_tree_seen_running'],'native grant/Controller/behavior continuation differs')
    return dict(status='passed',profile=r['profile'],native_behavior_cases=6,native_late_cases=2,whole_characters_migrated=False,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
