"""Native identity logout/reset/startup evidence must match the original async class."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.frontend_logout_contract import PROFILES,FALSE_FIELDS,TRUE_FIELDS,ROW_TRUE,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[],source_python_state_pairs_match=True);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for profile in PROFILES:
        row=dict(profile=profile,confirmation_results=[0],native_logout_success_delta=1,native_initialize_user_indices=[0],native_async_logout_proxy_class='/Script/OnlineSubsystemUtils.LogoutCallbackProxy',new_destroy_session_proxies=0);row.update(dict.fromkeys(ROW_TRUE,True));r['profiles'].append(row)
    return r

class FrontendLogoutContractTests(unittest.TestCase):
    def test_complete_native_logout(self):self.assertEqual(validate(report())['native_confirmed_identity_logout_profiles'],2)
    def test_all_native_sequence_observations_are_required(self):
        for field in ROW_TRUE:
            r=report();r['profiles'][0][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_cleanup_and_scope_are_required(self):
        for field in TRUE_FIELDS+FALSE_FIELDS:
            r=report();r[field]=not r[field]
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_native_confirmation_must_actually_be_confirmed(self):
        r=report();r['profiles'][0]['confirmation_results']=[1]
        with self.assertRaises(RuntimeError):validate(r)
    def test_duplicate_success_or_wrong_user_is_rejected(self):
        for field,value in (('native_logout_success_delta',2),('native_initialize_user_indices',[1])):
            r=report();r['profiles'][1][field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_original_identity_proxy_and_absence_of_destroy_proxy_are_required(self):
        for field,value in (('native_async_logout_proxy_class','/Script/OnlineSubsystemUtils.DestroySessionCallbackProxy'),('new_destroy_session_proxies',1)):
            r=report();r['profiles'][0][field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_profile_order_and_state_pair_are_required(self):
        r=report();r['profiles'].reverse()
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['source_python_state_pairs_match']=False
        with self.assertRaises(RuntimeError):validate(r)
