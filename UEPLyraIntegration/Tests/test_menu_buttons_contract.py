"""Reject absent inherited children, native continuations and scope overclaims."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.menu_buttons_contract import FALSE_FIELDS,TRUE_FIELDS,ROW_FIELDS,PROFILES,WIDGETS,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',completion_guard_fixture_sets_only_owned_widget_flag=True,profiles=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in PROFILES:
        rows=[]
        for k in WIDGETS:
            row=dict(widget=k,raw_progress_cases=5,native_finished_callbacks=2,layout_cases=8,native_tile_art_parameter_matches=True);row.update(dict.fromkeys(ROW_FIELDS,True));rows.append(row)
        r['profiles'].append(dict(profile=p,widgets=rows))
    return r

class MenuContractTests(unittest.TestCase):
    def test_complete_bounded_native_matrix(self):self.assertEqual(validate(report())['native_widgets'],8)
    def test_missing_inherited_arrow_is_rejected(self):
        r=report();r['profiles'][1]['widgets'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_second_natural_completion_is_rejected(self):
        r=report();r['profiles'][0]['widgets'][0]['native_finished_callbacks']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_each_required_observation_is_enforced(self):
        for key in ROW_FIELDS:
            r=report();r['profiles'][1]['widgets'][1][key]=False
            with self.subTest(field=key),self.assertRaises(RuntimeError):validate(r)
    def test_unrun_input_or_network_claims_are_rejected(self):
        for key in FALSE_FIELDS:
            r=report();r[key]=True
            with self.subTest(field=key),self.assertRaises(RuntimeError):validate(r)
