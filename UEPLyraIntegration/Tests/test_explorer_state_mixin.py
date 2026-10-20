"""Preserve StateTree source completion semantics, including the asymmetric flag."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');native.find_struct=lambda n:lambda **v:v
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
spec=importlib.util.spec_from_file_location('_explorer_state_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/explorer_state_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs}):spec.loader.exec_module(policy)

class ExplorerStatePolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.props=dict(Delay=.75,DelayInProgress=False,PlayerPosition='old',PlayerLocation='old')
        self.obj=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call)
        policy.ue=native;policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(f,*a))
    def set(self,k,v):self.props[k]=v;self.calls.append(('set',k,v))
    def call(self,f,*a):self.calls.append((f,*a));return 'native-player-zero-location'
    def library(self,f,*a):self.calls.append((f,*a));return '.75' if f=='Conv_DoubleToString' else None
    def test_position_getter_is_native_and_re_evaluated_on_each_tick(self):
        for kind,prop in (('eval','PlayerPosition'),('location','PlayerLocation')):
            self.obj=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call)
            policy.invoke(self.obj,kind,'tick',.2);self.assertEqual(self.props[prop],'native-player-zero-location')
    def test_native_move_is_started_without_caching_goal_or_ai_result(self):
        for kind in ('follow','goto'):
            self.calls.clear();self.obj=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call)
            policy.invoke(self.obj,kind,'enter',object());self.assertEqual(self.calls,[(policy.NATIVE[kind]['move'],)])
    def test_move_finished_always_succeeds_even_for_non_success_move_result(self):
        for kind in ('follow','goto'):
            self.obj=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call)
            policy.invoke(self.obj,kind,'success',object(),5);self.assertEqual(self.calls[-1],('FinishTask',True))
    def test_request_failed_finishes_false(self):
        for kind in ('follow','goto'):
            self.obj=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call)
            policy.invoke(self.obj,kind,'failed');self.assertEqual(self.calls[-1],('FinishTask',False))
    def test_enter_sets_flag_and_starts_original_enter_delay_without_finish(self):
        policy.invoke(self.obj,'delay','enter',object());self.assertTrue(self.props['DelayInProgress']);self.assertEqual(self.calls[-1],(policy.NATIVE['delay']['enter_delay'],));self.assertFalse(any(c[0]=='FinishTask' for c in self.calls));self.assertTrue(any(c[0]=='PrintString' and c[2]=='Wait for .75 Seconds In State EnterState' for c in self.calls))
    def test_ticks_during_enter_delay_do_not_start_tick_delay(self):
        self.props['DelayInProgress']=True;policy.invoke(self.obj,'delay','tick',.2);self.assertEqual(self.calls,[])
    def test_enter_completion_clears_flag_without_finishing_task(self):
        self.props['DelayInProgress']=True;policy.invoke(self.obj,'delay','enter_done');self.assertFalse(self.props['DelayInProgress']);self.assertFalse(any(c[0]=='FinishTask' for c in self.calls))
    def test_tick_reentry_starts_only_one_native_tick_delay(self):
        policy.invoke(self.obj,'delay','tick',.1);policy.invoke(self.obj,'delay','tick',.1);self.assertEqual(sum(c[0]==policy.NATIVE['delay']['tick_delay'] for c in self.calls),1)
    def test_tick_completion_finishes_true_and_retains_flag(self):
        self.props['DelayInProgress']=True;policy.invoke(self.obj,'delay','tick_done');self.assertTrue(self.props['DelayInProgress']);self.assertEqual(self.calls[-1],('FinishTask',True))
    def test_complete_own_class_profile_methods_and_fallback_passthrough(self):
        for kind,methods in policy.METHODS.items():
            self.obj=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call)
            cls=getattr(policy,'LyraExplorerState'+kind.title()+'BlueprintFallbackProfile')
            self.assertEqual({m for m,f in vars(cls).items() if callable(f) and hasattr(f,'override')},set(methods))
            for m in methods:self.assertTrue(vars(cls)[m](self.obj))
        self.assertEqual(self.calls,[])
