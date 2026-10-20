"""Reject missing native assignments, localization or read-only settings gates."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.settings_editors_contract import FALSE_FIELDS,TRUE_FIELDS,ROW_FIELDS,PROFILES,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in PROFILES:
        row=dict(profile=p,focus_cases=5,hover_widget_cases=7,scalar_value_cases=5,scalar_default_cases=3,rotator_style_cases=9,rotator_index_cases=5,enum_option_count=2);row.update(dict.fromkeys(ROW_FIELDS,True));r['profiles'].append(row)
    return r

class SettingsEditorsContractTests(unittest.TestCase):
    def test_complete_bounded_matrix(self):self.assertEqual(validate(report())['presentation_widget_classes'],10)
    def test_native_assignment_evidence_required(self):
        r=report();r['profiles'][0]['actual_native_list_assignment_preserves_localized_action_and_navigation_labels']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_every_observation_is_enforced(self):
        for k in ROW_FIELDS:
            r=report();r['profiles'][1][k]=False
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
    def test_settings_writes_and_unrun_input_claims_rejected(self):
        for k in FALSE_FIELDS:
            r=report();r[k]=True
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
    def test_persistent_config_or_native_index_change_rejected(self):
        for k in ('settings_config_files_unchanged','native_selected_setting_index_unchanged'):
            r=report();r[k]=False
            with self.subTest(field=k),self.assertRaises(RuntimeError):validate(r)
