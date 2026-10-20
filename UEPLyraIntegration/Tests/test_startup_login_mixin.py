"""Exact startup ordering, local-controller state, native opaque IO boundaries."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');native.find_class=lambda name:name
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda name:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._startup_login_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/startup_login_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class StartupLoginPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.props=dict(PressStartButton='press',bWaitingForPlayerInitialize=True,PlayerNumber=1);self.button=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('button',f,*a)));self.props['LoginButton']=self.button;self.w=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call);self.sub=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('user',f,*a)));self.controllers={0:'primary',1:'secondary'};self.logged=True;policy.ue=native;policy.lib=lambda name:types.SimpleNamespace(call_function=lambda f,*a:self.library(name,f,a))
    def set(self,k,v):self.props[k]=v;self.calls.append(('set',k,v))
    def call(self,f,*a):
        if f=='IsPlayerLoggedIn':return self.logged
        self.calls.append(('widget',f,*a))
    def library(self,name,f,a):
        if f=='GetGameInstanceSubsystem':return self.sub
        if f=='GetPlayerController':return self.controllers.get(a[1])
        self.calls.append((name,f,*a))
    def test_startup_focus_is_original_press_start_button(self):self.assertEqual(policy.invoke(self.w,'startup','focus'),dict(UseOriginal=False,ReturnValue='press'))
    def test_press_start_listens_before_setting_waiting_for_initialize(self):
        policy.invoke(self.w,'startup','press_start');self.assertEqual(self.calls,[('widget','SetListenForLoginInput',True),('set','bWaitingForPlayerInitialize',True)])
    def test_full_menu_deactivates_before_stopping_login_input(self):
        policy.invoke(self.w,'startup','full_menu');self.assertEqual(self.calls,[('widget','DeactivateWidget'),('widget','SetListenForLoginInput',False)])
    def test_initialize_requires_both_success_and_current_waiting_flag(self):
        for success in (False,True):
            for waiting in (False,True):
                self.calls=[];self.props['bWaitingForPlayerInitialize']=waiting;policy.invoke(self.w,'startup','initialized',success);self.assertEqual(self.calls,[('set','bWaitingForPlayerInitialize',False),('widget','SwitchToFullMenu')] if success and waiting else [])
    def test_startup_click_disables_input_before_native_initialization(self):
        policy.invoke(self.w,'startup','click');self.assertEqual(self.calls,[('widget','SetListenForLoginInput',False),('widget',policy.ALIASES['startup']['initialize'])])
    def test_both_listeners_set_the_flag_and_select_original_opaque_key_adapter(self):
        for k,field in (('startup','bWaitingForLoginInput'),('login','WaitingForLoginInput')):
            for enabled in (False,True):
                self.calls=[];policy.invoke(self.w,k,'listen',enabled);self.assertEqual(self.calls,[('set',field,enabled),('widget',policy.ALIASES[k]['listen_on' if enabled else 'listen_off'])])
    def test_logged_in_uses_local_controller_validity_and_handles_missing_index(self):
        for index,exists in ((0,True),(1,True),(9,False),(-1,False)):
            self.props['PlayerNumber']=index;self.assertEqual(policy.invoke(self.w,'login','logged_in'),dict(UseOriginal=False,ReturnValue=exists))
    def test_refresh_existing_controller_assigns_owner_then_native_text_then_listen_off(self):
        self.logged=(True,);policy.invoke(self.w,'login','refresh');self.assertEqual(self.calls,[('button','SetOwningPlayer','secondary'),('widget',policy.ALIASES['login']['text_in']),('widget','SetListenForLoginInput',False)])
    def test_refresh_tuple_false_uses_primary_owner_then_join_text_then_listen_on(self):
        self.logged=(False,);policy.invoke(self.w,'login','refresh');self.assertEqual(self.calls,[('button','SetOwningPlayer','primary'),('widget',policy.ALIASES['login']['text_out']),('widget','SetListenForLoginInput',True)])
    def test_login_initialized_ignores_result_payload_and_always_refreshes(self):
        policy.invoke(self.w,'login','initialized');self.assertEqual(self.calls,[('widget','RefreshLoginState')])
    def test_existing_secondary_click_logs_out_with_destroy_true_then_refreshes(self):
        policy.invoke(self.w,'login','click');self.assertEqual(self.calls,[('user','TryToLogOutUser',1,True),('widget','RefreshLoginState')])
    def test_missing_secondary_click_only_starts_original_native_initialize(self):
        self.logged=(False,);policy.invoke(self.w,'login','click');self.assertEqual(self.calls,[('widget',policy.ALIASES['login']['initialize'])])
    def test_construct_keeps_original_native_binding_and_following_transition(self):
        for k in ('startup','login'):
            self.calls=[];policy.invoke(self.w,k,'construct');self.assertEqual(self.calls,[('widget',policy.ALIASES[k]['bind'])])
    def test_destruct_stops_input_only_when_native_subsystem_exists(self):
        policy.invoke(self.w,'login','destruct');self.assertEqual(self.calls,[('widget','SetListenForLoginInput',False)]);self.sub=None;self.calls=[];policy.invoke(self.w,'login','destruct');self.assertFalse(self.calls)
    def test_profiles_cover_exact_method_sets_without_relying_on_python_inheritance(self):
        for k in policy.CLASSES:
            for profile in ('Python','BlueprintFallback'):
                cls=getattr(policy,'LyraStartupLogin'+k.title()+profile+'Profile');self.assertEqual({v.override for v in vars(cls).values() if callable(v)},set(policy.GATES[k].values()))
