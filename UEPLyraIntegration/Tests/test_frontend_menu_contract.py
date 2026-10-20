"""Reject incomplete native async routes and manufactured terminal acceptance."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.frontend_menu_contract import PROFILES,ROUTES,FALSE_FIELDS,TRUE_FIELDS,validate

def report(mode='life'):
    r=dict(status='passed',error=None,native_mode='Standalone',mode=mode,profiles=[],source_python_state_pairs_match=True,native_request_exit_fallback_used=False);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    if mode=='quit':r.update(profile='Python',native_confirmed_quit_result=[0],native_quit_requested_from_original_confirmation=True)
    else:r['profiles']=[dict(profile=p,actual_activation_animation_and_focus_target=True,native_afterpush_routes=[[n,c] for n,_,c in ROUTES],native_declined_confirmation_results=[['quit',1],['logout',1]],original_prompt_localization_preserved=True,declines_leave_original_controller_world=True) for p in PROFILES]
    return r

class FrontendMenuContractTests(unittest.TestCase):
    def test_complete_native_lifecycle(self):self.assertEqual(validate(report())['native_afterpush_routes'],8)
    def test_complete_native_confirmed_quit(self):self.assertEqual(validate(report('quit'))['owned_native_confirmed_quit_profile'],'Python')
    def test_missing_or_reordered_route_is_not_accepted(self):
        for reverse in (False,True):
            r=report();r['profiles'][0]['native_afterpush_routes']=list(reversed(r['profiles'][0]['native_afterpush_routes'])) if reverse else []
            with self.assertRaises(RuntimeError):validate(r)
    def test_each_cleanup_and_scope_claim_is_checked(self):
        for field in FALSE_FIELDS+TRUE_FIELDS:
            r=report();r[field]=not r[field]
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_wrong_native_confirmation_result_is_rejected(self):
        r=report();r['profiles'][1]['native_declined_confirmation_results'][1][1]=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_fallback_exit_does_not_certify_original_quit(self):
        r=report('quit');r['native_request_exit_fallback_used']=True
        with self.assertRaises(RuntimeError):validate(r)
