"""Source UI sequence and opaque native lock/search boundaries."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda name:None
spec=importlib.util.spec_from_file_location('_session_browser_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/session_browser_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)
class SessionBrowserPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.results=[];self.list=types.SimpleNamespace(call_function=lambda fn,*args:self.calls.append(('list',fn,*args)));self.border=types.SimpleNamespace(call_function=lambda fn,*args:self.calls.append(('border',fn,*args)));self.props=dict(LyraListView=self.list,NoGamesBorder=self.border,SearchRequest=types.SimpleNamespace(get_property=lambda n:self.results),OnActivated_0='activate',ProgressSpinnerIntro='intro',ProgressSpinnerOutro='outro');self.w=types.SimpleNamespace(get_property=self.props.get,call_function=self.call)
    def call(self,fn,*args):
        self.calls.append(('widget',fn,*args))
        if fn=='GetOwningPlayer':return ('owner',)
    def test_const_focus_returns_original_list(self):self.assertEqual(policy.invoke(self.w,'focus'),dict(UseOriginal=False,ReturnValue=self.list))
    def test_activation_animates_before_starting_original_lock(self):policy.invoke(self.w,'activate');self.assertEqual(self.calls,[('widget','PlayAnimationForward','activate',1.,False),('widget','StartSearch')])
    def test_refresh_uses_original_start_search(self):policy.invoke(self.w,'refresh');self.assertEqual(self.calls,[('widget','StartSearch')])
    def test_search_clears_list_hides_empty_state_then_restarts_spinner_before_native_submit(self):
        policy.invoke(self.w,'search');self.assertEqual(self.calls,[('list','ClearListItems'),('border','SetVisibility',1),('widget','IsAnimationPlayingForward','outro'),('widget','StopAnimation','outro'),('widget','PlayAnimationForward','intro',1.,False),('widget',policy.NATIVE['submit'])])
    def test_unlock_resets_original_do_once_before_spinner_outro(self):
        policy.invoke(self.w,'unlock');self.assertEqual(self.calls,[('widget',policy.NATIVE['reset']),('widget','IsAnimationPlayingForward','intro'),('widget','StopAnimation','intro'),('widget','PlayAnimationForward','outro',1.,False)])
    def test_empty_results_use_original_hit_test_invisible_value(self):policy.invoke(self.w,'results');self.assertEqual(self.calls[0],('border','SetVisibility',3))
    def test_nonempty_results_collapse_empty_state_and_preserve_result_identity(self):
        result=object();self.results=[result];policy.invoke(self.w,'results');self.assertEqual(self.calls[:2],[('border','SetVisibility',1),('list','BP_SetListItems',[result])])
    def test_results_focus_self_then_list_before_unlock(self):policy.invoke(self.w,'results');self.assertEqual(self.calls[-4:],[('widget','GetOwningPlayer'),('widget','SetUserFocus','owner'),('list','SetUserFocus','owner'),('widget','UnlockAfterSearchFinish')])
    def test_results_re_read_current_request_on_each_native_completion(self):
        policy.invoke(self.w,'results');self.results=[object()];policy.invoke(self.w,'results');self.assertEqual([v[2] for v in self.calls if v[:2]==('border','SetVisibility')],[3,1])
    def test_both_profiles_have_exact_gates_and_no_ftext_parameter(self):
        for p in ('Python','BlueprintFallback'):
            cls=getattr(policy,'LyraSessionBrowser'+p+'Profile');self.assertEqual({f.override for f in vars(cls).values() if callable(f)},set(policy.GATES.values()));self.assertNotIn('OnSearchFinished',vars(cls))
    def test_fallback_retains_native_do_once_and_original_search(self):
        result=policy.LyraSessionBrowserBlueprintFallbackProfile.search(self.w);self.assertTrue(result);self.assertEqual(policy.evidence(self.w)['fallback_search'],1);self.assertFalse(self.calls)
    def test_python_returns_false_after_submit(self):self.assertFalse(policy.LyraSessionBrowserPythonProfile.search(self.w));self.assertEqual(policy.evidence(self.w)['python_search'],1)
