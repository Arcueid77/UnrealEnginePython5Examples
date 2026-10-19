"""Retained Array_Set tail semantics and native Niagara/latent boundary decisions."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");enums=types.ModuleType("unreal_engine.enums")
enums.ENCPoolMethod=types.SimpleNamespace(**{"None":0})
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location("_weapon_decals_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_decals_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.enums":enums,"uep_lyra_world.effect_pad_mixin":helpers}):spec.loader.exec_module(policy)


class Component:
    def __init__(self,owner,active=True):self.owner,self.active=owner,active
    def call_function(self,method,*args):
        self.owner.calls.append(("component",method,args));return self.active if method=="IsActive" else None


class TestWeaponDecalsMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.new=None;self.data={"Surface Types":[3,2,1,0],"Impact Surface Types":[0,1,2],
            "ImpactPositions":[(100.,0.,0.)],"ImpactNormals":[(-1.,0.,0.)],"Decal System":"decal-asset","Impact Trigger":False}
        self.data["Decal"]=Component(self)
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=lambda *args:self.calls.append(("actor",args)))
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda method,*args,**kw:self.backend(method,args,kw)))
        native.FVector=lambda *args:args or (0.,0.,0.);native.FRotator=lambda *args:args or (0.,0.,0.)
    def write(self,name,value):self.calls.append(("write",name,value));self.data[name]=value
    def backend(self,method,args,kw):
        self.calls.append((method,args,kw));return self.new if method=="SpawnSystemAtLocation" else None
    def test_shorter_surface_input_preserves_prior_tail(self):
        policy.fire(self.actor);self.data["Impact Surface Types"]=[3];policy.fire(self.actor);self.assertEqual(self.data["Surface Types"],[3,1,2,0])
    def test_empty_surface_input_retains_whole_previous_array(self):
        self.data["Impact Surface Types"]=[];policy.fire(self.actor);self.assertEqual(self.data["Surface Types"],[3,2,1,0])
    def test_growing_surface_input_extends_native_int_array(self):
        self.data["Impact Surface Types"]=[0,1,2,3,4,5];policy.fire(self.actor);self.assertEqual(self.data["Surface Types"],[0,1,2,3,4,5])
    def test_active_cache_reused_even_if_asset_changed(self):
        old=self.data["Decal"];self.data["Decal System"]="other";policy.fire(self.actor);self.assertIs(self.data["Decal"],old);self.assertEqual(policy.evidence(self.actor)["spawns"],0)
    def test_inactive_cache_replaced_and_trigger_reset(self):
        self.data["Decal"].active=False;self.data["Impact Trigger"]=True;self.new=Component(self);policy.fire(self.actor)
        self.assertIs(self.data["Decal"],self.new);self.assertEqual([r[2] for r in self.calls if r[:2]==("write","Impact Trigger")],[False,True])
    def test_reused_cache_toggles_trigger(self):
        policy.fire(self.actor);policy.fire(self.actor);self.assertIs(self.data["Impact Trigger"],False)
    def test_spawn_uses_world_origin_default_rotation_and_scale(self):
        self.data["Decal"]=None;policy.fire(self.actor);kw=next(r[2] for r in self.calls if r[0]=="SpawnSystemAtLocation")
        self.assertIs(kw["WorldContextObject"],self.actor);self.assertEqual((kw["Location"],kw["Rotation"],kw["Scale"]),((0.,0.,0.),(0.,0.,0.),(1.,1.,1.)))
        self.assertTrue(kw["bAutoDestroy"] and kw["bAutoActivate"] and kw["bPreCullCheck"]);self.assertEqual(kw["PoolingMethod"],0)
    def test_position_array_remains_position_typed(self):
        policy.fire(self.actor);self.assertTrue(any(r[0]=="SetNiagaraArrayPosition" and r[1][1:]==("User.ImpactPositions",self.data["ImpactPositions"]) for r in self.calls))
    def test_normals_use_actual_input_without_matching_position_count(self):
        self.data["ImpactNormals"]=[];policy.fire(self.actor);self.assertTrue(any(r[0]=="SetNiagaraArrayVector" and r[1][1:]==("User.ImpactNormals",[]) for r in self.calls))
    def test_hit_count_uses_positions_rather_than_retained_surface_tail(self):
        policy.fire(self.actor);self.assertIn(("component","SetVariableInt",("User.NumberOfHits",1)),self.calls)
    def test_failed_spawn_still_updates_surface_tail_and_requests_delay(self):
        self.data["Decal"]=None;policy.fire(self.actor);self.assertIs(self.data["Impact Trigger"],True);self.assertEqual(self.data["Surface Types"],[0,1,2,0]);self.assertEqual(self.calls[-1],("actor",(policy.DELAY,)))
        self.assertFalse(any(r[0].startswith("SetNiagaraArray") for r in self.calls))
    def test_cleanup_valid_inactive_component_repeats_delay(self):
        self.data["Decal"].active=False;policy.cleanup(self.actor);self.assertEqual(self.calls,[("actor",(policy.DELAY,))])
    def test_cleanup_invalid_component_destroys_actor(self):
        self.data["Decal"]=None;policy.cleanup(self.actor);self.assertEqual(self.calls,[("actor",("K2_DestroyActor",))])
    def test_lowercase_original_entry_and_latent_callback_preserved(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args)
        policy.LyraWeaponDecalsBlueprintFallbackProfile.Fire(self.actor);policy.LyraWeaponDecalsBlueprintFallbackProfile.AfterDelay(self.actor)
        self.assertEqual(self.calls,[("fire",),(policy.AFTER,)]);self.assertEqual(policy.LyraWeaponDecalsPythonProfile.Fire.override,"fire")
