from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.ui_regression_suite_contract import SCENARIOS,defer_finish_exit,validate
from uep_lyra_hud.startup import validation_module


class Engine:
    def __init__(self):self.real_exits=0;self.messages=[]
    def request_exit(self):self.real_exits+=1
    def log(self,message):self.messages.append(message)


ue=Engine()


class Scenario:
    def __init__(self):self.finished=False;self.cleanup_calls=0
    def cleanup(self):self.cleanup_calls+=1
    def finish(self,error=None):
        if self.finished:return
        self.finished=True;self.cleanup();self.error=error;ue.log('original finish');ue.request_exit()


class UIRegressionSuiteTests(unittest.TestCase):
    def test_original_cleanup_bytecode_and_logs_run_without_global_exit_patch(self):
        global ue
        ue=Engine();deferred=[];original=Scenario.finish;original_globals=original.__globals__['ue']
        wrapped=defer_finish_exit(original,lambda:deferred.append(True));cls=type('Combined',(Scenario,),dict(finish=wrapped));case=cls();case.finish()
        self.assertIs(wrapped.__code__,original.__code__)
        self.assertIs(original.__globals__['ue'],original_globals)
        self.assertEqual(case.cleanup_calls,1);self.assertEqual(ue.messages,['original finish']);self.assertEqual(deferred,[True]);self.assertEqual(ue.real_exits,0)
        ue.request_exit();self.assertEqual(ue.real_exits,1)

    def test_repeated_finish_keeps_original_once_only_guard(self):
        deferred=[];cls=type('Combined',(Scenario,),dict(finish=defer_finish_exit(Scenario.finish,lambda:deferred.append(True))))
        case=cls();case.finish('original failure');case.finish();self.assertEqual(case.error,'original failure');self.assertEqual(case.cleanup_calls,1);self.assertEqual(len(deferred),1)

    def test_missing_scenarios_do_not_pass_a_combined_gate(self):
        with self.assertRaises(RuntimeError):validate(dict(status='passed',error=None,cases=[]),'.')

    def test_suite_is_an_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPUIRegressionSuiteResult=owned.json']),'uep_lyra_hud.ui_regression_suite_validation')
        self.assertIsNone(validation_module([]));self.assertIsNone(validation_module(['-run=Py','-UEPUIRegressionSuiteResult=owned.json']))

    def test_original_module_has_ten_distinct_required_groups(self):
        self.assertEqual(len(SCENARIOS),10);self.assertEqual(len({name for name,_ in SCENARIOS}),10)

    def test_audio_scenarios_keep_their_native_offline_renderer_prerequisite(self):
        driver=Path(__file__).resolve().parents[3]/'Validation/Run-UEP58UIRegressionSuite.ps1'
        if not driver.exists():self.skipTest('Core validation driver is outside this standalone Examples checkout')
        source=driver.read_text(encoding='utf-8-sig')
        self.assertIn("'-DeterministicAudio'",source);self.assertNotIn("'-NoSound'",source)
        self.assertIn('Using Audio Hardware Device Non-realtime Renderer',source)
