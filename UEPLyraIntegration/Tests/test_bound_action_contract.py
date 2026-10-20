"""Reject missing delegate lifetime, remount or animation completion evidence."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.bound_action_contract import FALSE_FIELDS,TRUE_FIELDS,ROW_FIELDS,PROFILES,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in PROFILES:
        row=dict(profile=p,typed_input_style_cases=4,actual_native_input_changes=3,native_finished_callbacks=2);row.update(dict.fromkeys(ROW_FIELDS,True));r['profiles'].append(row)
    return r

class BoundActionContractTests(unittest.TestCase):
    def test_complete_bounded_native_matrix(self):self.assertEqual(validate(report())['native_input_changes'],6)
    def test_missing_removed_widget_unbind_rejected(self):
        r=report();r['profiles'][0]['removed_widget_bp_input_delegate_unbound']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_each_lifetime_and_animation_observation_required(self):
        for k in ROW_FIELDS:
            r=report();r['profiles'][1][k]=False
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
    def test_missing_real_native_input_change_rejected(self):
        r=report();r['profiles'][0]['actual_native_input_changes']=2
        with self.assertRaises(RuntimeError):validate(r)
    def test_unrun_physical_or_replayed_callbacks_rejected(self):
        for k in FALSE_FIELDS:
            r=report();r[k]=True
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
