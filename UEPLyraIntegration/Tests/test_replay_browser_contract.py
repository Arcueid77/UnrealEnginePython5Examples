"""Reject incomplete real recording/query/dialog/current-item playback proof."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.replay_browser_contract import TRUE_FIELDS,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,profile='Python',actual_query_completions=2,recording_count=2,native_result_count=2,native_dialog_results=[1,0],played_replay_name='first',recorded_replay_names=['first','second'],native_playback_seconds=1.,direct_interface_inputs=['null','wrong replay-list object','retarget to older real replay during confirmation']);r.update(dict.fromkeys(TRUE_FIELDS,True));r.update(dict.fromkeys(FALSE_FIELDS,False));return r
class ReplayBrowserContractTests(unittest.TestCase):
    def test_complete_native_lifecycle(self):self.assertEqual(validate(report())['real_recordings'],2)
    def test_missing_native_observation_rejected(self):
        for field in TRUE_FIELDS:
            r=report();r[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_scope_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_missing_real_record_query_or_dialog_rejected(self):
        for field,value in (('recording_count',1),('actual_query_completions',1),('native_result_count',0),('native_dialog_results',[0])):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_confirmed_must_play_current_retargeted_older_item(self):
        r=report();r['played_replay_name']='second'
        with self.assertRaises(RuntimeError):validate(r)
    def test_missing_clock_or_disclosed_direct_inputs_rejected(self):
        for field,value in (('native_playback_seconds',0.),('direct_interface_inputs',[])):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate(r)
