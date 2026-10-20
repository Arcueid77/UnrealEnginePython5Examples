"""Reject missing original native completions,class semantics or restoration."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.ui_preparation_probe_contract import CASES,FALSE_FIELDS,validate
def report():
    cases=[]
    for name in CASES:
        value=None if name in ('null','wrong_actor') else name
        cases.append(dict(case=name,expected_class=value,original_class=value,python_class=value,actual_original_native_completions=1,actual_helper_native_continuations=1,original_setter_notifications=1,python_setter_notifications=1))
    r=dict(status='passed',error=None,native_mode='Standalone',cases=cases,direct_python_helper_inputs=True,owned_objects_roots_loading_class_and_health_restored=True);r.update(dict.fromkeys(FALSE_FIELDS,False));return r
class UIExperiencePreparationContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_original_macro_cases'],4)
    def test_missing_case_rejected(self):
        r=report();r['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_scope_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_duplicate_or_missing_native_callback_rejected(self):
        for field in ('actual_original_native_completions','actual_helper_native_continuations','original_setter_notifications','python_setter_notifications'):
            r=report();r['cases'][0][field]=2
            with self.assertRaises(RuntimeError):validate(r)
    def test_pure_cast_failure_must_clear_and_continue(self):
        r=report();r['cases'][-1].update(expected_class='Actor',original_class='Actor',python_class='Actor')
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_restoration_rejected(self):
        r=report();r['owned_objects_roots_loading_class_and_health_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
