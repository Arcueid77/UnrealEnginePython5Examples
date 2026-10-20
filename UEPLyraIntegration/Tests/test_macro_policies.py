"""Macro completion semantics, first-element rules and native tag/asset identity."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.load_class=lambda n:n
structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda a:a is not None
spec=importlib.util.spec_from_file_location('_macro_policies_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/macro_policies.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)


class MacroPolicyTests(unittest.TestCase):
    def setUp(self):
        self.weapon=types.SimpleNamespace(is_a=lambda c:c==policy.WEAPON);self.wrong=types.SimpleNamespace(is_a=lambda c:False);self.spawned=[self.weapon];self.instance=types.SimpleNamespace(call_function=lambda f:self.spawned);self.instances=[self.instance];self.manager=types.SimpleNamespace(call_function=lambda *a:self.instances);self.target=types.SimpleNamespace(call_function=lambda *a:self.manager);self.item=types.SimpleNamespace(call_function=self.item_call);self.has=True;self.ammo=17;self.quick=types.SimpleNamespace(call_function=lambda f:self.item);self.controller=types.SimpleNamespace(get_component_by_type=lambda c:self.quick);self.instigator=types.SimpleNamespace(call_function=lambda f:self.controller);self.echo=types.SimpleNamespace(get_property=lambda n:self.instigator);self.invis=object();native.load_object=lambda *a:self.invis
    def item_call(self,f,tag):return self.has if f=='HasStatTag' else self.ammo
    def test_normal_weapon_keeps_exact_native_identity(self):self.assertIs(policy.weapon_for(self.target),self.weapon)
    def test_empty_equipment_array_does_not_search_another_source(self):
        self.instances=[];self.assertIsNone(policy.weapon_for(self.target))
    def test_only_first_equipment_instance_is_considered(self):
        self.instances=[None,self.instance];self.assertIsNone(policy.weapon_for(self.target))
    def test_only_first_spawned_actor_is_considered(self):
        self.spawned=[self.wrong,self.weapon];self.assertIsNone(policy.weapon_for(self.target));self.spawned=[None,self.weapon];self.assertIsNone(policy.weapon_for(self.target))
    def test_valid_first_actor_is_not_replaced_by_later_actor(self):
        self.spawned=[self.weapon,self.wrong];self.assertIs(policy.weapon_for(self.target),self.weapon)
    def test_empty_spawned_actor_array_uses_failure_path(self):
        self.spawned=[];self.assertIsNone(policy.weapon_for(self.target))
    def test_no_instigator_never_completes_ammo_macro(self):
        self.instigator=None;self.assertEqual(policy.weapon_ammo(self.echo),(False,0,False))
    def test_no_controller_never_completes_ammo_macro(self):
        self.controller=None;self.assertEqual(policy.weapon_ammo(self.echo),(False,0,False))
    def test_no_quickbar_never_completes_ammo_macro(self):
        self.quick=None;self.assertEqual(policy.weapon_ammo(self.echo),(False,0,False))
    def test_empty_active_slot_preserves_original_diagnostic_fallback(self):
        self.item=None;self.assertEqual(policy.weapon_ammo(self.echo),(False,0,True))
    def test_missing_magazine_stat_completes_with_zero(self):
        self.has=False;self.assertEqual(policy.weapon_ammo(self.echo),(True,0,False))
    def test_present_magazine_stat_uses_native_stack_count(self):self.assertEqual(policy.weapon_ammo(self.echo),(True,17,False))
    def test_tag_helper_passes_native_name_without_python_case_rules(self):
        calls=[];mesh=types.SimpleNamespace(call_function=lambda *a:calls.append(a) or True);self.assertTrue(policy.ignore_tag(mesh));self.assertEqual(calls,[('ComponentHasTag','ignore')])
    def test_specific_mesh_uses_native_asset_identity(self):
        mesh=types.SimpleNamespace(call_function=lambda f:self.invis);self.assertTrue(policy.ignore_specific(mesh));mesh.call_function=lambda f:object();self.assertFalse(policy.ignore_specific(mesh))
