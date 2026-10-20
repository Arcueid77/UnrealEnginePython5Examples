"""Independent presentation acceptance with read-only native settings models."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','culture_switch_tested','physical_pointer_or_button_input_tested','native_touch_input_tested','ui_sound_energy_tested','settings_values_written','settings_applied_or_saved','localized_text_roundtripped','health_properties_written')
TRUE_FIELDS=('source_python_state_pairs_match','all_widget_roots_and_profile_selectors_restored','native_input_type_restored','native_selected_setting_index_unchanged','settings_config_files_unchanged','original_live_player_health_unchanged')
ROW_FIELDS=('actual_native_list_assignment_preserves_localized_action_and_navigation_labels','typed_gamepad_focus_targets_match','manual_pointer_callbacks_and_actual_hover_animation_frames','background_actual_multicast_enter_leave_order','scalar_raw_values_and_defaults_match','discrete_both_component_callback_sound_paths','rotator_native_population_selection_and_raw_material_values','rotator_strict_width_material_thresholds_and_local_count','details_native_text_precedes_selected_material_update','enum_native_localized_options_selection_order_and_pool_reuse','enum_invalid_setting_resets_without_deleting_pool')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native settings editors failed')
    for k in FALSE_FIELDS:require(r[k] is False,'settings editor scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'settings editor Profiles incomplete')
    for p in r['profiles']:
        for k in ROW_FIELDS:require(p[k] is True,'settings presentation evidence missing: '+k)
        require(p['focus_cases']==5 and p['hover_widget_cases']==7 and p['scalar_value_cases']==5 and p['scalar_default_cases']==3 and p['rotator_style_cases']==9 and p['rotator_index_cases']==5 and p['enum_option_count']>=2,'settings presentation matrices incomplete')
    for k in TRUE_FIELDS:require(r[k] is True,'settings presentation cleanup/parity missing: '+k)
    return dict(status='passed',native_profile_matrices=2,presentation_widget_classes=10,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
