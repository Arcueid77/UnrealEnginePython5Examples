"""Real native roster and timer behavior is required for both Profiles."""
import unittest
from uep_lyra_hud.scoreboard_list_contract import PROFILES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_replaced','timer_callbacks_replayed','localized_format_roundtripped','health_properties_written','native_roster_array_written'):r[k]=False
    for k in ('widget_roots_removed','profile_selectors_restored','owned_actors_destroyed','original_health_unchanged'):r[k]=True
    for p in PROFILES:
        row=dict(profile=p,native_poll_elapsed_seconds=1.,diagnostic_fallbacks=0)
        for k in ('unfiltered_accepts_null','team_filter_matches_native','initial_membership_matches','initial_rank_matches','ties_keep_membership_order','pooled_rows_match_sorted_states','native_timer_added_new_player','native_timer_changed_filter','native_timer_removed_destroyed_player','native_ping_text_format_matches','ping_color_cached_at_association','native_ping_timer_updates','removed_rooted_timer_updates','unfiltered_has_no_native_periodic_update'):row[k]=True
        r['profiles'].append(row)
    return r


class ScoreboardListContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_roster_timer_scenarios'],6)
    def test_no_substitute_for_native_roster_timer_changes(self):
        for k in ('native_timer_added_new_player','native_timer_changed_filter','native_timer_removed_destroyed_player'):
            r=report();r['profiles'][0][k]=False
            with self.subTest(k=k),self.assertRaises(RuntimeError):validate(r)
    def test_stable_ties_pooled_rows_and_localized_format_must_match(self):
        for k in ('ties_keep_membership_order','pooled_rows_match_sorted_states','native_ping_text_format_matches'):
            r=report();r['profiles'][0][k]=False
            with self.subTest(k=k),self.assertRaises(RuntimeError):validate(r)
    def test_native_roster_and_callbacks_are_not_replayed(self):
        r=report();r['native_roster_array_written']=True
        with self.assertRaises(RuntimeError):validate(r)
