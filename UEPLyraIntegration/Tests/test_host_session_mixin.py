"""Host mode/bot choices, request overrides and native callback continuation order."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda name:None;validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location('_host_session_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/host_session_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class HostSessionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.request_props=dict(ExtraArgs={'Experience':'mode','NumBots':'7','Other':'keep'});self.request=types.SimpleNamespace(set_property=self.request_set,get_property=self.request_props.get);self.exp=types.SimpleNamespace(call_function=lambda fn,*args:self.create(fn,args));self.props={'Online Mode':2,'BotsEnabled':True,'SelectedExperience':self.exp,'BotsToggleButton':'bots button','OnActivated':'intro'};self.w=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call)
    def create(self,name,args):self.calls.append(('definition',name,*args));return self.request
    def request_set(self,name,value):self.request_props[name]=value;self.calls.append(('request',name,value))
    def set(self,name,value):self.props[name]=value;self.calls.append(('set',name,value))
    def call(self,name,*args):
        self.calls.append(('widget',name,*args))
        if name=='CreateHostingRequest':return (self.request,)
    def test_focus_returns_exact_bot_toggle(self):self.assertEqual(policy.invoke(self.w,'focus'),dict(UseOriginal=False,ReturnValue='bots button'))
    def test_activation_updates_labels_before_animation(self):
        policy.invoke(self.w,'activate');self.assertEqual(self.calls,[('widget','UpdateOnlineModeText'),('widget','UpdateBotsEnabledText'),('widget','PlayAnimationForward','intro',1.,False)])
    def test_mode_cycle_is_online_lan_offline_online(self):
        modes=[]
        for _ in range(3):policy.invoke(self.w,'mode_cycle');modes.append(self.props['Online Mode'])
        self.assertEqual(modes,[1,0,2])
    def test_bot_toggle_updates_native_label_after_value(self):
        policy.invoke(self.w,'bots_toggle');self.assertEqual(self.calls,[('set','BotsEnabled',False),('widget','UpdateBotsEnabledText')])
    def test_mode_label_stays_native_opaque_text(self):
        policy.invoke(self.w,'mode_text');self.assertEqual(self.calls,[('widget',policy.NATIVE['mode_text'])])
    def test_bot_labels_select_original_native_text_writers(self):
        for enabled,key in ((True,'bots_on'),(False,'bots_off')):
            self.props['BotsEnabled']=enabled;self.calls=[];policy.invoke(self.w,'bots_text');self.assertEqual(self.calls,[('widget',policy.NATIVE[key])])
    def test_null_definition_returns_null_request_without_constructor(self):
        self.props['SelectedExperience']=None;self.assertEqual(policy.invoke(self.w,'request'),dict(UseOriginal=False,ReturnValue=None));self.assertFalse(self.calls)
    def test_request_preserves_all_modes_and_existing_args_when_bots_enabled(self):
        for mode in (0,1,2):
            self.props['Online Mode']=mode;result=policy.invoke(self.w,'request');self.assertIs(result['ReturnValue'],self.request);self.assertEqual(self.request_props['OnlineMode'],mode);self.assertEqual(self.request_props['ExtraArgs']['NumBots'],'7')
    def test_disabled_bots_only_override_num_bots_zero(self):
        self.props['BotsEnabled']=False;policy.invoke(self.w,'request');self.assertEqual(self.request_props['ExtraArgs'],{'Experience':'mode','NumBots':'0','Other':'keep'})
    def test_null_selection_does_not_initialize_or_push(self):
        policy.invoke(self.w,'selected',None);self.assertEqual(self.calls,[('set','SelectedExperience',None)])
    def test_online_selection_initializes_but_offline_and_lan_push_spinner(self):
        for mode,key in ((0,'spinner'),(1,'spinner'),(2,'login')):
            self.props['Online Mode']=mode;self.calls=[];policy.invoke(self.w,'selected',self.exp);self.assertEqual(self.calls,[('set','SelectedExperience',self.exp),('widget',policy.NATIVE[key])])
    def test_failed_online_initialize_does_not_push_spinner(self):
        policy.invoke(self.w,'online_result',False);self.assertFalse(self.calls);policy.invoke(self.w,'online_result',True);self.assertEqual(self.calls,[('widget',policy.NATIVE['spinner'])])
    def test_spinner_afterpush_stores_widget_before_starting_async_prepare(self):
        widget=object();policy.invoke(self.w,'spinner_pushed',widget);self.assertEqual(self.calls,[('set','SpinnerWidget',widget),('widget',policy.NATIVE['prepare'])])
    def test_prepared_builds_request_then_submits_and_normalizes_bp_out_tuple(self):
        policy.invoke(self.w,'prepared');self.assertEqual(self.calls,[('widget','CreateHostingRequest'),('widget',policy.NATIVE['submit'],self.request)])
    def test_completion_success_is_noop_failure_uses_original_native_error_chain(self):
        policy.invoke(self.w,'completed',True);self.assertFalse(self.calls);policy.invoke(self.w,'completed',False);self.assertEqual(self.calls,[('widget',policy.NATIVE['failure'])])
    def test_profiles_have_exact_own_methods(self):
        for profile in ('Python','BlueprintFallback'):
            cls=getattr(policy,'LyraHostSession'+profile+'Profile');self.assertEqual({fn.override for fn in vars(cls).values() if callable(fn)},set(policy.GATES.values()))
