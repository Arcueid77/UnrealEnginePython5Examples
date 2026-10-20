"""Reject missing native lifecycle/quit evidence and unrun terminal claims."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.menu_layers_contract import FALSE_FIELDS,COMMON_TRUE,ROW_FIELDS,PROFILES,validate

def report(mode='life'):
    r=dict(status='passed',error=None,native_mode='Standalone',mode=mode,profiles=[],source_python_state_pairs_match=True,native_request_exit_fallback_used=False);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(COMMON_TRUE,True))
    if mode=='quit':r.update(profile='Python',native_quit_requested_by_owned_menu=True,native_input_reset_to_mouse_before_quit=True)
    else:
        for p in PROFILES:
            row=dict(profile=p,native_afterpush_callbacks=1,native_confirmation_results=[1]);row.update(dict.fromkeys(ROW_FIELDS,True));r['profiles'].append(row)
    return r

class MenuLayerContractTests(unittest.TestCase):
    def test_complete_lifecycle(self):self.assertEqual(validate(report())['native_lifecycle_profile_matrices'],2)
    def test_complete_owned_native_quit(self):self.assertEqual(validate(report('quit'))['owned_native_quit_profile'],'Python')
    def test_request_exit_fallback_cannot_certify_native_quit(self):
        r=report('quit');r['native_request_exit_fallback_used']=True
        with self.assertRaises(RuntimeError):validate(r)
    def test_each_lifecycle_observation_required(self):
        for k in ROW_FIELDS:
            r=report();r['profiles'][0][k]=False
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
    def test_replayed_result_or_unrun_confirmed_travel_rejected(self):
        for k in FALSE_FIELDS:
            r=report();r[k]=True
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
