"""Require native tabs, const focus, async modal pushes and calibration restoration."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','culture_switch_tested','physical_settings_input_tested','done_apply_save_or_reset_invoked','max_display_nits_setting_written','health_properties_written','native_async_completion_replayed','native_interface_message_replayed')
TRUE_FIELDS=('source_python_state_pairs_match','all_widget_roots_and_profile_selectors_restored','settings_and_native_hdr_overrides_restored','settings_config_files_unchanged','all_owned_modal_widgets_popped','original_live_player_health_unchanged')
ROW_FIELDS=('gamma_actual_const_focus_returns_self','hdr_actual_construct_caches_native_material','hdr_raw_luminance_material_matches','actual_construct_registers_original_tab_order','native_tab_titles_preserve_localization_and_hidden_policy','actual_native_tab_selection_routes_navigation','actual_screen_and_panel_activation_animation_frames','exact_unknown_action_tag_does_not_push','actual_native_async_afterpush_widgets_match_routes','native_hdr_activation_overrides_and_deactivation_restore')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native settings screens failed')
    for k in FALSE_FIELDS:require(r[k] is False,'settings screen scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'settings screen Profiles incomplete')
    for p in r['profiles']:
        for k in ROW_FIELDS:require(p[k] is True,'settings screen evidence missing: '+k)
        require(p['registered_tab_callbacks']==5 and p['hdr_luminance_cases']==5 and p['native_modal_afterpush_callbacks']==3,'settings screen matrix incomplete')
    for k in TRUE_FIELDS:require(r[k] is True,'settings screen cleanup/parity missing: '+k)
    require(r['temporary_native_hdr_overrides_exercised'] is True,'native HDR behavior was not exercised')
    return dict(status='passed',native_profile_matrices=2,native_async_modal_pushes=6,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
