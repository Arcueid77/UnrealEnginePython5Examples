"""Natural lifecycle,actual tick samples and opaque pointer replies are required."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.replay_runtime_contract import TRUE_FIELDS,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,profile='Python',synthetic_slate_pointer_inputs=[.75,.2],native_handled_replies=[True,True],native_seek_samples=[{'target':3.},{'target':.8}],native_tick_samples=3,direct_zero_width_slate_pointer_input=True);r.update(dict.fromkeys(TRUE_FIELDS,True));r.update(dict.fromkeys(FALSE_FIELDS,False));return r
class ReplayRuntimeContractTests(unittest.TestCase):
    def test_complete_runtime_matrix(self):self.assertEqual(validate(report())['native_seek_inputs'],2)
    def test_missing_native_lifecycle_or_tick_observation_rejected(self):
        for field in TRUE_FIELDS:
            r=report();r[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_scope_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_unhandled_original_reply_rejected(self):
        r=report();r['native_handled_replies']=[True,False]
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_pointer_or_tick_samples_rejected(self):
        for field,value in (('native_seek_samples',[]),('native_tick_samples',0),('synthetic_slate_pointer_inputs',[.75])):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_missing_zero_width_input_boundary_rejected(self):
        r=report();r['direct_zero_width_slate_pointer_input']=False
        with self.assertRaises(RuntimeError):validate(r)
