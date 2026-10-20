"""Native GAS activation/scan/input/event target/end and owned lifetime evidence."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','physical_keyboard_tested','task_callbacks_replayed','python_scan_clock_added','native_task_private_properties_written','production_ability_sets_modified')
TRUE_FIELDS=('native_onspawn_gas_activation','original_scan_query_and_avatar_location_preserved','native_parent_nearby_task_granted_target_ability','native_trace_found_real_collectable','native_input_press_activated_target_event','native_press_rearmed_one_wait_without_duplicate_scan','native_target_out_of_range_cleared_options','native_press_with_no_options_did_not_trigger_target','pending_profile_switch_used_current_callback','native_cancel_stopped_all_tasks_without_late_callbacks','native_reactivation_and_normal_end_stopped_all_tasks','owned_player_pawn_state_target_destroyed')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Explorer Interact native fixture failed')
    for k in FALSE_FIELDS:require(r[k] is False,'Explorer Interact overclaim: '+k)
    for k in ('primary_player_inventory_and_health_unchanged','class_selectors_roots_and_owned_contexts_restored'):require(r[k] is True,'Explorer Interact cleanup missing: '+k)
    require([c['profile'] for c in r['cases']]==['BlueprintFallback','Python'],'Explorer Interact Profile matrix incomplete')
    for c in r['cases']:
        for k in TRUE_FIELDS:require(c[k] is True,'native Interact observation missing: '+k)
        require(c['active_task_counts']==dict(scan=1,wait=1,nearby=1,release=0),'original native interaction task family differs')
        require(c['native_target_trigger_count']==2 and c['target_event_tag']=='Ability.Interaction.Activate' and c['target_event_instigator_and_target_match'],'native interaction target payload/count differs')
        require(c['end_cancelled_values']==[True,False],'native cancellation versus normal end differs')
    return dict(status='passed',native_interact_profiles=2,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
