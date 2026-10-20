"""Reject unsampled pairs, lost native locale formats or diagnostic overclaims."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.diagnostic_widgets_contract import FALSE_FIELDS,TRUE_FIELDS,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',native_cached_stat_subsystem_valid=True,same_frame_performance_cases=8,native_performance_tick_observations=24,native_format_value_cases=24,native_format_fractional_digit_variants=3,native_watermark_player_cases=4,native_missing_controller_localized_status_verified=True,native_valid_user_branch_exercised=True);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r

class DiagnosticContractTests(unittest.TestCase):
    def test_complete_bounded_matrix(self):self.assertEqual(validate(report())['native_format_value_cases'],24)
    def test_missing_same_frame_case_rejected(self):
        r=report();r['same_frame_performance_cases']=7
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_real_tick_observations_rejected(self):
        r=report();r['native_performance_tick_observations']=23
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_localized_missing_user_status_rejected(self):
        r=report();r['native_missing_controller_localized_status_verified']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_cache_writes_or_unrun_pixels_claims_rejected(self):
        for k in FALSE_FIELDS:
            r=report();r[k]=True
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
