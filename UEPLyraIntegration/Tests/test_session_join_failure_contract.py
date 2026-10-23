import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud import session_join_failure_contract as gate
from uep_lyra_hud.startup import validation_module


def client(profile='Python'):
    report=dict(status='passed',error=None,role='client',profile=profile,native_destination_mode='Client',native_destination_level='Owned',native_destination_experience='Exp',
        native_join_notification_sequence=[True,False,True],native_failure_error_id='UnknownError',duplicate_prepared_calls=2,duplicate_completion_calls=2,
        failure_state=dict(body='localized native failure'))
    report.update(dict.fromkeys(gate.FALSE_FIELDS,False));report.update(dict.fromkeys(gate.CLIENT_TRUE,True))
    report.update(dict.fromkeys(('failed_join_error_ui_natively_tested','duplicate_row_uses_actual_advertised_result','native_duplicate_join_rejected',
        'native_failure_ftext_history_preserved','native_spinner_popped_after_failure','native_acknowledgement_closed_error_dialog',
        'failure_cleanup_destroyed_owned_named_session','native_retry_rejoined_same_host','initial_row_not_reentered_by_other_join_notifications','exclusive_selected_profile_calls'),True))
    return report


class SessionJoinFailureContract(unittest.TestCase):
    def test_real_success_rejection_and_retry_are_required(self):self.assertTrue(gate.validate_peer(client()))

    def test_ui_failure_without_native_provider_result_is_rejected(self):
        report=client();report['native_join_notification_sequence']=[True,True,True]
        with self.assertRaises(RuntimeError):gate.validate_peer(report)

    def test_missing_retry_cleanup_or_unbound_control_is_rejected(self):
        for field in ('native_retry_rejoined_same_host','failure_cleanup_destroyed_owned_named_session','initial_row_not_reentered_by_other_join_notifications'):
            report=client();report[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):gate.validate_peer(report)

    def test_error_code_is_the_actual_null_provider_unknown_error(self):
        report=client();report['native_failure_error_id']='AlreadyInSession'
        with self.assertRaises(RuntimeError):gate.validate_peer(report)

    def test_callbacks_replay_and_duplicated_continuation_fail(self):
        for field,value in (('native_callbacks_replayed',True),('duplicate_completion_calls',3)):
            report=client();report[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):gate.validate_peer(report)

    def test_lane_stays_explicit_and_out_of_commandlets(self):
        self.assertIsNone(validation_module([]))
        self.assertEqual(validation_module(['-UEPSessionJoinFailureResult=owned.json']),'uep_lyra_hud.session_join_failure_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPSessionJoinFailureResult=owned.json']))
