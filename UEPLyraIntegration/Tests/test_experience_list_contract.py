"""Native list evidence requires real completions, original cache and caller delivery."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.experience_list_contract import PROFILES,FALSE_FIELDS,COMMON_TRUE,ROW_TRUE,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',trials=[],source_python_state_pairs_match=True);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(COMMON_TRUE,True))
    for p in PROFILES:
        for show in (False,True):
            row=dict(profile=p,show_all=show,visible_entries=3,native_completed_loads=2,native_async_actions_observed=2,initial_cache_size=3,remount_cache_size=6,native_selection_events=4,fixture_collapsed_content_original_visibility=1,fixture_temporarily_expanded_for_focus=True);row.update(dict.fromkeys(ROW_TRUE,True));r['trials'].append(row)
    return r

class ExperienceListContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_asset_load_completions'],8)
    def test_all_native_observations_and_scope_checks_required(self):
        for field in FALSE_FIELDS+COMMON_TRUE:
            r=report();r[field]=not r[field]
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
        for field in ROW_TRUE:
            r=report();r['trials'][0][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_cleared_cache_cannot_certify_original_accumulation(self):
        r=report();r['trials'][0]['remount_cache_size']=3
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_async_or_selection_events_rejected(self):
        for field,value in (('native_completed_loads',1),('native_async_actions_observed',1),('native_selection_events',3)):
            r=report();r['trials'][0][field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_profile_show_all_order_rejected(self):
        r=report();r['trials'].reverse()
        with self.assertRaises(RuntimeError):validate(r)
    def test_state_pair_mismatch_rejected(self):
        r=report();r['source_python_state_pairs_match']=False
        with self.assertRaises(RuntimeError):validate(r)
