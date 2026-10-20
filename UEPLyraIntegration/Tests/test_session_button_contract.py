"""Reject incomplete native button observations and enlarged acceptance claims."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.session_button_contract import PROFILES,FALSE_FIELDS,ROW_TRUE,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[dict(profile=p,native_finished_callbacks=1,**dict.fromkeys(ROW_TRUE,True)) for p in PROFILES],owned_roots_profiles_and_gameplay_health_restored=True,source_python_state_pairs_match=True,direct_blueprint_event_inputs=['BP_OnHovered','BP_OnUnhovered']);r.update(dict.fromkeys(FALSE_FIELDS,False));return r

class SessionButtonContractTests(unittest.TestCase):
    def test_complete_native_pair(self):self.assertEqual(validate(report())['native_session_button_profiles'],2)
    def test_missing_native_observations_rejected(self):
        for field in ROW_TRUE:
            r=report();r['profiles'][0][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_scope_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_wrong_finished_count_rejected(self):
        for value in (0,2):
            r=report();r['profiles'][1]['native_finished_callbacks']=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_omitted_direct_hover_input_rejected(self):
        r=report();r['direct_blueprint_event_inputs']=[]
        with self.assertRaises(RuntimeError):validate(r)
    def test_cleanup_and_profile_mismatch_rejected(self):
        for field in ('owned_roots_profiles_and_gameplay_health_restored','source_python_state_pairs_match'):
            r=report();r[field]=False
            with self.assertRaises(RuntimeError):validate(r)
