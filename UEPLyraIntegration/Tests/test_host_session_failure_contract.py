import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Overlay/Content/Scripts'))
from uep_lyra_hud import host_session_failure_contract as gate
from uep_lyra_hud.startup import validation_module


def fixture():
    flags = ('native_tile_click_and_spinner', 'selected_experience_invalidated_only_at_prepared_entry',
        'native_failed_completion_and_error_dialog', 'native_error_ftext_history_preserved', 'native_spinner_popped',
        'native_acknowledge_button_closed_dialog', 'native_second_failure_did_not_reenter_unbound_widget', 'no_late_callbacks_or_world_change')
    rows = [dict(profile=p, prepared_calls=1, completed_calls=1, invalidations=1, native_failure_notifications=2,
        exclusive_selected_profile_calls=True, **dict.fromkeys(flags, True)) for p in ('BlueprintFallback', 'Python')]
    report = dict(status='passed', error=None, native_mode='Standalone', profiles=rows, native_failure_notifications=4,
        source_python_failure_states_match=True, owned_roots_profiles_input_and_loading_class_restored=True,
        profile_methods_restored=True, original_gameplay_health_unchanged=True)
    report.update(dict.fromkeys(('full_acceptance','network_acceptance','packaged_runtime','pixels_tested',
        'physical_button_input_tested','online_provider_failure_tested','callbacks_replayed','health_properties_written'), False))
    return report


class HostFailureContract(unittest.TestCase):
    def test_native_invalid_request_does_not_claim_online_provider_failure(self):
        self.assertTrue(gate.validate(fixture()))

    def test_missing_dialog_or_second_failure_control_fails(self):
        for field in ('native_error_ftext_history_preserved', 'native_second_failure_did_not_reenter_unbound_widget', 'exclusive_selected_profile_calls'):
            report=fixture(); report['profiles'][1][field]=False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(report)

    def test_duplicate_completion_or_missing_native_notification_fails(self):
        for field in ('completed_calls', 'native_failure_notifications'):
            report=fixture(); report['profiles'][0][field]+=1
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(report)

    def test_cleanup_and_scope_overclaim_fail(self):
        for field,value in (('profile_methods_restored',False),('callbacks_replayed',True),('online_provider_failure_tested',True)):
            report=fixture(); report[field]=value
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(report)

    def test_missing_original_profile_is_not_a_comparison(self):
        report=fixture(); report['profiles'].pop(0)
        with self.assertRaises(RuntimeError): gate.validate(report)

    def test_lane_requires_an_explicit_play_flag(self):
        self.assertIsNone(validation_module([]))
        self.assertEqual(validation_module(['-UEPHostSessionFailureResult=owned.json']), 'uep_lyra_hud.host_session_failure_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPHostSessionFailureResult=owned.json']))
