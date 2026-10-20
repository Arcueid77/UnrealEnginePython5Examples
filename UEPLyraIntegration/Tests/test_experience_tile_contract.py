"""Reject incomplete native sound, localization or source-asymmetry evidence."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.experience_tile_contract import FALSE_FIELDS,TRUE_FIELDS,ROW_FIELDS,PROFILES,validate

def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for p in PROFILES:
        row=dict(profile=p,raw_progress_cases=5,texture_cases=3,native_finished_callbacks=2,spawned_click_audio=[dict(playing=True,auto_destroy=True,existing_before_click=False,ui_sound=True,spatialized=False,stop_with_owner=False)]*2);row.update(dict.fromkeys(ROW_FIELDS,True));r['profiles'].append(row)
    return r

class ExperienceContractTests(unittest.TestCase):
    def test_complete_bounded_native_matrix(self):self.assertEqual(validate(report())['native_spawned_audio'],4)
    def test_missing_reference_restore_rejected(self):
        r=report();r['original_game_instance_sound_reference_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_existing_or_inactive_sound_not_accepted_as_new_spawn(self):
        for field,value in (('existing_before_click',True),('playing',False),('auto_destroy',False)):
            r=report();r['profiles'][0]['spawned_click_audio']=[dict(r['profiles'][0]['spawned_click_audio'][0],**{field:value})]*2
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_every_required_observation_is_enforced(self):
        for key in ROW_FIELDS:
            r=report();r['profiles'][0][key]=False
            with self.subTest(field=key),self.assertRaises(RuntimeError):validate(r)
    def test_unrun_physical_or_travel_claim_rejected(self):
        for key in FALSE_FIELDS:
            r=report();r[key]=True
            with self.subTest(field=key),self.assertRaises(RuntimeError):validate(r)
