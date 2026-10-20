"""Reject incomplete selection callbacks, request sequencing and quickplay travel."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.experience_screen_contract import PROFILES,FALSE_FIELDS,validate

FIELDS=('native_activation_animation_and_const_focus','native_list_selection_assigns_exact_definition','native_visible_hidden_spinner_states','native_online_request_payload_matches_definition','native_host_afterpush','native_browse_online_callback_then_browser_afterpush','native_browser_search_completes')
def report(mode='life'):
    r=dict(status='passed',error=None,initial_native_mode='Standalone',mode=mode,profiles=[],owned_roots_profiles_input_and_loading_class_restored=True,source_python_state_pairs_match=True,original_gameplay_health_unchanged=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    if mode=='life':r['profiles']=[dict(profile=p,**dict.fromkeys(FIELDS,True)) for p in PROFILES]
    else:r.update(profile='Python',native_online_initialize_success=True,native_async_preparation_then_online_request=True,native_quickplay_search_empty_then_host=True,native_destination_map_experience_and_player_ready=True,owned_native_session_destroyed=True,online_request_mode=2,quickplay_handler_calls=1,prepared_handler_calls=1)
    return r

class ExperienceScreenContractTests(unittest.TestCase):
    def test_complete_native_lifecycle(self):self.assertEqual(validate(report())['native_selection_profiles'],2)
    def test_complete_native_quickplay(self):self.assertEqual(validate(report('quick'))['native_null_quickplay_profile'],'Python')
    def test_all_lifecycle_observations_required(self):
        for field in FIELDS:
            r=report();r['profiles'][0][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_source_scope_overclaim_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_missing_native_prepare_or_session_cleanup_rejected(self):
        for field in ('native_async_preparation_then_online_request','owned_native_session_destroyed'):
            r=report('quick');r[field]=False
            with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_online_mode_and_duplicate_continuation_rejected(self):
        for field,value in (('online_request_mode',0),('prepared_handler_calls',2)):
            r=report('quick');r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
