"""Native experience selection routes, requests and real NULL quickplay travel."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested','native_callbacks_replayed','online_authentication_tested','health_properties_written')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['initial_native_mode']=='Standalone','native experience screen failed')
    for field in FALSE_FIELDS:require(r[field] is False,'experience screen scope overclaim: '+field)
    require(r['owned_roots_profiles_input_and_loading_class_restored'] is True,'experience screen cleanup incomplete')
    if r['mode']=='quick':
        require(r['profile'] in PROFILES and r['native_online_initialize_success'] is True and r['native_async_preparation_then_online_request'] is True and r['native_quickplay_search_empty_then_host'] is True and r['native_destination_map_experience_and_player_ready'] is True and r['owned_native_session_destroyed'] is True,'native quickplay success path incomplete')
        require(r['online_request_mode']==2 and r['quickplay_handler_calls']==1 and r['prepared_handler_calls']==1,'native quickplay request/order/count differs')
        return dict(status='passed',native_null_quickplay_profile=r['profile'],full_acceptance=False)
    require(r['mode']=='life' and [row['profile'] for row in r['profiles']]==list(PROFILES),'native selection Profiles incomplete')
    for row in r['profiles']:
        for field in ('native_activation_animation_and_const_focus','native_list_selection_assigns_exact_definition','native_visible_hidden_spinner_states','native_online_request_payload_matches_definition','native_host_afterpush','native_browse_online_callback_then_browser_afterpush','native_browser_search_completes'):
            require(row[field] is True,'selection lifecycle evidence missing: '+field)
    require(r['source_python_state_pairs_match'] is True and r['original_gameplay_health_unchanged'] is True,'selection lifecycle state/health differs')
    return dict(status='passed',native_selection_profiles=2,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
