"""Reject replayed timers, missing original removed-widget behavior or scope claims."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.credits_widgets_contract import FALSE_FIELDS,TRUE_FIELDS,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',native_timer_callbacks_per_profile_min=3,visibility_cases=10,manual_scroll_edge_cases=3,owned_fixture_scroll_speed_overridden=True,owned_fixture_endpoint_overridden_after_capture=True);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r

class CreditsContractTests(unittest.TestCase):
    def test_complete_bounded_matrix(self):self.assertEqual(validate(report())['native_profile_matrices'],2)
    def test_missing_natural_timer_callbacks_rejected(self):
        r=report();r['native_timer_callbacks_per_profile_min']=2
        with self.assertRaises(RuntimeError):validate(r)
    def test_original_removed_timer_behavior_required(self):
        r=report();r['rooted_deactivated_removed_widget_keeps_original_timer']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_scope_replay_or_unrun_pixels_rejected(self):
        for k in FALSE_FIELDS:
            r=report();r[k]=True
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
    def test_fixture_bounds_must_be_declared(self):
        for k in ('owned_fixture_scroll_speed_overridden','owned_fixture_endpoint_overridden_after_capture'):
            r=report();r[k]=False
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
