"""Native user lifecycle gate rejects missing callbacks, duplicate binds and scope claims."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.startup_login_contract import PROFILES,FALSE_FIELDS,ROW_TRUE,COMMON_TRUE,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',source_python_state_pairs_match=True,profiles=[],fixture_inert_character_event_created_secondary_slate_user=True,fixture_slate_user_lifetime='owned standalone process until normal shutdown');r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(COMMON_TRUE,True))
    for p in PROFILES:
        row=dict(profile=p,controller_indices=[-1,0,1,7],logged_in_results=[False,True,False,False],natural_initialize_user_indices=[1,0,0],removed_callback_deltas=[1,1],remounted_callback_deltas=[1,1]);row.update(dict.fromkeys(ROW_TRUE,True));r['profiles'].append(row)
    return r

class StartupLoginContractTests(unittest.TestCase):
    def test_complete_native_lifecycle(self):self.assertEqual(validate(report())['natural_initialize_callbacks'],6)
    def test_all_lifetime_cleanup_and_scope_claims_are_required(self):
        for field in FALSE_FIELDS+COMMON_TRUE:
            r=report();r[field]=not r[field]
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
        for field in ROW_TRUE:
            r=report();r['profiles'][0][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_controller_validity_is_not_replaced_by_account_availability(self):
        r=report();r['profiles'][1]['logged_in_results']=[False,False,False,False]
        with self.assertRaises(RuntimeError):validate(r)
    def test_duplicate_remount_binding_is_rejected(self):
        r=report();r['profiles'][0]['remounted_callback_deltas']=[2,2]
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_removed_callback_is_rejected(self):
        r=report();r['profiles'][0]['removed_callback_deltas']=[1,0]
        with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_native_user_indices_or_profile_state_is_rejected(self):
        r=report();r['profiles'][0]['natural_initialize_user_indices']=[0,0,0]
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['source_python_state_pairs_match']=False
        with self.assertRaises(RuntimeError):validate(r)
