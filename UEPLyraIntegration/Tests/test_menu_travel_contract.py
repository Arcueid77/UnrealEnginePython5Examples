"""Reject transport-only, wrong-map, leaked-URL and incomplete frontend evidence."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.menu_travel_contract import MAP,EXPERIENCE,EXPERIENCE_CLASS,FRONTEND,FALSE_FIELDS,TRUE_FIELDS,validate

def report():
    r=dict(status='passed',error=None,profile='Python',initial_native_mode='Standalone',confirmation_results=[0],menu_result_handler_calls=1,old_world_path='/ShooterMaps/Maps/L_Expanse.L_Expanse',new_world_path=MAP,native_experience_option=EXPERIENCE,native_experience_class=EXPERIENCE_CLASS,native_frontend_widget_class=FRONTEND,native_frontend_profile='Python',native_primary_local_user_state=5);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r

class MenuTravelContractTests(unittest.TestCase):
    def test_complete_native_travel(self):self.assertEqual(validate(report())['native_confirmed_frontend_travel_profile'],'Python')
    def test_every_native_destination_and_cleanup_observation_required(self):
        for field in TRUE_FIELDS:
            r=report();r[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_scope_and_callback_replay_claims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_wrong_native_map_experience_or_frontend_rejected(self):
        for field in ('new_world_path','native_experience_option','native_experience_class','native_frontend_widget_class'):
            r=report();r[field]='wrong'
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_declined_or_repeated_result_rejected(self):
        for field,value in (('confirmation_results',[1]),('menu_result_handler_calls',2)):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_uninitialized_user_or_wrong_profile_rejected(self):
        for field,value in (('native_primary_local_user_state',0),('native_frontend_profile','BlueprintFallback')):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
