"""Native caller/login/browser push and repeated NULL search acceptance."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested','audio_playback_tested','native_callbacks_replayed','health_properties_written','browser_entry_or_join_migrated','nonempty_provider_results_natively_tested','failed_search_system_message_natively_tested')
ROW_TRUE=('native_selection_login_then_browser_afterpush','native_activation_and_const_focus','native_empty_results_visibility_list_and_unlock','native_refresh_button_starts_new_request','native_do_once_blocks_duplicates_across_profiles','native_completion_after_profile_switch_unlocks_next_search','native_three_actual_search_completions_and_quiet')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['initial_native_mode']=='Standalone','native browser failed')
    for field in FALSE_FIELDS:require(r[field] is False,'browser scope overclaim: '+field)
    for field in ('owned_roots_profiles_input_and_loading_class_restored','original_gameplay_health_unchanged','source_python_state_pairs_match'):require(r[field] is True,'browser state/cleanup mismatch: '+field)
    require([row['profile'] for row in r['profiles']]==list(PROFILES),'browser Profiles incomplete')
    require([row['native_pooled_browser_reused'] for row in r['profiles']]==[False,True],'actual native browser pool reactivation missing')
    for row in r['profiles']:
        for field in ROW_TRUE:require(row[field] is True,'native browser observation missing: '+field)
        require(row['actual_native_search_completions']==3 and row['result_counts']==[0,0,0],'native NULL search matrix differs')
    return dict(status='passed',native_browser_profiles=2,actual_native_search_completions=6,full_acceptance=False)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
