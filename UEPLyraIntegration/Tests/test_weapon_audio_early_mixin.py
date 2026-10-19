"""Original reflection eligibility, trace routing, float locals and Tap inputs."""
import importlib.util
import math
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");world=types.ModuleType("uep_lyra_world.effect_pad_mixin");world.valid=lambda value:value is not None
trace=types.ModuleType("uep_lyra_abilities.melee_trace_mixin");trace.native_outputs=lambda cls,method,value:value;trace.trace_outputs=lambda method,value:(value[0],value[1]);trace.break_hit=lambda value:value
dispatch=types.ModuleType("uep_lyra_weapons.weapon_audio_dispatch_mixin");dispatch.tap_preset=lambda:None
spec=importlib.util.spec_from_file_location("uep_lyra_weapons._early_policy_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_audio_early_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":world,"uep_lyra_abilities.melee_trace_mixin":trace,"uep_lyra_weapons.weapon_audio_dispatch_mixin":dispatch}):spec.loader.exec_module(policy)


def f32(value):return struct.unpack("<f",struct.pack("<f",value))[0]
class Object:
    def __init__(self,**values):self.values=values
    def get_property(self,name):return self.values.get(name)
    def call_function(self,name,*args):return self.values.get(name)


class TestWeaponAudioEarlyMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.queries=[];self.taps=[];self.platform="Windows";self.ids=list(range(20,28));self.router=types.SimpleNamespace()
        self.actor=Object(K2_GetActorLocation=(100.,200.,300.));self.pawn=Object(K2_GetActorLocation=(100.,200.,300.));self.camera=Object(GetCameraLocation=(10.,20.,30.),GetCameraRotation=(0.,0.,0.))
        self.payload=dict(Location=(400.,500.,600.),Normal=(0.,-1.,0.),PhysicalMaterial=Object(SurfaceType=0))
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.backend));native.load_class=native.find_class
        native.FVector=lambda:(0.,0.,0.);native.FLinearColor=lambda *args:args;policy.tap_preset=lambda:types.SimpleNamespace(call_function=lambda name:(self.ids,))
    def backend(self,name,*args,**kwargs):
        self.calls.append((name,args,kwargs))
        if name=="GetPlatformName":return self.platform
        if name=="EqualEqual_StriStri":return args[0].casefold()==args[1].casefold()
        if name=="GetPlayerCameraManager":return self.camera
        if name=="GetPlayerPawn":return self.pawn
        if name=="BreakGameplayCueParameters":return self.payload
        if name=="Conv_DoubleToFloat":return f32(args[0])
        if name=="Subtract_VectorVector":return tuple(a-b for a,b in zip(*args))
        if name=="Add_VectorVector":return tuple(a+b for a,b in zip(*args))
        if name=="Multiply_VectorVector":return tuple(a*b for a,b in zip(*args))
        if name=="Conv_DoubleToVector":return (args[0],)*3
        if name=="VSize":return math.sqrt(sum(v*v for v in args[0]))
        if name=="Conv_VectorToRotator":return args[0]
        if name=="GetUpVector":return (0.,0.,1.)
        if name=="Normal":
            size=math.sqrt(sum(v*v for v in args[0]));return tuple(v/size for v in args[0]) if size*size>args[1] else (0.,0.,0.)
        if name=="GetSideReflectionAngles":return (tuple(v+1. for v in args[0]),tuple(v-1. for v in args[0]))
        if name=="LineTraceSingle":
            self.queries.append(kwargs);index=len(self.queries);return (index%2==0,dict(Location=(index*10.,index*20.,index*30.),Normal=(1.,0.,0.),Distance=index*10.125))
        if name=="Calculate Tap Properties":self.taps.append(args)
    def run_schedule(self,target=None):return policy.schedule(self.router,self.actor if target is None else target,"cue","world")
    def test_seven_native_queries_eight_taps_preserve_nonsequential_id_order(self):
        self.assertFalse(self.run_schedule());self.assertEqual(len(self.queries),7);self.assertEqual([args[3] for args in self.taps],[20,21,24,25,22,23,26,27])
        self.assertEqual(policy.evidence(self.router)["queries"],7);self.assertEqual(policy.evidence(self.router)["taps"],8)
    def test_only_first_side_rays_ignore_target_and_all_use_authored_query_defaults(self):
        self.run_schedule();self.assertEqual([row["ActorsToIgnore"] for row in self.queries],[[],[],[],[],[],[self.actor],[self.actor]])
        for row in self.queries:self.assertEqual((row["TraceChannel"],row["bTraceComplex"],row["bIgnoreSelf"],row["DrawDebugType"],row["DrawTime"]),(0,False,True,0,2.))
    def test_first_side_listeners_stay_zero_while_other_taps_use_camera(self):
        self.run_schedule();self.assertEqual([args[7] for args in self.taps],[(10.,20.,30.)]*6+[(0.,0.,0.)]*2)
    def test_primary_hit_uses_material_validity_not_next_trace_result(self):
        self.run_schedule();self.assertTrue(self.taps[0][6]);self.assertFalse(self.taps[1][6])
        self.taps=[];self.queries=[];self.payload["PhysicalMaterial"]=None;self.run_schedule();self.assertFalse(self.taps[0][6])
    def test_distance_is_from_camera_and_float_narrows_before_secondary_travel(self):
        self.payload["Location"]=(16777217.125,3.,0.);self.camera.values["GetCameraLocation"]=(0.,0.,0.);self.run_schedule(self.pawn)
        distance=f32(math.sqrt(16777217.125**2+9.));self.assertEqual(self.taps[0][5],distance);self.assertEqual(self.taps[1][5],f32(distance+10.125))
    def test_foreign_strict_limit_and_local_bypass(self):
        self.camera.values["GetCameraLocation"]=(0.,0.,0.);self.payload["Location"]=(0.,4000.,0.);self.run_schedule();self.assertEqual(self.taps,[])
        self.run_schedule(self.pawn);self.assertEqual(len(self.taps),8)
    def test_flesh_null_target_and_unsupported_platform_skip(self):
        self.payload["PhysicalMaterial"]=Object(SurfaceType=1);self.run_schedule();self.assertEqual(self.taps,[])
        self.payload["PhysicalMaterial"]=None;policy.schedule(self.router,None,"cue","world");self.assertEqual(self.taps,[])
        self.platform="Android";self.run_schedule();self.assertEqual(self.queries,[])
    def test_missing_camera_is_authored_noop_and_short_preset_retains_vm_diagnostics(self):
        camera=self.camera;self.camera=None;self.assertFalse(self.run_schedule());self.camera=camera;self.ids=[20];self.assertTrue(self.run_schedule());self.assertEqual(self.taps,[])
    def test_named_fallback_only_selects_original(self):
        self.assertEqual(policy.LyraWeaponAudioEarlyBlueprintFallbackProfile.Early(self.router,None,None,None),dict(UseOriginal=True));self.assertEqual(self.calls,[])
        self.assertTrue(policy.LyraWeaponAudioEarlyPythonProfile.Early.uep_named_outputs);self.assertEqual(policy.LyraWeaponAudioEarlyPythonProfile.Early.override,policy.METHOD)
