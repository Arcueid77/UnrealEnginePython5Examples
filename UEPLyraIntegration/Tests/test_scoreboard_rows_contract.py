"""Native timer and inherited row behavior must be present, not just snapshots."""
import unittest
from uep_lyra_hud.scoreboard_rows_contract import PROFILES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_replaced','timer_callbacks_replayed','health_properties_written','new_native_timer_cleanup_added'):r[k]=False
    for k in ('widget_roots_removed','cdo_profiles_restored','profile_families_restored','owned_actors_destroyed','original_health_unchanged'):r[k]=True
    for p in PROFILES:
        row=dict(profile=p,mode_rows=[dict(children_from_native_panel=True,child_association_fanout=True,team_and_local_marker_match=True,all_row_colors_match=True,native_grouped_individual_score_match=True) for _ in range(2)],native_update_elapsed_seconds=1.,diagnostic_fallbacks=0)
        for k in ('base_association','icon_association','name_team_colors_match','local_name_white','native_construct_width','positive_preconstruct_width','nonpositive_preconstruct_retains_width','zero_stat_tinted','native_timer_updated_grouped_stat','positive_stat_white','rebinding_updates_immediately','null_association_preserves_text','removed_rooted_stat_timer_still_updates'):row[k]=True
        r['profiles'].append(row)
    return r


class ScoreboardContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_mode_row_matrices'],4)
    def test_parent_fanout_and_native_children_required(self):
        r=report();r['profiles'][0]['mode_rows'][0]['child_association_fanout']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_timer_and_source_null_lifetime_cannot_be_substituted(self):
        for key in ('native_timer_updated_grouped_stat','null_association_preserves_text','removed_rooted_stat_timer_still_updates'):
            r=report();r['profiles'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_no_timer_callback_or_cleanup_replacement_claim(self):
        r=report();r['new_native_timer_cleanup_added']=True
        with self.assertRaises(RuntimeError):validate(r)
    def test_timing_and_cdo_restore_required(self):
        r=report();r['profiles'][0]['native_update_elapsed_seconds']=0.
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['cdo_profiles_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
