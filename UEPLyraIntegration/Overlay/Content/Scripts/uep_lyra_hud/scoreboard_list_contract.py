"""Native membership changes, stable ranking, pooled rows and localized ping."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native scoreboard list failed')
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_replaced','timer_callbacks_replayed','localized_format_roundtripped','health_properties_written','native_roster_array_written'):require(r[k] is False,'list scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'list source comparison missing')
    for p in r['profiles']:
        for k in ('unfiltered_accepts_null','team_filter_matches_native','initial_membership_matches','initial_rank_matches','ties_keep_membership_order','pooled_rows_match_sorted_states','native_timer_added_new_player','native_timer_changed_filter','native_timer_removed_destroyed_player','native_ping_text_format_matches','ping_color_cached_at_association','native_ping_timer_updates','removed_rooted_timer_updates','unfiltered_has_no_native_periodic_update'):
            require(p[k] is True,'native list/connection behavior missing: '+k)
        require(p['native_poll_elapsed_seconds']>=.9 and p['diagnostic_fallbacks']==0,'native polling timing or diagnostic fallback differs')
    for k in ('widget_roots_removed','profile_selectors_restored','owned_actors_destroyed','original_health_unchanged'):require(r[k] is True,'list cleanup missing: '+k)
    return dict(status='passed',native_profile_matrices=2,native_roster_timer_scenarios=6,native_connection_timers=2,full_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
