"""Require actual level events,task release timing and owned unload cleanup."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.lobby_background_contract import PROFILES,FALSE_FIELDS,ROW_TRUE,validate
def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[dict(profile=p,loaded_callbacks=1,shown_callbacks=1,release_callbacks=1,release_delay_game_seconds=.5,**dict.fromkeys(ROW_TRUE,True)) for p in PROFILES],owned_roots_cdo_profile_and_original_health_restored=True);r.update(dict.fromkeys(FALSE_FIELDS,False));return r
class LobbyBackgroundContractTests(unittest.TestCase):
    def test_complete_native_profiles(self):self.assertEqual(validate(report())['native_lobby_streaming_profiles'],2)
    def test_missing_actual_level_task_or_unload_observation_rejected(self):
        for field in ROW_TRUE:
            r=report();r['profiles'][0][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_scope_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_duplicate_or_missing_native_callbacks_rejected(self):
        for field in ('loaded_callbacks','shown_callbacks','release_callbacks'):
            r=report();r['profiles'][0][field]=2
            with self.assertRaises(RuntimeError):validate(r)
    def test_early_release_rejected(self):
        r=report();r['profiles'][1]['release_delay_game_seconds']=.1
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_owned_cleanup_rejected(self):
        r=report();r['owned_roots_cdo_profile_and_original_health_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
