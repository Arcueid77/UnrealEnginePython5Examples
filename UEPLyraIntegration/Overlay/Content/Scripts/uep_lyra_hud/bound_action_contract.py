"""Require native input delegate teardown/remount and original brush semantics."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_hover_input_tested','physical_click_input_tested','physical_action_binding_execution_tested','ui_sound_energy_tested','health_properties_written','native_animation_completion_replayed','construct_destruct_or_input_delegate_replayed')
TRUE_FIELDS=('source_python_state_pairs_match','all_widget_roots_and_profile_selector_restored','native_input_type_restored','original_live_player_health_unchanged','owned_selection_fixture_enables_selectable_and_toggleable','completion_guard_fixture_sets_only_owned_widget_flag')
ROW_FIELDS=('native_construct_preconstruct_and_reset','source_brush_copied_pins_and_omitted_defaults_match','only_gamepad_hides_border','native_input_method_callback_exactly_once','removed_widget_bp_input_delegate_unbound','same_widget_remount_rebinds_bp_delegate_once','native_hover_selection_and_deselection_callbacks','disabled_callbacks_are_noops','both_material_disable_enable_and_reset','native_click_immediate_and_natural_completion','disabled_flag_at_natural_completion_keeps_reverse_guard')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native bound-action failed')
    for k in FALSE_FIELDS:require(r[k] is False,'bound-action scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'bound-action Profiles incomplete')
    for p in r['profiles']:
        for k in ROW_FIELDS:require(p[k] is True,'bound-action evidence missing: '+k)
        require(p['typed_input_style_cases']==4 and p['actual_native_input_changes']==3 and p['native_finished_callbacks']==2,'bound-action matrix incomplete')
    for k in TRUE_FIELDS:require(r[k] is True,'bound-action cleanup/parity missing: '+k)
    return dict(status='passed',native_profile_matrices=2,native_input_changes=6,natural_click_completions=4,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
