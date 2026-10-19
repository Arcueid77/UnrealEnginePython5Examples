"""Owner filtering, exact native binding and team callback business order."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
base=types.ModuleType("uep_lyra_weapons.weapon_actor_fire_mixin")
class Fire:
    def AddFakeProjectileData(self,*args):pass
    def TriggerFireAudio(self,*args):pass
    def UpdateCustomStencil(self,*args):pass
    def UpdateTeamColors(self,*args):pass
    def Fire(self,*args):pass
base.LyraWeaponActorFirePythonProfile=base.LyraWeaponActorFireBlueprintFallbackProfile=Fire
spec=importlib.util.spec_from_file_location("uep_lyra_weapons._weapon_actor_begin_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_actor_begin_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":helpers,"uep_lyra_weapons.weapon_actor_fire_mixin":base}):spec.loader.exec_module(policy)


class TestWeaponActorBeginMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.pawn=True
        self.owner=types.SimpleNamespace(is_a=lambda cls:self.pawn)
        self.proxy=types.SimpleNamespace(call_function=lambda *args:self.calls.append(("activate",args)))
        self.actor=types.SimpleNamespace(call_function=self.call,set_property=lambda *args:self.calls.append(("write",args)))
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.factory))
        native.load_class=lambda path:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda *args:self.calls.append(("bind",args))))
    def call(self,method,*args):
        if method=="GetOwner":return self.owner
        if method==policy.BIND:self.calls.append(("bind",(method,*args)));return
        self.calls.append((method,args))
    def factory(self,*args):self.calls.append(("factory",args));return self.proxy
    def test_original_write_factory_bind_activate_order(self):policy.begin(self.actor);self.assertEqual([row[0] for row in self.calls],["write","factory","bind","activate"])
    def test_factory_uses_owner_pawn_as_context(self):policy.begin(self.actor);self.assertEqual(self.calls[1],("factory",("ObserveTeamColors",self.owner)))
    def test_transport_binds_native_proxy_to_weapon(self):policy.begin(self.actor);self.assertEqual(self.calls[2],("bind",(policy.BIND,self.proxy)))
    def test_invalid_owner_noops_without_overwriting_existing_state(self):self.owner=None;policy.begin(self.actor);self.assertEqual(self.calls,[])
    def test_nonpawn_owner_noops(self):self.pawn=False;policy.begin(self.actor);self.assertEqual(self.calls,[])
    def test_null_factory_skips_bind_and_activation(self):self.proxy=None;policy.begin(self.actor);self.assertEqual([row[0] for row in self.calls],["write","factory"])
    def test_per_call_factory_not_deduplicated(self):policy.begin(self.actor);policy.begin(self.actor);self.assertEqual(policy.evidence(self.actor)["factories"],2)
    def test_assigned_team_stencil_then_color(self):policy.changed(self.actor,True,2,"display");self.assertEqual(self.calls,[("UpdateCustomStencil",(2,)),("UpdateTeamColors",("display",))])
    def test_missing_team_leaves_previous_visual_state_untouched(self):policy.changed(self.actor,False,-1,None);self.assertEqual(self.calls,[])
    def test_null_display_still_follows_original_callback_sequence(self):policy.changed(self.actor,True,3,None);self.assertEqual(self.calls[-1],("UpdateTeamColors",(None,)))
    def test_fallback_preserves_actual_beginplay_entry(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args)
        policy.LyraWeaponActorBeginBlueprintFallbackProfile.ReceiveBeginPlay(self.actor);self.assertEqual(self.calls,[("ReceiveBeginPlay",)])
    def test_fallback_preserves_guid_callback_and_three_inputs(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args)
        policy.LyraWeaponActorBeginBlueprintFallbackProfile.ObservedTeamChanged(self.actor,True,2,"display");self.assertEqual(self.calls,[(policy.CALLBACK,True,2,"display")])
    def test_existing_fire_and_helpers_retained(self):self.assertIs(policy.LyraWeaponActorBeginPythonProfile.Fire,Fire.Fire)
