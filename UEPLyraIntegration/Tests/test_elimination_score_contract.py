"""Require actual countdown delegates, source lifetime and cleanup evidence."""
import unittest
from uep_lyra_hud.elimination_score_contract import PROFILES,FALSE_FIELDS,TRUE_FIELDS,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in PROFILES:
        row=dict(profile=p,style_cases=3,score_cases=4,clock_cases=12,score_sound_cases=8,native_clock_interval=1.,diagnostic_fallbacks=0);row.update(dict.fromkeys(('actual_construct_and_async_team_binding','full_brush_fields_and_tints_match','numeric_values_and_unclamped_arcs_match','localized_clock_floor_and_audio_match','score_audio_parameters_match','actual_native_score_ticks','native_player_counted_delegate','native_countdown_timer_delegate','removed_tick_stops_but_countdown_binding_remains','remount_callback_count_matches_source'),True));r['profiles'].append(row)
    return r


class TDMHudContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['clock_cases'],24)
    def test_native_timer_and_retained_binding_lifetime_required(self):
        for key in ('native_countdown_timer_delegate','removed_tick_stops_but_countdown_binding_remains','native_player_counted_delegate'):
            r=report();r['profiles'][1][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_restoration_and_scope_claims_are_enforced(self):
        for key,value in (('real_countdown_value_restored',False),('production_localized_text_roundtripped',True)):
            r=report();r[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_native_interval_cannot_be_faked_with_rapid_callbacks(self):
        r=report();r['profiles'][0]['native_clock_interval']=.1
        with self.assertRaises(RuntimeError):validate(r)
