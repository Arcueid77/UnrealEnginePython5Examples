"""Native parent/interface fan-out, fixed colors and one-second stat updates."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native scoreboard rows failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_replaced','timer_callbacks_replayed','health_properties_written','new_native_timer_cleanup_added'):require(r[k] is False,'scoreboard scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'scoreboard source comparison missing')
    for p in r['profiles']:
        require(p['base_association'] and p['icon_association'] and p['name_team_colors_match'] and p['local_name_white'],'base/icon/name behavior differs')
        require(len(p['mode_rows'])==2 and all(c['children_from_native_panel'] and c['child_association_fanout'] and c['team_and_local_marker_match'] and c['all_row_colors_match'] and c['native_grouped_individual_score_match'] for c in p['mode_rows']),'CP/TDM parent/children/color/score behavior differs')
        require(p['native_construct_width'] and p['positive_preconstruct_width'] and p['nonpositive_preconstruct_retains_width'],'stat width source conditions differ')
        require(p['zero_stat_tinted'] and p['native_timer_updated_grouped_stat'] and p['positive_stat_white'] and p['native_update_elapsed_seconds']>=.9,'native stat loop/format/color missing')
        require(p['rebinding_updates_immediately'] and p['null_association_preserves_text'] and p['removed_rooted_stat_timer_still_updates'],'source stat association/timer lifetime differs')
        require(p['diagnostic_fallbacks']==0,'defined scoreboard inputs used diagnostics')
    for k in ('widget_roots_removed','cdo_profiles_restored','profile_families_restored','owned_actors_destroyed','original_health_unchanged'):require(r[k] is True,'scoreboard cleanup missing: '+k)
    return dict(status='passed',native_profile_matrices=2,native_mode_row_matrices=4,native_stat_timers=2,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
