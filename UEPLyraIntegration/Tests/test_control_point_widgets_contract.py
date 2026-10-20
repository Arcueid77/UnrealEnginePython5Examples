"""Reject incomplete CP matrices, missing cleanup and overclaimed evidence."""
import unittest
from uep_lyra_hud.control_point_widgets_contract import PROFILES,FALSE_FIELDS,TRUE_FIELDS,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in PROFILES:
        row=dict(profile=p,style_cases=3,marker_cases=13,sound_cases=8,status_cases=3,diagnostic_fallbacks=0)
        row.update(dict.fromkeys(('actual_construct_and_native_async_binding','actual_score_and_status_ticks','style_brush_fields_and_colors_match','native_text_and_clamp_match','all_marker_scalar_states_match','owner_animation_condition_match','status_index_and_negative_team_guard_match','score_left_native_audio_parameters_match','unchanged_score_does_not_retrigger','removed_widgets_stop_native_ticks'),True));r['profiles'].append(row)
    return r


class CPWidgetContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['marker_cases'],26)
    def test_native_ticks_and_audio_cannot_be_omitted(self):
        for key in ('actual_score_and_status_ticks','score_left_native_audio_parameters_match','all_marker_scalar_states_match'):
            r=report();r['profiles'][1][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_scope_limits_are_enforced(self):
        r=report();r['pixels_tested']=True
        with self.assertRaises(RuntimeError):validate(r)
    def test_original_point_roster_and_tags_must_restore(self):
        for key in ('original_point_state_restored','team_tag_deltas_restored'):
            r=report();r[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
