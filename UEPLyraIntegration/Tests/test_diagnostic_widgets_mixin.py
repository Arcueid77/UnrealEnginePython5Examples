"""Native sampling order, numeric scaling and user/controller validity policies."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda o:o is not None
spec=importlib.util.spec_from_file_location('uep_lyra_hud._diagnostic_widgets_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/diagnostic_widgets_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)

class DiagnosticWidgetsPolicyTests(unittest.TestCase):
    def setUp(self):
        policy.ue=native;self.calls=[];self.sample=12.5;self.controller=object();self.user=types.SimpleNamespace(call_function=self.user_call);self.sub=types.SimpleNamespace(call_function=lambda f,n:self.user);self.data=dict(ScaleFactor=1000.,ValuePaddingWidth=73.,PlayerNumber=0,StatValueSizer=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('sizer',f,*a))));self.w=types.SimpleNamespace(get_property=self.data.get,call_function=self.call);policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(n,f,a))
    def call(self,f,*a):
        self.calls.append(('widget',f,*a))
        if f=='FetchStatValue':return self.sample
    def user_call(self,f,*a):
        self.calls.append(('user',f,*a));return '昵称{}' if f=='GetNickname' else 'debug'
    def library(self,n,f,a):
        self.calls.append((n,f,*a))
        if f=='GetPlayerController':return self.controller
        if f=='GetGameInstanceSubsystem':return self.sub
        if f=='GetBuildVersion':return '1.2'
        if f=='GetBuildConfiguration':return 'Development'
    def test_graph_updates_native_graph_before_sampling_then_scales(self):
        policy.invoke(self.w,'graph','tick');self.assertEqual(self.calls,[('widget','UpdateGraphData',1000.),('widget','FetchStatValue'),('widget',policy.NATIVE_VALUE,12500.)])
    def test_text_widget_does_not_update_graph_backend(self):
        policy.invoke(self.w,'text','tick');self.assertEqual(self.calls,[('widget','FetchStatValue'),('widget',policy.NATIVE_VALUE,12500.)])
    def test_numeric_scale_is_raw_without_clamp(self):
        for scale,value,expected in ((0.,1.,0.),(-2.,3.,-6.),(.5,-.25,-.125),(1000.,.001,1.)):
            self.calls=[];self.data['ScaleFactor']=scale;self.sample=value;policy.invoke(self.w,'text','tick');self.assertEqual(self.calls[-1],('widget',policy.NATIVE_VALUE,expected))
    def test_preconstruct_uses_native_label_zero_formatter(self):
        policy.invoke(self.w,'graph','pre');self.assertEqual(self.calls,[('widget',policy.NATIVE_PRE)])
    def test_text_width_is_set_after_native_label_zero_formatter(self):
        policy.invoke(self.w,'text','pre');self.assertEqual(self.calls,[('widget',policy.NATIVE_PRE),('sizer','SetWidthOverride',73.)])
    def test_build_strings_are_forwarded_to_native_localized_formatter(self):
        policy.invoke(self.w,'build','construct');self.assertEqual(self.calls[-1],('widget',policy.NATIVE_BUILD,'1.2','Development'))
    def test_missing_controller_does_not_query_user_subsystem(self):
        self.controller=None;policy.invoke(self.w,'watermark','tick');self.assertEqual(self.calls[-1],('widget',policy.NATIVE_MISSING,1));self.assertFalse(any(c[1]=='GetGameInstanceSubsystem' for c in self.calls))
    def test_missing_user_selects_original_native_localized_status(self):
        self.user=None;policy.invoke(self.w,'watermark','tick');self.assertEqual(self.calls[-1],('widget',policy.NATIVE_MISSING,1))
    def test_valid_user_preserves_game_context_and_both_native_strings(self):
        policy.invoke(self.w,'watermark','tick');self.assertEqual(self.calls[-3:],[('user','GetNickname',0),('user','GetDebugString'),('widget',policy.NATIVE_USER,'昵称{}','debug',1)])
    def test_player_index_is_passed_to_both_native_lookups(self):
        self.data['PlayerNumber']=3;policy.invoke(self.w,'watermark','tick');self.assertEqual(self.calls[0],('GameplayStatics','GetPlayerController',self.w,3));self.assertEqual(self.calls[-1][-1],4)
    def test_display_number_retains_source_int32_add_wrap(self):
        for value,expected in ((-1,0),(0,1),(3,4),(2147483647,-2147483648),(-2147483648,-2147483647)):self.assertEqual(policy.display_player_number(value),expected)
    def test_profiles_route_only_declared_refresh_and_preconstruct_methods(self):
        for k,methods in policy.METHODS.items():
            for p in ('Python','BlueprintFallback'):
                cls=getattr(policy,'LyraDiagnostic'+k.title()+p+'Profile');self.assertEqual({v.override for v in vars(cls).values() if callable(v) and hasattr(v,'override')},set(policy.GATES[k].values()))
