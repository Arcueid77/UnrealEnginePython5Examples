"""Require native TDM score/clock/style/audio and retained delegate lifetimes."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_energy_tested','production_localized_text_roundtripped','native_timer_replaced','native_delegates_replaced','health_properties_written')
TRUE_FIELDS=('native_source_pairs_match','widget_roots_removed','profile_selectors_and_wrappers_restored','team_tag_deltas_restored','real_target_score_restored','real_countdown_value_restored','original_health_unchanged')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native TDM HUD failed')
    for key in FALSE_FIELDS:require(r[key] is False,'TDM HUD scope overclaim: '+key)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'source/Python TDM HUD matrices incomplete')
    for p in r['profiles']:
        for key in ('actual_construct_and_async_team_binding','full_brush_fields_and_tints_match','numeric_values_and_unclamped_arcs_match','localized_clock_floor_and_audio_match','score_audio_parameters_match','actual_native_score_ticks','native_player_counted_delegate','native_countdown_timer_delegate','removed_tick_stops_but_countdown_binding_remains','remount_callback_count_matches_source'):
            require(p[key] is True,'TDM HUD evidence missing: '+key)
        require(p['style_cases']==3 and p['score_cases']>=4 and p['clock_cases']>=12 and p['score_sound_cases']>=8 and p['native_clock_interval']>=.9 and p['diagnostic_fallbacks']==0,'TDM HUD cases/timing incomplete')
    for key in TRUE_FIELDS:require(r[key] is True,'TDM HUD parity/cleanup missing: '+key)
    return dict(status='passed',native_profile_matrices=2,style_cases=6,clock_cases=sum(p['clock_cases'] for p in r['profiles']),full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
