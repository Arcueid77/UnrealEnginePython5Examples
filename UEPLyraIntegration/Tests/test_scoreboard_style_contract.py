"""Require actual current-mode timer/static-target and activation parity."""
import unittest
from uep_lyra_hud.scoreboard_style_contract import PROFILES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',mode='tdm',profiles=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_replaced','timer_callbacks_replayed','activation_callbacks_replayed','localized_team_name_roundtripped','health_properties_written'):r[k]=False
    for k in ('native_source_style_pairs_match','widget_roots_removed','profile_selectors_restored','team_tag_deltas_restored','real_target_score_restored','original_health_unchanged'):r[k]=True
    for p in PROFILES:
        row=dict(profile=p,native_update_elapsed_seconds=1.,diagnostic_fallbacks=0)
        for k in ('team_names_match_native_literals','all_text_tints_match','all_brush_resources_and_source_fields_match','glow_rotation_speed_match','target_score_matches_mode','native_stat_tag_updates','target_not_refreshed_by_timer','actual_activation_callback','native_animation_playing','reactivation_matches_native_source_condition'):row[k]=True
        r['profiles'].append(row)
    return r


class ScoreboardStyleContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_team_style_cases'],4)
    def test_original_brush_localized_label_and_rotation_required(self):
        for k in ('team_names_match_native_literals','all_brush_resources_and_source_fields_match','glow_rotation_speed_match'):
            r=report();r['profiles'][0][k]=False
            with self.subTest(k=k),self.assertRaises(RuntimeError):validate(r)
    def test_native_timer_must_not_make_target_periodic(self):
        r=report();r['profiles'][0]['target_not_refreshed_by_timer']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_activation_must_be_actual_native_callback(self):
        r=report();r['profiles'][0]['actual_activation_callback']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_original_mode_target_and_team_counts_restore(self):
        r=report();r['real_target_score_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
