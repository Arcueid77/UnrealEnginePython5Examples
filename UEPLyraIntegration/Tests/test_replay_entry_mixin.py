"""Confirmed-only playback reads the current item after the native dialog."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location('_replay_entry_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/replay_entry_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)
class ReplayEntryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.current=object();self.w=types.SimpleNamespace(get_property=lambda n:self.current,call_function=lambda f,*a:self.calls.append(('widget',f,*a)));self.sub=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('sub',f,*a)));policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.getsub(n,f,a));policy.ue=native
    def getsub(self,n,f,args):self.calls.append((n,f,*args));return self.sub
    def test_null_and_wrong_item_do_not_replace_existing_text_or_item(self):policy.invoke(self.w,'item',None);policy.invoke(self.w,'item',types.SimpleNamespace(is_a=lambda cls:False));self.assertFalse(self.calls)
    def test_valid_item_uses_typed_native_storage_and_localized_format(self):
        item=types.SimpleNamespace(is_a=lambda cls:cls=='LyraReplayListEntry');policy.invoke(self.w,'item',item);self.assertEqual(self.calls,[('widget',policy.NATIVE['item'],item)])
    def test_click_only_requests_original_native_confirmation(self):policy.invoke(self.w,'click');self.assertEqual(self.calls,[('widget',policy.NATIVE['dialog'])])
    def test_cancelled_and_closed_results_do_not_play(self):
        for result in (1,2):policy.invoke(self.w,'result',result)
        self.assertFalse(self.calls)
    def test_confirmed_reads_current_entry_at_completion(self):
        policy.invoke(self.w,'click');self.current=object();policy.invoke(self.w,'result',0);self.assertEqual(self.calls[-1],('sub','PlayReplay',self.current))
    def test_confirmed_null_still_calls_native_null_safe_play(self):self.current=None;policy.invoke(self.w,'result',0);self.assertEqual(self.calls[-1],('sub','PlayReplay',None))
    def test_complete_profiles_do_not_send_text_or_timespan_through_python(self):
        for p in ('Python','BlueprintFallback'):
            cls=getattr(policy,'LyraReplayEntry'+p+'Profile');self.assertEqual({f.override for f in vars(cls).values() if callable(f)},set(policy.GATES.values()))
