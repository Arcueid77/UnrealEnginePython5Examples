"""Appearance acceptance must retain helper regression and native evidence."""
import unittest
from test_explorer_helpers_contract import report as helpers_report
from uep_lyra_characters.explorer_style_contract import validate,CASES

def report():
    r=helpers_report();r.update(hardware_output_tested=False,pixels_tested=False,owned_device_markers_and_roots_released=True)
    for row in r['characters']:row.update(style_cases=[dict(name=n,native_values_match=True) for n in CASES],existing_mid_reused_without_new_blend=True,nonlocal_outline_is_noop=True,native_device_count_matches_platform_validity=True,native_device_evaluations_and_retirement_observed=True)
    return r
class ExplorerStyleContractTests(unittest.TestCase):
    def test_complete_native_style_and_helpers(self):self.assertEqual(validate(report())['style_cases'],10)
    def test_all_original_style_cases_required(self):
        r=report();r['characters'][0]['style_cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_values_and_cache_and_guard_required(self):
        for name in ('existing_mid_reused_without_new_blend','nonlocal_outline_is_noop','native_device_count_matches_platform_validity','native_device_evaluations_and_retirement_observed'):
            r=report();r['characters'][0][name]=False
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_native_parameter_mismatch_rejected(self):
        r=report();r['characters'][1]['style_cases'][2]['native_values_match']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_helper_regression_still_required(self):
        r=report();r['characters'][0]['cases'][0]['clear_verified']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_scope_and_observer_cleanup_required(self):
        for name,value in (('hardware_output_tested',True),('pixels_tested',True),('owned_device_markers_and_roots_released',False)):
            r=report();r[name]=value
            with self.assertRaises(RuntimeError):validate(r)
