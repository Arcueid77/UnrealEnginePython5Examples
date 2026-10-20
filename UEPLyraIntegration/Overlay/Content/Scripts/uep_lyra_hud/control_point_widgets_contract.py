"""Require native CP source/Python matrices and explicit fixture cleanup."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','health_properties_written','native_async_factories_replaced','native_delay_replaced','audio_energy_tested')
TRUE_FIELDS=('native_source_pairs_match','widget_roots_removed','profile_selectors_restored','team_tag_deltas_restored','real_target_score_restored','original_point_state_restored','original_health_unchanged')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native CP HUD failed')
    for k in FALSE_FIELDS:require(r[k] is False,'CP HUD scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'CP HUD source/Python matrix incomplete')
    for p in r['profiles']:
        for k in ('actual_construct_and_native_async_binding','actual_score_and_status_ticks','style_brush_fields_and_colors_match','native_text_and_clamp_match','all_marker_scalar_states_match','owner_animation_condition_match','status_index_and_negative_team_guard_match','score_left_native_audio_parameters_match','unchanged_score_does_not_retrigger','removed_widgets_stop_native_ticks'):
            require(p[k] is True,'CP HUD native behavior missing: '+k)
        require(p['style_cases']==3 and p['marker_cases']>=12 and p['sound_cases']>=8 and p['status_cases']>=3 and p['diagnostic_fallbacks']==0,'CP HUD defined matrices incomplete')
    for k in TRUE_FIELDS:require(r[k] is True,'CP HUD parity/cleanup missing: '+k)
    return dict(status='passed',native_profile_matrices=2,style_cases=6,marker_cases=sum(p['marker_cases'] for p in r['profiles']),sound_cases=sum(p['sound_cases'] for p in r['profiles']),full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
