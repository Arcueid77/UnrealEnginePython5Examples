"""Real isolated recordings,query/rows/confirmation and native replay playback."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested','audio_playback_tested','native_callbacks_replayed','health_properties_written','replay_handler_hud_and_scrub_policy_migrated','cross_travel_actor_health_identity_claimed')
TRUE_FIELDS=('isolated_native_saved_directory_verified','native_initial_empty_query_and_const_focus','native_shared_do_once_blocks_duplicate_across_profile_switch','native_record_and_stop_two_real_replays','native_query_identity_and_timestamp_order_preserved','native_generated_row_localized_text_and_duration','native_invalid_items_preserve_current_row','native_decline_does_not_play','native_confirmation_prompt_localization','native_confirmed_play_uses_retargeted_current_item','native_replay_controller_hud_and_clock_observed','native_playback_stopped','initial_gameplay_health_unchanged_before_playback','owned_roots_profiles_settings_and_input_restored')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in PROFILES,'native replay browser failed')
    for field in FALSE_FIELDS:require(r[field] is False,'replay browser overclaim: '+field)
    for field in TRUE_FIELDS:require(r[field] is True,'native replay observation missing: '+field)
    require(r['actual_query_completions']==2 and r['recording_count']==2 and r['native_result_count']==2 and r['native_dialog_results']==[1,0],'native replay query/record/dialog matrix differs')
    require(r['played_replay_name']==r['recorded_replay_names'][0] and r['native_playback_seconds']>.25,'current-item playback identity/time differs')
    require(r['direct_interface_inputs']==['null','wrong replay-list object','retarget to older real replay during confirmation'],'direct row test inputs must be disclosed')
    return dict(status='passed',native_replay_browser_profile=r['profile'],real_recordings=2,actual_query_completions=2,full_acceptance=False)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
