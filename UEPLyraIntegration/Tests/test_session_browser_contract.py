"""Missing native lock,completion or caller observations must not pass."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.session_browser_contract import PROFILES,FALSE_FIELDS,ROW_TRUE,validate
def report():
    r=dict(status='passed',error=None,initial_native_mode='Standalone',profiles=[dict(profile=p,native_pooled_browser_reused=i==1,actual_native_search_completions=3,result_counts=[0,0,0],**dict.fromkeys(ROW_TRUE,True)) for i,p in enumerate(PROFILES)],owned_roots_profiles_input_and_loading_class_restored=True,original_gameplay_health_unchanged=True,source_python_state_pairs_match=True);r.update(dict.fromkeys(FALSE_FIELDS,False));return r
class SessionBrowserContractTests(unittest.TestCase):
    def test_complete_native_profiles(self):self.assertEqual(validate(report())['actual_native_search_completions'],6)
    def test_missing_native_observation_rejected(self):
        for field in ROW_TRUE:
            r=report();r['profiles'][0][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_scope_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_missing_callback_or_wrong_native_result_matrix_rejected(self):
        for field,value in (('actual_native_search_completions',2),('result_counts',[0,0,1])):
            r=report();r['profiles'][1][field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_missing_caller_profile_rejected(self):
        r=report();r['profiles'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_actual_pool_reactivation_rejected(self):
        r=report();r['profiles'][1]['native_pooled_browser_reused']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_unrestored_health_or_roots_rejected(self):
        for field in ('owned_roots_profiles_input_and_loading_class_restored','original_gameplay_health_unchanged','source_python_state_pairs_match'):
            r=report();r[field]=False
            with self.assertRaises(RuntimeError):validate(r)
