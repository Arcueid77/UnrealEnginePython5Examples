"""Portal local-owner gate,current experience and original offline payload IO."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
spec=importlib.util.spec_from_file_location('_editor_portal_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/editor_experience_portal_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)
class EditorExperiencePortalPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.experience=object();self.actor=types.SimpleNamespace(get_property=lambda n:self.experience,call_function=self.call);policy.ue=native;policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:types.SimpleNamespace(call_function=lambda g,*b:self.calls.append((g,*b))))
    def call(self,f,*args):self.calls.append((f,*args));return 'request' if f==policy.NATIVE['request'] else None
    def test_widget_receives_current_experience_before_original_delay(self):
        tile=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append((f,*a)));policy.invoke(self.actor,'widget',tile);self.assertEqual(self.calls,[('Set User Facing Experience',self.experience),(policy.NATIVE['delay'],)])
    def test_only_default_experience_applies_original_native_color(self):policy.invoke(self.actor,'color',False);self.assertFalse(self.calls);policy.invoke(self.actor,'color',True);self.assertEqual(self.calls,[(policy.NATIVE['color'],)])
    def test_unrelated_actor_or_uncontrolled_pawn_does_not_load(self):policy.invoke(self.actor,'overlap',None);policy.invoke(self.actor,'overlap',types.SimpleNamespace(is_a=lambda c:False));policy.invoke(self.actor,'overlap',types.SimpleNamespace(is_a=lambda c:True,call_function=lambda f:None));self.assertFalse(self.calls)
    def test_nonlocal_controller_does_not_load(self):
        controller=types.SimpleNamespace(call_function=lambda f:False);pawn=types.SimpleNamespace(is_a=lambda c:True,call_function=lambda f:controller);policy.invoke(self.actor,'overlap',pawn);self.assertFalse(self.calls)
    def test_local_player_controller_uses_public_load_event(self):
        controller=types.SimpleNamespace(call_function=lambda f:True,is_a=lambda c:c=='PlayerController');pawn=types.SimpleNamespace(is_a=lambda c:c=='Pawn',call_function=lambda f:controller);policy.invoke(self.actor,'overlap',pawn);self.assertEqual(self.calls,[('LoadIntoExperience',controller)])
    def test_null_experience_does_not_push_spinner(self):self.experience=None;policy.invoke(self.actor,'load','player');self.assertFalse(self.calls)
    def test_valid_experience_uses_original_native_spinner(self):policy.invoke(self.actor,'load','player');self.assertEqual(self.calls,[(policy.NATIVE['push'],)])
    def test_afterpush_rereads_experience_and_submits_original_native_offline_request(self):policy.invoke(self.actor,'load','player');self.experience=object();policy.invoke(self.actor,'pushed','player');self.assertEqual(self.calls[-2:],[(policy.NATIVE['request'],self.experience),('HostSession','player','request')])
