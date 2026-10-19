"""Original Fire state order, exposed spawn properties and cache reuse."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");enums=types.ModuleType("unreal_engine.enums")
enums.ESpawnActorCollisionHandlingMethod=types.SimpleNamespace(Undefined=0)
enums.ESpawnActorScaleMethod=types.SimpleNamespace(OverrideRootScale=1)
enums.EAttachmentRule=types.SimpleNamespace(KeepRelative=0)
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda obj:obj is not None and getattr(obj,"alive",True)
base=types.ModuleType("uep_lyra_weapons.weapon_actor_helpers_mixin")
class Helpers:
    def AddFakeProjectileData(self,*args):pass
    def TriggerFireAudio(self,*args):pass
    def UpdateCustomStencil(self,*args):pass
    def UpdateTeamColors(self,*args):pass
base.LyraWeaponActorHelpersPythonProfile=base.LyraWeaponActorHelpersBlueprintFallbackProfile=Helpers
spec=importlib.util.spec_from_file_location("uep_lyra_weapons._weapon_actor_fire_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_actor_fire_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.enums":enums,"uep_lyra_world.effect_pad_mixin":helpers,"uep_lyra_weapons.weapon_actor_helpers_mixin":base}):spec.loader.exec_module(policy)


class FX:
    def __init__(self,owner,name):self.owner,self.name,self.data,self.alive=owner,name,{},True
    def set_property(self,name,value):self.data[name]=value;self.owner.calls.append((self.name,"write",name,value))
    def call_function(self,name,*args,**kwargs):self.owner.calls.append((self.name,name,args,kwargs))


class TestWeaponActorFireMixin(unittest.TestCase):
    def setUp(self):
        self.calls,self.finished,self.spawned=[],[],[]
        self.mesh=types.SimpleNamespace(call_function=lambda *args:"muzzle")
        self.data={"SkeletalMesh":self.mesh,"NeedsFakeProjectileData":False,"Numer Of Fake Projectiles":2,
            "Shell Eject System":"shell-system","Muzzle Flash System":"muzzle-system","Tracer System":"tracer-system","Shell Eject Mesh":"shell-mesh"}
        for field,_,_ in policy.STAGES:self.data[field]=FX(self,field)
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.fake)
        native.FVector=lambda *args:args or "zero";native.FRotator=lambda:"rotation";native.FTransform=lambda *args:("transform",args)
        native.load_class=lambda path:path
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.backend))
    def write(self,name,value):self.data[name]=value;self.calls.append(("actor","write",name,value))
    def fake(self,*args):
        self.calls.append(("fake",args))
        self.data["Impact Positions"]=list(self.data["Impact Positions"])+["fake-position"]
    def backend(self,method,*args):
        self.calls.append((method,args))
        if method=="BeginDeferredActorSpawnFromClass":
            value=FX(self,args[1]);self.spawned.append(value);return value
        if method=="FinishSpawningActor":self.finished.append(dict(args[0].data));return args[0]
        self.fail(method)
    def run_fire(self):policy.fire(self.actor,["p"],["n"],[0])
    def test_input_property_order_and_muzzle_before_fx(self):
        self.run_fire();self.assertEqual([row[2] for row in self.calls[:4]],["Impact Positions","Impact Normals","ImpactSurfaceTypes","MuzzlePosition"])
    def test_three_original_fx_order_and_lowercase_decal_entry(self):
        self.run_fire();self.assertEqual([row[:2] for row in self.calls if row[1] in ("Fire","fire")],[("WeaponFire","Fire"),("Weapon Impacts","Fire"),("Weapon Decals","fire")])
    def test_valid_cached_actors_not_spawned_or_attached_again(self):
        self.run_fire();self.assertEqual(self.spawned,[]);self.assertFalse(any(row[1]=="K2_AttachToComponent" for row in self.calls))
    def test_independent_original_surface_field_spellings(self):
        self.run_fire();self.assertEqual(self.data["WeaponFire"].data["ImpactSurfaceTypes"],[0]);self.assertEqual(self.data["Weapon Decals"].data["Impact Surface Types"],[0])
    def test_only_impacts_receive_muzzle_position(self):
        self.run_fire();self.assertEqual(self.data["Weapon Impacts"].data["MuzzlePosition"],"muzzle");self.assertNotIn("MuzzlePosition",self.data["WeaponFire"].data)
    def test_fake_helper_receives_original_default_five_degree_angle(self):
        self.data["NeedsFakeProjectileData"]=True;self.run_fire();self.assertIn(("fake",("Add Fake Projectile Data",2,5.)),self.calls)
        self.assertEqual(self.data["WeaponFire"].data["ImpactPositions"],["p","fake-position"])
    def test_fake_helper_not_called_when_flag_false(self):self.run_fire();self.assertFalse(any(row[0]=="fake" for row in self.calls))
    def test_cold_spawn_exposed_properties_set_before_finish(self):
        for field,_,_ in policy.STAGES:self.data[field]=None
        self.run_fire();self.assertEqual(len(self.spawned),3)
        self.assertEqual(self.finished[0]["Skeletal Mesh Component"],self.mesh)
        self.assertTrue(all(self.finished[0][key] for key in ("Enable Shell Eject","Enable Muzzle Flash","Enable Tracer")))
        self.assertEqual(self.finished[0]["Tracer System"],"tracer-system");self.assertEqual(self.finished[1],{"Distance Threshold":500.})
    def test_native_spawn_owner_collision_and_scale_options(self):
        self.data["WeaponFire"]=None;self.run_fire();row=next(row for row in self.calls if row[0]=="BeginDeferredActorSpawnFromClass")
        self.assertEqual(row[1][3:],(0,None,1))
    def test_native_attachment_rules_and_weld(self):
        self.data["WeaponFire"]=None;self.run_fire();row=next(row for row in self.calls if len(row)>1 and row[1]=="K2_AttachToComponent")
        self.assertEqual(row[3],dict(Parent=self.mesh,SocketName="None",LocationRule=0,RotationRule=0,ScaleRule=0,bWeldSimulatedBodies=True))
    def test_only_invalid_cached_fx_recreated(self):
        self.data["Weapon Impacts"].alive=False;self.run_fire();self.assertEqual(len(self.spawned),1);self.assertEqual(self.spawned[0].name,policy.STAGES[1][1])
    def test_missing_mesh_preserves_zero_muzzle_default(self):self.data["SkeletalMesh"]=None;self.run_fire();self.assertEqual(self.data["MuzzlePosition"],"zero")
    def test_fallback_passes_all_three_reflected_arrays(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args)
        policy.LyraWeaponActorFireBlueprintFallbackProfile.Fire(self.actor,[1],[2],[3]);self.assertEqual(self.calls,[("Fire",[1],[2],[3])])
    def test_original_helpers_retained(self):self.assertIs(policy.LyraWeaponActorFirePythonProfile.UpdateTeamColors,Helpers.UpdateTeamColors)
