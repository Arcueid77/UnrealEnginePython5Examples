"""Original replay query UI state and result identity/order."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda name:None
spec=importlib.util.spec_from_file_location('_replay_browser_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/replay_browser_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)
class ReplayBrowserPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.props=dict(RefreshButton='refresh',ProgressSpinner=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('spinner',f,*a))),ReplayListWidget=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('list',f,*a))));self.w=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=lambda f,*a:self.calls.append(('widget',f,*a)))
    def set(self,name,value):self.props[name]=value;self.calls.append(('set',name,value))
    def test_const_focus_is_refresh_button(self):self.assertEqual(policy.invoke(self.w,'focus'),dict(UseOriginal=False,ReturnValue='refresh'))
    def test_activation_and_refresh_call_original_start_search(self):
        for key in ('activate','refresh'):policy.invoke(self.w,key)
        self.assertEqual(self.calls,[('widget','StartSearch'),('widget','StartSearch')])
    def test_search_shows_spinner_without_clearing_previous_results(self):policy.invoke(self.w,'search');self.assertEqual(self.calls,[('spinner','SetVisibility',0),('widget',policy.NATIVE['query'])])
    def test_unlock_resets_native_do_once_before_collapsing_spinner(self):policy.invoke(self.w,'unlock');self.assertEqual(self.calls,[('widget',policy.NATIVE['reset']),('spinner','SetVisibility',1)])
    def test_result_object_is_stored_before_native_order_is_assigned(self):
        items=[object(),object()];result=types.SimpleNamespace(get_property=lambda n:items);policy.invoke(self.w,'results',result);self.assertEqual(self.calls,[('set','ResultList',result),('list','BP_SetListItems',items),('widget','UnlockAfterSearchFinish')]);self.assertIs(self.calls[1][2][0],items[0])
    def test_empty_results_still_replace_list_and_unlock(self):
        policy.invoke(self.w,'results',types.SimpleNamespace(get_property=lambda n:[]));self.assertEqual(self.calls[-2:],[('list','BP_SetListItems',[]),('widget','UnlockAfterSearchFinish')])
    def test_profiles_own_complete_gates(self):
        for p in ('Python','BlueprintFallback'):
            cls=getattr(policy,'LyraReplayBrowser'+p+'Profile');self.assertEqual({f.override for f in vars(cls).values() if callable(f)},set(policy.GATES.values()))
