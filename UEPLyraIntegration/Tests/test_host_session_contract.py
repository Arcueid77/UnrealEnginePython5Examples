"""Require full native host mode/bot payloads and real owned-session cleanup."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.host_session_contract import PROFILES,FALSE_FIELDS,validate

FIELDS=('native_activation_const_focus_and_labels','native_mode_button_cycle_online_lan_offline','native_bots_button_and_localized_labels','native_null_request_returns_none','native_six_mode_bot_request_payloads')
def report(mode='life'):
    r=dict(status='passed',error=None,initial_native_mode='Standalone',mode=mode,profiles=[],owned_roots_profiles_input_and_loading_class_restored=True,source_python_state_pairs_match=True,original_gameplay_health_unchanged=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    if mode=='life':r['profiles']=[dict(profile=p,mode_cycle=[1,0,2],request_cases=6,**dict.fromkeys(FIELDS,True)) for p in PROFILES]
    else:r.update(profile='Python',native_actual_entry_selection_and_online_init=True,native_spinner_afterpush_and_async_loading_before_submit=True,native_create_completion_handler_after_original_unbind=True,native_requested_map_experience_player_and_bot_option_ready=True,owned_native_session_destroyed=True,request_mode=2,request_bots='0',prepared_handler_calls=1,completion_handler_calls=1)
    return r

class HostSessionContractTests(unittest.TestCase):
    def test_complete_lifecycle(self):self.assertEqual(validate(report())['request_payload_cases'],12)
    def test_complete_native_hosting(self):self.assertEqual(validate(report('host'))['native_null_online_host_profile'],'Python')
    def test_missing_lifecycle_observations_rejected(self):
        for field in FIELDS:
            r=report();r['profiles'][0][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_scope_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_wrong_mode_bot_option_or_completion_count_rejected(self):
        for field,value in (('request_mode',0),('request_bots','1'),('completion_handler_calls',2)):
            r=report('host');r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_missing_owned_session_cleanup_rejected(self):
        r=report('host');r['owned_native_session_destroyed']=False
        with self.assertRaises(RuntimeError):validate(r)
