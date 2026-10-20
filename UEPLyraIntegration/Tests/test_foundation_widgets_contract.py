"""Reject synthetic lifecycle, localization or loading lifetime overclaims."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.foundation_widgets_contract import FALSE_FIELDS,TRUE_FIELDS,ROW_FIELDS,PROFILES,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in PROFILES:
        row=dict(profile=p,aspect_brush_cases=3,spinner_size_cases=3,native_reason_ticks=3,native_loading_changes=2);row.update(dict.fromkeys(ROW_FIELDS,True));r['profiles'].append(row)
    return r

class FoundationWidgetsContractTests(unittest.TestCase):
    def test_complete_bounded_native_matrix(self):self.assertEqual(validate(report())['native_widget_trials'],10)
    def test_missing_natural_tick_rejected(self):
        r=report();r['profiles'][0]['native_reason_ticks']=2
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_preserved_removed_host_callback_rejected(self):
        r=report();r['profiles'][1]['rooted_removed_loading_host_keeps_original_delegate']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_every_native_observation_is_enforced(self):
        for k in ROW_FIELDS:
            r=report();r['profiles'][0][k]=False
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
    def test_replayed_ticks_or_added_unbind_rejected(self):
        for k in FALSE_FIELDS:
            r=report();r[k]=True
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
