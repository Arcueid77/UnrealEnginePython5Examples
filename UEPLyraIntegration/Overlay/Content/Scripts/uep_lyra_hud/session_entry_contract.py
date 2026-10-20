"""Real native browser rows, localized labels and successful owned LAN joins."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','remote_host_network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested','audio_playback_tested','native_callbacks_replayed','health_properties_written','online_provider_authentication_tested','failed_join_error_ui_natively_tested')
CLIENT_TRUE=('native_selection_login_and_browser_afterpush','native_actual_nonempty_search_and_list_row','native_original_localized_and_numeric_five_texts','native_definition_texture_identity','native_invalid_items_preserve_current_row','native_spinner_afterpush_then_primary_and_loading_macro','native_join_completion_after_unbind_and_spinner_pop','native_client_travel_to_owned_host_map_and_experience','owned_native_client_session_destroyed','initial_gameplay_health_unchanged_before_join','owned_roots_profiles_input_and_loading_class_restored')
HOST_TRUE=('native_lan_host_choices_and_submit','native_requested_map_and_experience_ready','native_remote_client_observed','owned_native_host_session_destroyed','owned_roots_profiles_input_and_loading_class_restored')
def validate_peer(r):
    require(r['status']=='passed' and r['error'] is None,'native entry peer failed')
    for field in FALSE_FIELDS:require(r[field] is False,'entry scope overclaim: '+field)
    if r['role']=='host':
        for field in HOST_TRUE:require(r[field] is True,'native host observation missing: '+field)
        require(r['request_mode']==1 and r['request_bots']=='0' and r['native_destination_mode']=='ListenServer','owned native LAN host payload differs')
    else:
        require(r['role']=='client' and r['profile'] in PROFILES,'unknown entry client Profile')
        for field in CLIENT_TRUE:require(r[field] is True,'native entry observation missing: '+field)
        require(r['prepared_handler_calls']==r['completion_handler_calls']==1 and r['native_destination_mode']=='Client','native join continuation count/mode differs')
        require(r['native_result_count']>=1 and r['native_world_controller_replacement_expected'] is True,'real result/travel missing')
    return True
def validate(directory):
    root=Path(directory);host=json.loads((root/'host.json').read_text(encoding='utf-8-sig'));validate_peer(host)
    for profile in PROFILES:
        client=json.loads((root/(profile+'.json')).read_text(encoding='utf-8-sig'));validate_peer(client);require(client['profile']==profile,'join Profiles incomplete');require(client['native_destination_level']==host['native_destination_level'] and client['native_destination_experience']==host['native_destination_experience'],'client joined different map/experience')
    return dict(status='passed',owned_local_lan_host=True,actual_native_join_profiles=2,full_acceptance=False)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);print(json.dumps(validate(parser.parse_args().directory)))
