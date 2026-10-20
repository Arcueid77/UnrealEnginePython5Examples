"""Independent gate for localized labels, asymmetric materials and native audio."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_hover_input_tested','physical_click_input_tested','ui_sound_energy_tested','audio_cross_travel_tested','localized_text_roundtripped','health_properties_written','native_animation_completion_replayed')
TRUE_FIELDS=('source_python_state_pairs_match','all_widget_roots_and_profile_selectors_restored','original_live_player_health_unchanged','original_game_instance_sound_reference_restored','only_new_owned_click_audio_stopped_or_destroyed','owned_selection_fixture_enables_selectable_and_toggleable','completion_guard_fixture_sets_only_owned_widget_flag')
ROW_FIELDS=('native_construct_and_preconstruct','only_border_disable_parameter_and_all_four_material_resets','native_hover_selection_and_deselection_callbacks','disabled_callbacks_are_noops','localized_three_text_histories_preserved','tile_art_parameter_identity','null_texture_input_retains_previous_native_parameter','native_click_immediate_and_natural_completion','disabled_flag_at_natural_completion_keeps_reverse_guard','unwired_audio_return_clears_game_instance_reference')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native experience tile failed')
    for k in FALSE_FIELDS:require(r[k] is False,'experience scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'experience Profiles incomplete')
    for p in r['profiles']:
        for k in ROW_FIELDS:require(p[k] is True,'experience evidence missing: '+k)
        require(p['raw_progress_cases']==5 and p['texture_cases']==3 and p['native_finished_callbacks']==2,'experience matrix incomplete')
        require(len(p['spawned_click_audio'])==2,'native spawned click components missing')
        for a in p['spawned_click_audio']:require(a['playing'] is True and a['auto_destroy'] is True and a['existing_before_click'] is False and a['ui_sound'] is True and a['spatialized'] is False and a['stop_with_owner'] is False,'native click sound state differs')
    for k in TRUE_FIELDS:require(r[k] is True,'experience cleanup/parity missing: '+k)
    return dict(status='passed',native_profile_matrices=2,natural_click_completions=4,native_spawned_audio=4,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
