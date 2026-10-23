from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud import session_browser_failure_contract as gate
from uep_lyra_hud.startup import validation_module


def fixture():
    flags=('native_initial_search_completed','native_bad_player_failure_dialog','native_error_ftext_history_preserved',
        'native_acknowledgement_and_refresh_recovery','native_pending_screen_close_matches_original',
        'native_reactivation_started_distinct_request','native_pending_widget_collected_before_completion',
        'native_request_completed_without_destroyed_widget_callback','exclusive_selected_profile_calls')
    report=dict(status='passed',error=None,native_mode='Standalone',profiles=[dict(profile=p,native_notification_sequence=[True,False,True,True],
        search_calls=3,results_calls=3,unlock_calls=3,**dict.fromkeys(flags,True)) for p in ('BlueprintFallback','Python')],
        source_python_states_match=True,owned_roots_profiles_input_and_loading_class_restored=True,original_gameplay_health_unchanged=True)
    report.update(dict.fromkeys(('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested',
        'online_provider_failure_tested','backend_search_cancelled','callbacks_replayed','health_properties_written'),False))
    return report


class BrowserFailureContract(unittest.TestCase):
    def test_real_failure_hidden_completion_and_collected_receiver_are_separate(self):
        self.assertTrue(gate.validate(fixture()))

    def test_screen_close_cannot_claim_backend_cancellation(self):
        report=fixture();report['backend_search_cancelled']=True
        with self.assertRaises(RuntimeError):gate.validate(report)

    def test_collection_after_completion_is_not_pending_receiver_coverage(self):
        report=fixture();report['profiles'][1]['native_pending_widget_collected_before_completion']=False
        with self.assertRaises(RuntimeError):gate.validate(report)

    def test_missing_failure_or_late_receiver_callback_fails(self):
        for key,value in (('native_notification_sequence',[True,True,True,True]),('results_calls',4),('native_request_completed_without_destroyed_widget_callback',False)):
            report=fixture();report['profiles'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):gate.validate(report)

    def test_cleanup_or_provider_error_overclaim_fails(self):
        for key,value in (('owned_roots_profiles_input_and_loading_class_restored',False),('online_provider_failure_tested',True)):
            report=fixture();report[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):gate.validate(report)

    def test_native_lane_remains_explicit_and_commandlets_do_not_run_it(self):
        self.assertIsNone(validation_module([]))
        self.assertEqual(validation_module(['-UEPSessionBrowserFailureResult=owned.json']),'uep_lyra_hud.session_browser_failure_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPSessionBrowserFailureResult=owned.json']))
