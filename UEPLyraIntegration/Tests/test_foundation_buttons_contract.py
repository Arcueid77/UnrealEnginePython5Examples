"""Require actual CommonUI parent/input/tab routing and UMG frame observations."""
import unittest
from uep_lyra_hud.foundation_buttons_contract import PROFILES,FALSE_FIELDS,TRUE_FIELDS,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in PROFILES:
        row=dict(profile=p,native_button_style_cases=4,alignment_cases=4,progress_cases=5,dynamic_tabs_created=3);row.update(dict.fromkeys(('native_construct_and_button_text_refresh','native_input_style_and_current_text_style_match','alignment_and_raw_press_progress_match','opaque_ftext_history_preserved','actual_native_selection_and_deselection_callbacks','native_hover_selected_animation_guards','actual_native_tab_registration_labels_and_removal','native_tab_selection_and_visibility_delegates','designer_preview_is_explicit_only'),True));r['profiles'].append(row)
    return r


class FoundationContractTests(unittest.TestCase):
    def test_complete_native_ui_matrix(self):self.assertEqual(validate(report())['native_dynamic_tab_cases'],6)
    def test_native_input_and_selection_callbacks_required(self):
        for key in ('native_input_style_and_current_text_style_match','actual_native_selection_and_deselection_callbacks'):
            r=report();r['profiles'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_opaque_text_and_input_restoration_required(self):
        r=report();r['profiles'][1]['opaque_ftext_history_preserved']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_hardware_hover_claim_cannot_replace_explicit_scope(self):
        r=report();r['physical_hover_input_tested']=True
        with self.assertRaises(RuntimeError):validate(r)
