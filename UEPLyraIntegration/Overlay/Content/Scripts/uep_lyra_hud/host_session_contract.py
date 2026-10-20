"""Native host UI choices, payloads and actual local NULL session hosting."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested','native_callbacks_replayed','online_authentication_tested','health_properties_written')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['initial_native_mode']=='Standalone','native host-session screen failed')
    for field in FALSE_FIELDS:require(r[field] is False,'host-session scope overclaim: '+field)
    require(r['owned_roots_profiles_input_and_loading_class_restored'] is True,'host-session cleanup incomplete')
    if r['mode']=='host':
        require(r['profile'] in PROFILES and r['native_actual_entry_selection_and_online_init'] is True and r['native_spinner_afterpush_and_async_loading_before_submit'] is True and r['native_create_completion_handler_after_original_unbind'] is True and r['native_requested_map_experience_player_and_bot_option_ready'] is True and r['owned_native_session_destroyed'] is True,'native online host success path incomplete')
        require(r['request_mode']==2 and r['request_bots']=='0' and r['prepared_handler_calls']==r['completion_handler_calls']==1,'native host request/order/count differs')
        return dict(status='passed',native_null_online_host_profile=r['profile'],full_acceptance=False)
    require(r['mode']=='life' and [row['profile'] for row in r['profiles']]==list(PROFILES),'host lifecycle Profiles incomplete')
    for row in r['profiles']:
        for key in ('native_activation_const_focus_and_labels','native_mode_button_cycle_online_lan_offline','native_bots_button_and_localized_labels','native_null_request_returns_none','native_six_mode_bot_request_payloads'):
            require(row[key] is True,'host native lifecycle missing: '+key)
        require(row['mode_cycle']==[1,0,2] and row['request_cases']==6,'host mode/bot matrix differs')
    require(r['source_python_state_pairs_match'] is True and r['original_gameplay_health_unchanged'] is True,'host lifecycle state/health differs')
    return dict(status='passed',native_host_lifecycle_profiles=2,request_payload_cases=12,full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
