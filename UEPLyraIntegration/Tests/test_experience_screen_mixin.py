"""Original async continuation ordering, browse failure behavior and request mode."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');native.find_class=lambda name:name
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda name:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location('_experience_screen_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/experience_screen_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class ExperienceScreenPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.exp=object();self.request=object();self.props=dict(QuickplayButton=object(),OnActivated='intro',SelectedExperience=self.exp);self.spinner=types.SimpleNamespace(call_function=lambda fn,*args:self.calls.append(('spinner',fn,*args)));self.list=types.SimpleNamespace(call_function=self.list_call);self.props.update(ProgressSpinner=self.spinner,W_ExperienceList=self.list);self.w=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call);self.sub=types.SimpleNamespace(call_function=lambda fn,*args:self.calls.append(('session',fn,*args)));policy.lib=lambda name:types.SimpleNamespace(call_function=lambda fn,*args:self.sub);policy.ue=native;self.clear_selection=False
    def set(self,name,value):self.props[name]=value;self.calls.append(('set',name,value))
    def call(self,name,*args):
        if name=='GetOwningPlayer':return 'controller'
        self.calls.append(('widget',name,*args))
        if name==policy.NATIVE['request']:return self.request
    def list_call(self,name,*args):
        self.calls.append(('list',name,*args))
        if self.clear_selection:self.props['SelectedExperience']=None
    def test_focus_returns_exact_quickplay_button(self):self.assertEqual(policy.invoke(self.w,'focus'),dict(UseOriginal=False,ReturnValue=self.props['QuickplayButton']))
    def test_activation_animates_before_hiding_spinner(self):
        policy.invoke(self.w,'activate');self.assertEqual(self.calls,[('widget','PlayAnimationForward','intro',1.,False),('widget','ShowProgressSpinner',False)])
    def test_spinner_uses_visible_or_hidden_not_collapsed(self):
        for enabled,value in ((True,0),(False,2)):
            self.calls=[];policy.invoke(self.w,'spinner',enabled);self.assertEqual(self.calls,[('spinner','SetVisibility',value)])
    def test_selection_stores_exact_definition(self):
        policy.invoke(self.w,'selected',None);self.assertEqual(self.calls,[('set','SelectedExperience',None)])
    def test_clicks_start_only_their_original_native_async_actions(self):
        for action in ('host','browse','quick'):
            self.calls=[];policy.invoke(self.w,action);self.assertEqual(self.calls,[('widget',policy.NATIVE[action])])
    def test_browse_success_and_failure_both_open_original_browser(self):
        for success in (False,True):
            self.calls=[];policy.invoke(self.w,'browse_result',success);self.assertEqual(self.calls,[('widget',policy.NATIVE['browser'])])
    def test_failed_quickplay_initialization_does_nothing(self):policy.invoke(self.w,'quick_result',False);self.assertFalse(self.calls)
    def test_quick_success_selects_before_validation_and_starts_only_preparation(self):
        policy.invoke(self.w,'quick_result',True);self.assertEqual(self.calls,[('list','SelectRandomExperience'),('widget',policy.NATIVE['prepare'])])
    def test_null_selection_after_random_skips_preparation(self):
        self.clear_selection=True;policy.invoke(self.w,'quick_result',True);self.assertEqual(self.calls,[('list','SelectRandomExperience')])
    def test_only_native_preparation_completion_builds_online_request_submits_then_shows_spinner(self):
        policy.invoke(self.w,'prepared');self.assertEqual(self.calls,[('widget',policy.NATIVE['request'],self.exp),('session','QuickPlaySession','controller',self.request),('widget','ShowProgressSpinner',True)])
    def test_prepared_continuation_reads_latest_selected_definition(self):
        replacement=object();self.props['SelectedExperience']=replacement;policy.invoke(self.w,'prepared');self.assertIs(self.calls[0][2],replacement)
    def test_profiles_have_exact_own_routing_methods(self):
        for profile in ('Python','BlueprintFallback'):
            cls=getattr(policy,'LyraExperienceScreen'+profile+'Profile');self.assertEqual({fn.override for fn in vars(cls).values() if callable(fn)},set(policy.GATES.values()))
