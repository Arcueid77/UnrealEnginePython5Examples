"""Independent native menu/tile and inherited child acceptance gate."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
WIDGETS=('menu','tile','modal','arrow')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_hover_input_tested','physical_click_input_tested','ui_sound_energy_tested','localized_text_roundtripped','health_properties_written','native_animation_completion_replayed')
TRUE_FIELDS=('source_python_state_pairs_match','all_widget_roots_and_profile_selectors_restored','original_live_player_health_unchanged')
ROW_FIELDS=('native_construct_and_preconstruct','material_disable_enable_and_reset','raw_press_progress','localized_text_history_preserved','native_hover_and_selection_animation_frames','disabled_callbacks_are_noops','native_click_immediate_and_natural_completion','disabled_flag_at_natural_completion_keeps_reverse_guard')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native menu buttons failed')
    for k in FALSE_FIELDS:require(r[k] is False,'menu UI scope overclaim: '+k)
    require(r['completion_guard_fixture_sets_only_owned_widget_flag'] is True,'native completion guard fixture scope missing')
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'menu Profiles incomplete')
    for p in r['profiles']:
        require([w['widget'] for w in p['widgets']]==list(WIDGETS),'menu inherited family incomplete')
        for w in p['widgets']:
            for k in ROW_FIELDS:require(w[k] is True,'menu evidence missing: '+k)
            require(w['raw_progress_cases']==5,'raw progress matrix incomplete')
            require(w['native_finished_callbacks']>=2,'both natural click continuations required')
            if w['widget']!='tile':require(w['layout_cases']==8,'menu layout combinations incomplete')
            else:require(w['native_tile_art_parameter_matches'] is True,'tile texture parameter differs')
    for k in TRUE_FIELDS:require(r[k] is True,'menu cleanup/parity missing: '+k)
    return dict(status='passed',native_profile_matrices=2,native_widgets=8,natural_click_completions=16,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
