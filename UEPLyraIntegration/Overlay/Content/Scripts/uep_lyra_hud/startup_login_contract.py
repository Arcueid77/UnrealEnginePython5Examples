"""Require native local-player lifecycle and retained removed-widget callbacks."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_key_or_button_input_tested','native_callbacks_replayed','online_authentication_tested','confirmed_frontend_logout_reset_executed','health_properties_written')
ROW_TRUE=('native_construct_focus_and_waiting_flags','native_secondary_button_creates_local_player','native_secondary_completion_closes_waiting_startup_without_index_filter','native_secondary_button_destroys_only_secondary_player','native_removed_rooted_widgets_keep_original_initialization_callbacks','native_remount_does_not_duplicate_binding','native_localized_join_leave_text_preserved')
COMMON_TRUE=('native_default_online_subsystem_is_null','owned_roots_profiles_cdo_player_number_and_input_restored','original_primary_controller_and_health_unchanged','fixture_secondary_player_removed','fixture_secondary_pawns_removed','owned_login_activatable_holders_restored')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native startup/login failed')
    require(r['fixture_inert_character_event_created_secondary_slate_user'] is True and r['fixture_slate_user_lifetime']=='owned standalone process until normal shutdown','native secondary Slate user fixture provenance missing')
    for key in FALSE_FIELDS:require(r[key] is False,'startup/login scope overclaim: '+key)
    for key in COMMON_TRUE:require(r[key] is True,'startup/login cleanup missing: '+key)
    require([row['profile'] for row in r['profiles']]==list(PROFILES),'startup/login Profiles incomplete')
    for row in r['profiles']:
        for key in ROW_TRUE:require(row[key] is True,'native startup/login observation missing: '+key)
        require(row['controller_indices']==[-1,0,1,7] and row['logged_in_results']==[False,True,False,False],'native controller-validity matrix differs')
        require(row['natural_initialize_user_indices']==[1,0,0] and row['removed_callback_deltas']==[1,1] and row['remounted_callback_deltas']==[1,1],'native actual callback index/order/count differs')
    require(r['source_python_state_pairs_match'] is True,'startup/login Profile states differ')
    return dict(status='passed',native_profiles=2,natural_initialize_callbacks=6,owned_secondary_join_leave_cycles=2,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
