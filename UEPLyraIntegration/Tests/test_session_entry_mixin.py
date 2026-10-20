"""Entry policy keeps opaque native text/async/delegate payload boundaries."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
native=types.ModuleType('unreal_engine');native.find_class=lambda name:name
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda name:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location('_session_entry_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/session_entry_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)
class SessionEntryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.props=dict(SessionEntry='prior',JoiningProgressWidget=None,SessionButton=types.SimpleNamespace(call_function=lambda fn,*args:self.calls.append(('button',fn,*args))));self.w=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=lambda fn,*args:self.calls.append(('widget',fn,*args)))
    def set(self,name,value):self.props[name]=value;self.calls.append(('set',name,value))
    def test_null_list_item_preserves_previous_row_without_loading(self):policy.invoke(self.w,'item',None);self.assertEqual(self.props['SessionEntry'],'prior');self.assertFalse(self.calls)
    def test_wrong_list_item_type_preserves_previous_row(self):policy.invoke(self.w,'item',types.SimpleNamespace(is_a=lambda cls:False));self.assertFalse(self.calls)
    def test_valid_list_item_stored_before_native_primary_load(self):
        item=types.SimpleNamespace(is_a=lambda cls:cls=='CommonSession_SearchResult');policy.invoke(self.w,'item',item);self.assertEqual(self.calls,[('set','SessionEntry',item),('widget',policy.NATIVE['display_load'])])
    def test_native_loaded_definition_enters_original_five_text_payload(self):policy.invoke(self.w,'display_ready',object());self.assertEqual(self.calls,[('widget',policy.NATIVE['texts'])])
    def test_image_uses_loaded_definition_tile_icon(self):policy.invoke(self.w,'image',types.SimpleNamespace(get_property=lambda n:'icon' if n=='TileIcon' else None));self.assertEqual(self.calls,[('button','SetMapImage','icon')])
    def test_click_uses_original_public_join_event(self):policy.invoke(self.w,'click');self.assertEqual(self.calls,[('widget','JoinSession')])
    def test_join_starts_original_native_spinner_push(self):policy.invoke(self.w,'join');self.assertEqual(self.calls,[('widget',policy.NATIVE['spinner'])])
    def test_spinner_is_stored_before_native_load_and_loading_macro(self):policy.invoke(self.w,'spinner','spinner');self.assertEqual(self.calls,[('set','JoiningProgressWidget','spinner'),('widget',policy.NATIVE['prepare_load'])])
    def test_only_native_loading_macro_completion_submits_join(self):policy.invoke(self.w,'prepared');self.assertEqual(self.calls,[('widget',policy.NATIVE['submit'])])
    def test_success_after_native_unbind_and_pop_has_no_extra_effect(self):policy.invoke(self.w,'completed',True);self.assertFalse(self.calls)
    def test_failure_after_native_unbind_and_pop_uses_original_ftext_message(self):policy.invoke(self.w,'completed',False);self.assertEqual(self.calls,[('widget',policy.NATIVE['failure'])])
    def test_complete_profiles_do_not_override_native_ftext_or_result_struct_events(self):
        for p in ('Python','BlueprintFallback'):
            cls=getattr(policy,'LyraSessionEntry'+p+'Profile');self.assertEqual({f.override for f in vars(cls).values() if callable(f)},set(policy.GATES.values()));self.assertNotIn('OnJoinCompleted',vars(cls));self.assertNotIn('Set Texts',vars(cls))
    def test_fallback_does_not_replace_original_input_or_async_io(self):self.assertTrue(policy.LyraSessionEntryBlueprintFallbackProfile.item(self.w,None));self.assertFalse(self.calls);self.assertEqual(policy.evidence(self.w)['fallback_item'],1)
