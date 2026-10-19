"""Original bucketing, inverted distance reuse and native backend call contracts."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");enums=types.ModuleType("unreal_engine.enums");structs=types.ModuleType("unreal_engine.structs")
enums.ENCPoolMethod=types.SimpleNamespace(**{"None":0});structs.NiagaraDataChannelSearchParameters=lambda **kw:kw
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location("_weapon_impacts_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_impacts_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.enums":enums,"unreal_engine.structs":structs,"uep_lyra_world.effect_pad_mixin":helpers}):spec.loader.exec_module(policy)


class Bucket:
    def __init__(self):self.data={}
    def set_field(self,name,value):self.data[name]=list(value)
    def get_field(self,name):return self.data[name]
    def clone(self):
        value=Bucket();value.data={key:list(items) for key,items in self.data.items()};return value


class Component:
    def __init__(self,owner,point=(0.,0.,0.)):self.owner,self.point=owner,point
    def call_function(self,method,*args,**kw):
        self.owner.calls.append(("component",method,kw or args))
        if method=="K2_GetComponentLocation":return self.point
        if method=="K2_SetWorldLocation":self.point=kw["NewLocation"]


class TestWeaponImpactsMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.new=Component(self);self.writer=Component(self)
        self.data={"ImpactBuckets":[],"Impact Systems":[],"ImpactPositions":[(1.,0.,0.),(2.,0.,0.),(3.,0.,0.)],
            "ImpactNormals":[(-1.,0.,0.)]*3,"ImpactSurfaceTypes":[2,0,2],"CurrentIndex":77,"CurrentSurface":1,"Use Data Channels":False,
            "Distance Threshold":10.,"MuzzlePosition":(25.,-10.,5.),"DefaultSceneRoot":"root","Has Valid Systems":True}
        self.data.update({name:name for name in policy.TEMPLATES})
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=lambda *args:self.calls.append(("actor",args)))
        native.FVector=lambda *args:args or (0.,0.,0.);native.FRotator=lambda *args:args or (0.,0.,0.);native.load_struct=lambda path:Bucket
        native.load_object=lambda cls,path:path;native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda method,*args,**kw:self.backend(method,args,kw)))
    def write(self,name,value):self.calls.append(("write",name,value));self.data[name]=value
    def backend(self,method,args,kw):
        self.calls.append((method,args,kw))
        if method=="SpawnSystemAtLocation":return self.new
        if method=="WriteToNiagaraDataChannel":return self.writer
        if method=="Vector_DistanceSquared":return sum((a-b)**2 for a,b in zip(*args))
    def prepare(self,position=(0.,0.,0.),component=None,surface=0):
        self.data["ImpactBuckets"]=[policy.bucket() for _ in range(surface+1)];self.data["ImpactBuckets"][surface]=policy.bucket([position],[(-1.,0.,0.)])
        self.data["Impact Systems"]=[None]*(surface+1);self.data["Impact Systems"][surface]=component
    def test_buckets_reset_existing_arrays_without_truncating_slots(self):
        self.data["ImpactBuckets"]=[policy.bucket([(999.,0.,0.)],[(0.,1.,0.)]) for _ in range(5)];policy.add_impacts(self.actor)
        self.assertEqual(len(self.data["ImpactBuckets"]),5);self.assertEqual(policy.fields(self.data["ImpactBuckets"][4]),([],[]))
    def test_surface_duplicates_append_in_input_order(self):
        policy.add_impacts(self.actor);self.assertEqual(policy.fields(self.data["ImpactBuckets"][2])[0],[(1.,0.,0.),(3.,0.,0.)]);self.assertEqual(self.data["CurrentIndex"],77)
    def test_existing_struct_views_are_detached_before_native_array_writeback(self):
        old=policy.bucket([(999.,0.,0.)],[(1.,0.,0.)]);self.data["ImpactBuckets"]=[old]
        def native_write(name,value):
            if name=="ImpactBuckets":
                for item in self.data[name]:item.data.clear()
            self.write(name,value)
        self.actor.set_property=native_write;policy.add_impacts(self.actor)
        self.assertIsNot(self.data["ImpactBuckets"][0],old);self.assertEqual(policy.fields(self.data["ImpactBuckets"][0])[0],[(2.,0.,0.)])
    def test_sparse_surface_grows_default_empty_buckets(self):
        self.data["ImpactSurfaceTypes"]=[6];policy.add_impacts(self.actor);self.assertEqual(len(self.data["ImpactBuckets"]),7);self.assertEqual(policy.fields(self.data["ImpactBuckets"][5]),([],[]))
    def test_empty_input_clears_arrays_and_preserves_current_index(self):
        self.data["ImpactBuckets"]=[policy.bucket([(99.,0.,0.)],[(1.,0.,0.)])];self.data["ImpactSurfaceTypes"]=[];policy.add_impacts(self.actor)
        self.assertEqual(policy.fields(self.data["ImpactBuckets"][0]),([],[]));self.assertEqual(self.data["CurrentIndex"],77)
    def test_missing_vector_uses_native_vm_zero_default(self):
        self.data["ImpactNormals"]=[];policy.add_impacts(self.actor);self.assertEqual(policy.fields(self.data["ImpactBuckets"][2])[1],[(0.,0.,0.)]*2)
    def test_selector_skips_buckets_missing_either_array(self):
        self.data["ImpactBuckets"]=[policy.bucket([(1.,0.,0.)],[]),policy.bucket([],[(1.,0.,0.)])];policy.select_spawns(self.actor)
        self.assertFalse(any(row[0]=="actor" for row in self.calls));self.assertEqual(self.data["CurrentSurface"],1)
    def test_channel_routing_is_only_concrete_and_glass(self):
        self.data["Use Data Channels"]=True;self.data["ImpactBuckets"]=[policy.bucket([(1.,0.,0.)],[(1.,0.,0.)]) for _ in range(4)];policy.select_spawns(self.actor)
        self.assertEqual([r[1] for r in self.calls if r[0]=="actor"],[("SpawnFromArrays",0),("SpawnFromArrays",1),("SpawnFromDataChannels",2),("SpawnFromDataChannels",3)])
    def test_disabled_channels_route_all_populated_surfaces_to_arrays(self):
        self.data["ImpactBuckets"]=[policy.bucket([(1.,0.,0.)],[(1.,0.,0.)]) for _ in range(4)];policy.select_spawns(self.actor)
        self.assertEqual([r[1] for r in self.calls if r[0]=="actor"],[("SpawnFromArrays",i) for i in range(4)])
        self.assertEqual(self.data["CurrentSurface"],1)
    def test_far_valid_component_reused_without_active_or_asset_check(self):
        old=Component(self);self.prepare((11.,0.,0.),old);policy.spawn_arrays(self.actor,0);self.assertIs(self.data["Impact Systems"][0],old);self.assertEqual(policy.evidence(self.actor)["spawns"],0)
    def test_equal_threshold_recreates_component(self):
        old=Component(self);self.prepare((10.,0.,0.),old);policy.spawn_arrays(self.actor,0);self.assertIs(self.data["Impact Systems"][0],self.new)
    def test_near_valid_component_recreates(self):
        old=Component(self);self.prepare((9.,0.,0.),old);policy.spawn_arrays(self.actor,0);self.assertIs(self.data["Impact Systems"][0],self.new)
    def test_negative_threshold_is_still_squared(self):
        self.data["Distance Threshold"]=-10.;old=Component(self);self.prepare((9.,0.,0.),old);policy.spawn_arrays(self.actor,0);self.assertIs(self.data["Impact Systems"][0],self.new)
    def test_invalid_template_preserves_component_and_native_parameters(self):
        self.prepare(component=Component(self));self.data["Default"]=None;policy.spawn_arrays(self.actor,0);self.assertEqual(self.calls,[])
    def test_unmapped_select_enum_has_null_native_default(self):
        policy.spawn_arrays(self.actor,6);self.assertEqual(policy.evidence(self.actor)["invalid_templates"],1);self.assertEqual(self.calls,[])
    def test_original_spawn_options_and_sparse_cache_growth(self):
        self.prepare(surface=3);self.data["Impact Systems"]=[];policy.spawn_arrays(self.actor,3);kw=next(r[2] for r in self.calls if r[0]=="SpawnSystemAtLocation")
        self.assertEqual(kw["SystemTemplate"],"Glass");self.assertTrue(kw["bAutoDestroy"] and kw["bAutoActivate"] and kw["bPreCullCheck"]);self.assertEqual(self.data["Impact Systems"],[None,None,None,self.new])
    def test_array_parameter_names_types_and_nonreset_activation(self):
        self.prepare();policy.spawn_arrays(self.actor,0);self.assertIn(("component","SetVariableInt",("NumberOfHits",1)),self.calls)
        self.assertIn(("component","SetVariablePosition",("User.MuzzlePosition",(25.,-10.,5.))),self.calls);self.assertIn(("component","Activate",(False,)),self.calls)
        self.assertTrue(any(r[0]=="SetNiagaraArrayPosition" and r[1][1]=="User.ImpactPositions" for r in self.calls))
    def test_world_move_skips_out_hit_result_with_named_inputs(self):
        self.prepare();policy.spawn_arrays(self.actor,0)
        self.assertIn(("component","K2_SetWorldLocation",dict(NewLocation=(0.,0.,0.),bSweep=False,bTeleport=False)),self.calls)
    def test_failed_native_spawn_still_writes_null_cache_slot(self):
        self.prepare(surface=3);self.new=None;policy.spawn_arrays(self.actor,3);self.assertIsNone(self.data["Impact Systems"][3]);self.assertEqual(policy.evidence(self.actor)["invalid_components"],1)
    def test_channel_writer_uses_original_search_count_and_visibility(self):
        self.prepare((7.,8.,9.),surface=2);policy.spawn_channel(self.actor,2);kw=next(r[2] for r in self.calls if r[0]=="WriteToNiagaraDataChannel")
        self.assertEqual(kw["SearchParams"],dict(OwningComponent="root",Location=(7.,8.,9.),bOverrideLocation=True));self.assertEqual(kw["Count"],1)
        self.assertTrue(kw["bVisibleToGame"] and kw["bVisibleToCPU"] and kw["bVisibleToGPU"]);self.assertEqual(kw["DebugSource"],"")
    def test_channel_writes_each_native_typed_field(self):
        self.prepare(surface=3);policy.spawn_channel(self.actor,3)
        self.assertEqual([r[1] for r in self.calls if r[0]=="component"],["WritePosition","WriteVector","WritePosition","WriteEnum"])
        self.assertIn(("component","WriteEnum",("ImpactSurface",0,3)),self.calls)
    def test_invalid_channel_writer_does_not_write_component_fields(self):
        self.prepare(surface=2);self.writer=None;policy.spawn_channel(self.actor,2);self.assertFalse(any(r[0]=="component" for r in self.calls))
    def test_fire_orders_native_helpers_then_clears_only_input_arrays_and_delays(self):
        self.data["ImpactBuckets"]=[policy.bucket()];policy.fire(self.actor)
        self.assertEqual([r[1] for r in self.calls if r[0]=="actor"],[("AddImpactsToBuckets",),("SpawnParticlesFromImpacts",),(policy.DELAY,)])
        self.assertEqual(len(self.data["ImpactBuckets"]),1);self.assertEqual(self.data["ImpactPositions"],[])
    def test_cleanup_valid_component_sets_flag_and_repeats(self):
        self.data["Impact Systems"]=[None,Component(self),None];policy.cleanup(self.actor);self.assertIs(self.data["Has Valid Systems"],True);self.assertEqual(self.calls[-1],("actor",(policy.DELAY,)))
    def test_cleanup_invalid_components_resets_stale_flag_and_destroys(self):
        self.data["Impact Systems"]=[None];policy.cleanup(self.actor);self.assertIs(self.data["Has Valid Systems"],False);self.assertEqual(self.calls[-1],("actor",("K2_DestroyActor",)))
    def test_fallback_delegates_parameterized_native_methods(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args);policy.LyraWeaponImpactsBlueprintFallbackProfile.SpawnFromArrays(self.actor,3)
        policy.LyraWeaponImpactsBlueprintFallbackProfile.SpawnFromDataChannels(self.actor,2);self.assertEqual(self.calls,[("SpawnFromArrays",3),("SpawnFromDataChannels",2)])
