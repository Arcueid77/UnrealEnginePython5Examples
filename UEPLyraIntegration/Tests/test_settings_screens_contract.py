"""Reject absent native modal completions or unrecovered calibration state."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.settings_screens_contract import FALSE_FIELDS,TRUE_FIELDS,ROW_FIELDS,PROFILES,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[],temporary_native_hdr_overrides_exercised=True);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in PROFILES:
        row=dict(profile=p,registered_tab_callbacks=5,hdr_luminance_cases=5,native_modal_afterpush_callbacks=3);row.update(dict.fromkeys(ROW_FIELDS,True));r['profiles'].append(row)
    return r

class SettingsScreensContractTests(unittest.TestCase):
    def test_complete_bounded_matrix(self):self.assertEqual(validate(report())['native_async_modal_pushes'],6)
    def test_missing_real_async_completion_rejected(self):
        r=report();r['profiles'][0]['native_modal_afterpush_callbacks']=2
        with self.assertRaises(RuntimeError):validate(r)
    def test_every_observation_is_enforced(self):
        for k in ROW_FIELDS:
            r=report();r['profiles'][1][k]=False
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
    def test_applied_settings_or_replayed_completion_rejected(self):
        for k in FALSE_FIELDS:
            r=report();r[k]=True
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
    def test_native_hdr_restoration_and_config_identity_required(self):
        for k in ('settings_and_native_hdr_overrides_restored','settings_config_files_unchanged'):
            r=report();r[k]=False
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
