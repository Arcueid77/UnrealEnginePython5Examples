"""Require native exposed spawn/layout/filter/overlap/offline travel proof."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.editor_experience_contract import TRUE_FIELDS,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,profile='Python',native_filter_cases=[False,True],request_mode=0,pushed_handler_calls=1,native_destination_level='Map',native_request_map='/Game/Map',native_destination_experience='Experience',native_request_experience='Experience');r.update(dict.fromkeys(TRUE_FIELDS,True));r.update(dict.fromkeys(FALSE_FIELDS,False));return r
class EditorExperienceContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_editor_experience_profile'],'Python')
    def test_missing_native_observation_rejected(self):
        for field in TRUE_FIELDS:
            r=report();r[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_scope_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_wrong_filter_mode_or_push_count_rejected(self):
        for field,value in (('native_filter_cases',[True]),('request_mode',2),('pushed_handler_calls',2)):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_destination_rejected(self):
        for field,value in (('native_destination_level','Other'),('native_destination_experience','Other')):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_missing_cleanup_rejected(self):
        r=report();r['owned_roots_profiles_fixture_actors_and_loading_class_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
