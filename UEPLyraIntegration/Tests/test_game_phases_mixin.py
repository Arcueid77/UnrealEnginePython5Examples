"""Native conversion semantics, invocation locals and original phase ordering."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.FLinearColor=lambda *a:a;native.find_class=lambda n:n;native.load_class=lambda p:p
libraries=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libraries.lib=lambda n:None
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._phase_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/game_phases_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libraries}):spec.loader.exec_module(policy)


def int32(v):return (int(v)+2**31)%2**32-2**31


class PhasePolicyTests(unittest.TestCase):
    def setUp(self):
        self.data=dict(WaitForPlayersDuration=30.,CountdownDuration=3,CountdownSecsRemaining=2);self.calls=[];self.skip=False;self.system=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('global',f,*a)));self.a=types.SimpleNamespace(get_property=self.data.get,set_property=self.set_property,call_function=self.call);policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(n,f,a))
    def set_property(self,name,value):
        if name not in self.data:raise AssertionError('Original function locals must not become ability properties')
        self.data[name]=value
    def call(self,f,*args):
        self.calls.append(('ability',f,*args))
        if f=='SanitizeDurations':policy.sanitize(self.a)
    def library(self,n,f,a):
        if f=='GetWorldSubsystem':return self.system
        if f=='ShouldSkipDirectlyToGameplay':return self.skip
        if f=='FMax':return max(a)
        if f=='Conv_DoubleToInt64':return int(a[0])
        if f=='Conv_Int64ToInt':return int32(a[0])
        if f=='Subtract_IntInt':return int32(a[0]-a[1])
        self.calls.append((n,f,*a))
    def test_valid_durations_do_not_print(self):
        policy.sanitize(self.a);self.assertFalse(self.calls);self.assertEqual(self.data['CountdownDuration'],3)
    def test_negative_durations_clamp_then_bound_countdown(self):
        self.data.update(WaitForPlayersDuration=-2.5,CountdownDuration=-3);policy.sanitize(self.a);self.assertEqual((self.data['WaitForPlayersDuration'],self.data['CountdownDuration']),(0.,0));self.assertEqual(self.calls[0][1],'PrintString')
    def test_fractional_wait_truncates_for_integer_countdown_limit(self):
        self.data.update(WaitForPlayersDuration=2.75,CountdownDuration=8);policy.sanitize(self.a);self.assertEqual(self.data['CountdownDuration'],2)
    def test_native_int64_to_int32_wrap_is_not_replaced_by_python_clamping(self):
        self.data.update(WaitForPlayersDuration=2147483648.,CountdownDuration=2);policy.sanitize(self.a);self.assertEqual(self.data['CountdownDuration'],-2147483648)
    def test_sanitize_original_values_stay_function_local(self):
        policy.sanitize(self.a);self.assertEqual(set(self.data),{'WaitForPlayersDuration','CountdownDuration','CountdownSecsRemaining'})
    def test_development_skip_starts_playing_without_lobby_or_wait(self):
        self.skip=True;policy.warmup(self.a);self.assertEqual(self.calls,[('ability',policy.BACKENDS['playing'])])
    def test_warmup_sanitizes_applies_lobby_then_enters_original_delay(self):
        policy.warmup(self.a);self.assertEqual(self.calls,[('ability','SanitizeDurations'),('global','ApplyEffectToAll',policy.LOBBY),('ability',policy.BACKENDS['wait'])])
    def test_zero_countdown_is_still_emitted(self):
        self.data['CountdownSecsRemaining']=1;policy.step(self.a);self.assertEqual(self.data['CountdownSecsRemaining'],0);self.assertEqual(self.calls,[('ability',policy.BACKENDS['emit'])])
    def test_negative_countdown_removes_lobby_before_playing(self):
        self.data['CountdownSecsRemaining']=0;policy.step(self.a);self.assertEqual(self.calls,[('global','RemoveEffectFromAll',policy.LOBBY),('ability',policy.BACKENDS['playing'])])
    def test_countdown_initialization_uses_configured_count(self):
        self.data['CountdownDuration']=3;policy.ready(self.a);self.assertEqual(self.data['CountdownSecsRemaining'],3);self.assertEqual(self.calls,[('ability',policy.BACKENDS['emit'])])
    def test_postgame_immunity_precedes_original_wait(self):
        policy.postgame(self.a);self.assertEqual(self.calls,[('global','ApplyEffectToAll',policy.IMMUNITY),('ability',policy.BACKENDS['postwait'])])
    def test_input_block_precedes_original_next_tick_wait(self):
        policy.block(self.a);self.assertEqual(self.calls,[('global','ApplyEffectToAll',policy.BLOCK),('ability',policy.BACKENDS['nexttick'])])
    def test_restart_uses_native_server_travel_api(self):
        policy.restart(self.a);self.assertEqual(self.calls,[('LyraSystemStatics','PlayNextGame',self.a)])
