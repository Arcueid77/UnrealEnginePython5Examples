"""Actual confirmed game-menu travel must reach the original frontend experience."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
MAP='/Game/System/FrontEnd/Maps/L_LyraFrontEnd.L_LyraFrontEnd'
EXPERIENCE='B_LyraFrontEnd_Experience'
EXPERIENCE_CLASS='/Game/System/FrontEnd/B_LyraFrontEnd_Experience.B_LyraFrontEnd_Experience_C'
FRONTEND='/Game/UI/Menu/W_LyraFrontEnd.W_LyraFrontEnd_C'
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_touch_or_button_input_tested','native_callbacks_replayed','travel_adapter_replayed_by_fixture','health_properties_written','online_authentication_tested')
TRUE_FIELDS=('original_reference_payload_preserved','native_open_menu_click_afterpush','native_yes_confirmation_result','native_confirmed_branch','native_old_world_replaced','native_frontend_experience_object_matches','native_frontend_state_component_present','native_frontend_main_menu_active_in_menu_layer','native_absolute_url_drops_old_options','original_gameplay_health_unchanged_until_travel_requested','owned_roots_profiles_and_input_restored')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in PROFILES and r['initial_native_mode']=='Standalone','native menu confirmed travel failed')
    for key in FALSE_FIELDS:require(r[key] is False,'menu travel scope overclaim: '+key)
    for key in TRUE_FIELDS:require(r[key] is True,'menu travel native evidence missing: '+key)
    require(r['confirmation_results']==[0] and r['menu_result_handler_calls']==1,'actual native confirmed result differs')
    require(r['new_world_path']==MAP and r['native_experience_option']==EXPERIENCE and r['native_experience_class']==EXPERIENCE_CLASS and r['native_frontend_widget_class']==FRONTEND,'native frontend map/experience/UI differs')
    require(r['old_world_path']!=r['new_world_path'] and r['native_frontend_profile']==r['profile'] and r['native_primary_local_user_state']==5,'native frontend travel/readiness profile differs')
    return dict(status='passed',native_confirmed_frontend_travel_profile=r['profile'],full_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
