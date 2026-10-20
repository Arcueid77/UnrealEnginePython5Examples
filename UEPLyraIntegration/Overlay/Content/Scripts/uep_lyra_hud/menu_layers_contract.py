"""Native root map, menu/confirmation/close lifecycle and owned terminal quit gates."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_tap_or_button_input_tested','confirmation_result_delegate_replayed','confirmed_frontend_travel_executed','health_properties_written')
COMMON_TRUE=('all_widget_roots_and_profile_selectors_restored','original_live_player_health_unchanged')
ROW_FIELDS=('actual_native_initialize_four_tag_stack_pairs','menu_and_spinner_const_focus_targets','actual_native_menu_activation_animation','native_settings_afterpush_and_beforepush_deactivation','native_confirmation_prompt_localization_preserved','native_decline_button_handler_delivers_result_without_travel','touch_close_unparented_noop_and_parent_native_deactivation')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native menu/layers failed')
    for k in FALSE_FIELDS:require(r[k] is False,'menu/layer scope overclaim: '+k)
    for k in COMMON_TRUE:require(r[k] is True,'menu/layer cleanup missing: '+k)
    if r['mode']=='quit':
        require(r['profile'] in PROFILES and r['native_quit_requested_by_owned_menu'] is True and r['native_input_reset_to_mouse_before_quit'] is True,'native owned-menu quit evidence missing')
        require(r['native_request_exit_fallback_used'] is False,'quit must cause shutdown through original native path')
        return dict(status='passed',owned_native_quit_profile=r['profile'],full_acceptance=False)
    require(r['mode']=='life' and [p['profile'] for p in r['profiles']]==list(PROFILES),'menu/layer lifecycle Profiles incomplete')
    for p in r['profiles']:
        for k in ROW_FIELDS:require(p[k] is True,'menu/layer lifecycle missing: '+k)
        require(p['native_afterpush_callbacks']==1 and p['native_confirmation_results']==[1],'native async lifecycle count/result differs')
    require(r['source_python_state_pairs_match'] is True,'menu/layer state pair differs')
    return dict(status='passed',native_lifecycle_profile_matrices=2,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
