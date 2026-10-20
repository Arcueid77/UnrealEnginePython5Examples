"""Require native input/selection/tab callbacks, FText and UMG animation parity."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_hover_input_tested','ui_sound_energy_tested','localized_text_roundtripped','native_parent_callbacks_replaced','health_properties_written')
TRUE_FIELDS=('source_python_state_pairs_match','all_widget_roots_and_profile_selectors_restored','native_input_type_restored','original_live_player_health_unchanged')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native foundation buttons failed')
    for k in FALSE_FIELDS:require(r[k] is False,'foundation UI scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'foundation UI Profiles incomplete')
    for p in r['profiles']:
        for k in ('native_construct_and_button_text_refresh','native_input_style_and_current_text_style_match','alignment_and_raw_press_progress_match','opaque_ftext_history_preserved','actual_native_selection_and_deselection_callbacks','native_hover_selected_animation_guards','actual_native_tab_registration_labels_and_removal','native_tab_selection_and_visibility_delegates','designer_preview_is_explicit_only'):
            require(p[k] is True,'foundation UI evidence missing: '+k)
        require(p['native_button_style_cases']>=4 and p['alignment_cases']==4 and p['progress_cases']>=5 and p['dynamic_tabs_created']==3,'foundation UI matrices incomplete')
    for k in TRUE_FIELDS:require(r[k] is True,'foundation UI cleanup/parity missing: '+k)
    return dict(status='passed',native_profile_matrices=2,native_dynamic_tab_cases=6,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
