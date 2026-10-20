"""Keep helper acceptance separate from remaining whole-character migration."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_characters.explorer_helpers_contract import FALSE_FIELDS,TRUE_FIELDS,CASES,validate

def report():
    r=dict(status='passed',error=None,profile='Python',characters=[dict(kind=k,natural_grant_calls=1,native_asc_ready=True,unarmed_unlinked_before_and_relinked_after=True,audio_roundtrip=True,missing_component_cases=True,unpossessed_noops=True,cases=[dict(name=n,expected_shape_matches=True,clear_verified=True,slot_events_match=True) for n in CASES]) for k in ('hero','pawn')]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r
class ExplorerHelpersContractTests(unittest.TestCase):
    def test_complete_two_character_native_matrix(self):self.assertEqual(validate(report())['cases'],10)
    def test_every_native_observation_is_required(self):
        for name in TRUE_FIELDS:
            r=report();r[name]=False
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_whole_character_and_other_scope_overclaims_rejected(self):
        for name in FALSE_FIELDS:
            r=report();r[name]=True
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_startup_and_actual_asc_are_required(self):
        for key,value in (('natural_grant_calls',0),('native_asc_ready',False)):
            r=report();r['characters'][0][key]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_original_unarmed_and_audio_and_negative_cases_required(self):
        for key in ('unarmed_unlinked_before_and_relinked_after','audio_roundtrip','missing_component_cases','unpossessed_noops'):
            r=report();r['characters'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_both_classes_and_every_loadout_case_required(self):
        r=report();r['characters'].pop()
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['characters'][1]['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_slot_payload_and_clear_required(self):
        for key in ('expected_shape_matches','clear_verified','slot_events_match'):
            r=report();r['characters'][0]['cases'][1][key]=False
            with self.assertRaises(RuntimeError):validate(r)
