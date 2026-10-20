"""Frontend action order, original non-destructive logout and result selection."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

scripts=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'
native=types.ModuleType('unreal_engine');native.find_class=lambda name:name
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda name:None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._frontend_menu_policy_test',scripts/'uep_lyra_hud/frontend_menu_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)

class FrontendMenuPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.focus=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('focus',f,*a)));self.props=dict(StartGameButton=self.focus,OnActivated='native animation');self.w=types.SimpleNamespace(get_property=self.props.get,call_function=self.call);self.sub=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('user',f,*a)));policy.lib=lambda name:types.SimpleNamespace(call_function=lambda f,*a:self.library(name,f,a));policy.ue=native
    def call(self,f,*a):
        self.calls.append(('widget',f,*a))
        if f=='GetDesiredFocusTarget':return self.focus
    def library(self,name,f,a):
        if f=='GetGameInstanceSubsystem':return self.sub
        self.calls.append((name,f,*a))
    def test_const_focus_returns_original_start_button(self):self.assertEqual(policy.invoke(self.w,'focus'),dict(UseOriginal=False,ReturnValue=self.focus))
    def test_activation_animates_before_getting_and_setting_native_focus(self):
        policy.invoke(self.w,'activate');self.assertEqual(self.calls,[('widget','PlayAnimationForward','native animation',1.,False),('widget','GetDesiredFocusTarget'),('focus','SetFocus')])
    def test_four_menu_routes_only_start_original_native_async_nodes(self):
        for action in ('start','options','credits','replays'):
            self.calls=[];policy.invoke(self.w,action);self.assertEqual(self.calls,[('widget',policy.ALIASES[action])])
    def test_quit_and_logout_open_original_native_localized_prompts(self):
        for action in ('quit','logout'):
            self.calls=[];policy.invoke(self.w,action);self.assertEqual(self.calls,[('widget',policy.ALIASES[action])])
    def test_only_confirmed_quit_calls_native_quit_with_original_arguments(self):
        for result in (0,1,2,3,4):
            self.calls=[];policy.invoke(self.w,'quit_result',result);self.assertEqual(self.calls,[('KismetSystemLibrary','QuitGame',self.w,None,0,False)] if result==0 else [])
    def test_only_confirmed_logout_begins_original_native_destroy_session(self):
        for result in (0,1,2,3,4):
            self.calls=[];policy.invoke(self.w,'logout_result',result);self.assertEqual(self.calls,[('widget',policy.ALIASES['destroy_session'])] if result==0 else [])
    def test_logout_success_preserves_player_before_reset_and_startup_push(self):
        policy.invoke(self.w,'logout_success');self.assertEqual(self.calls,[('user','TryToLogOutUser',0,False),('user','ResetUserState'),('widget',policy.ALIASES['startup'])])
    def test_declared_profiles_cover_exact_full_method_set(self):
        for profile in ('Python','BlueprintFallback'):
            cls=getattr(policy,'LyraFrontendMenu'+profile+'Profile');self.assertEqual({getattr(v,'override',None) for v in vars(cls).values() if callable(v)},set(policy.GATES.values()))
    def test_fallback_focus_and_events_request_original_graph_without_side_effects(self):
        cls=policy.LyraFrontendMenuBlueprintFallbackProfile;self.assertEqual(cls.focus(self.w),dict(UseOriginal=True,ReturnValue=None));self.assertTrue(cls.logout_success(self.w));self.assertFalse(self.calls)
