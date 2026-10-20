"""Native full brush/style parity, source goal lifetime and actual activation."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone' and r['mode'] in ('tdm','cp'),'native scoreboard styling failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_replaced','timer_callbacks_replayed','activation_callbacks_replayed','localized_team_name_roundtripped','health_properties_written'):require(r[k] is False,'style scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'style source/Python matrix incomplete')
    for p in r['profiles']:
        require(p['team_names_match_native_literals'] and p['all_text_tints_match'] and p['all_brush_resources_and_source_fields_match'] and p['glow_rotation_speed_match'],'team/header source presentation differs')
        require(p['target_score_matches_mode'] and p['native_stat_tag_updates'] and p['target_not_refreshed_by_timer'] and p['native_update_elapsed_seconds']>=.9,'native timer/static target behavior differs')
        require(p['actual_activation_callback'] and p['native_animation_playing'] and p['reactivation_matches_native_source_condition'],'actual board activation/retrigger missing')
        require(p['diagnostic_fallbacks']==0,'defined style inputs used diagnostics')
    for k in ('native_source_style_pairs_match','widget_roots_removed','profile_selectors_restored','team_tag_deltas_restored','real_target_score_restored','original_health_unchanged'):require(r[k] is True,'source parity/cleanup missing: '+k)
    return dict(status='passed',mode=r['mode'],native_profile_matrices=2,native_team_style_cases=4,native_header_style_cases=8,native_board_activation_cases=4,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
