"""Only the exact native permission-loss message in both owned windows is expected."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.frontend_logout_log_contract import audit,PROFILES

LINE='[2026.10.20-12.16.13:655][314]LogCommonGame: Error: HandlePrivilegeChanged: Player 0 no longer has permission to play the game!'
def log():return '\n'.join('UEP_IDENTITY_LOGOUT_BEGIN '+p+'\n'+LINE+'\nUEP_IDENTITY_LOGOUT_END '+p for p in PROFILES)

class FrontendLogoutLogTests(unittest.TestCase):
    def test_exact_expected_native_errors_are_audited_without_modifying_raw(self):
        raw=log();clean,r=audit(raw);self.assertEqual(r['expected_native_permission_loss_errors'],2);self.assertFalse(r['raw_log_modified']);self.assertFalse(r['other_native_errors_allowed']);self.assertNotIn('Error:',clean);self.assertEqual(raw.count(LINE),2)
    def test_same_message_outside_owned_windows_is_rejected(self):
        with self.assertRaises(RuntimeError):audit(log()+'\n'+LINE)
    def test_extra_unexpected_native_error_is_rejected(self):
        with self.assertRaises(RuntimeError):audit(log()+'\nLogPython: Error: unexpected')
    def test_different_player_is_rejected(self):
        with self.assertRaises(RuntimeError):audit(log().replace('Player 0','Player 1',1))
    def test_duplicate_native_error_within_one_window_is_rejected(self):
        with self.assertRaises(RuntimeError):audit(log().replace(LINE,LINE+'\n'+LINE,1))
    def test_missing_or_duplicate_ownership_markers_are_rejected(self):
        for raw in (log().replace('UEP_IDENTITY_LOGOUT_END Python','missing'),log()+'\nUEP_IDENTITY_LOGOUT_BEGIN Python'):
            with self.assertRaises(RuntimeError):audit(raw)
