"""Native rotation APIs, unclamped spread, float locals and typed branch choice."""
import importlib.util
import math
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine")
spec=importlib.util.spec_from_file_location("_weapon_audio_math_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_audio_math_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native}):spec.loader.exec_module(policy)
def f32(value):return struct.unpack("<f",struct.pack("<f",value))[0]


class TestWeaponAudioMathMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.backend))
    def backend(self,name,*args):
        self.calls.append((name,args))
        if name=="MakeVector":return args
        if name=="Conv_DoubleToVector":return (args[0],)*3
        if name=="RotateAngleAxis":return (1.,2.,3.) if args[1]>0. else (-1.,-2.,-3.)
        if name=="Multiply_VectorVector":return tuple(a*b for a,b in zip(*args))
        if name=="Add_VectorVector":return tuple(a+b for a,b in zip(*args))
        if name=="Subtract_VectorVector":return tuple(a-b for a,b in zip(*args))
        if name=="VSize":return math.sqrt(sum(v*v for v in args[0]))
        if name=="Normal":
            size=math.sqrt(sum(v*v for v in args[0]));return tuple(v/size for v in args[0]) if size*size>args[1] else (0.,0.,0.)
        if name=="FindClosestPointOnSegment":
            point,a,b=args;delta=tuple(v-u for u,v in zip(a,b));den=sum(v*v for v in delta);t=max(0.,min(1.,sum((v-u)*d for v,u,d in zip(point,a,delta))/den)) if den else 0.
            return tuple(u+t*d for u,d in zip(a,delta))
        if name=="Conv_DoubleToFloat":return f32(args[0])
        if name=="Conv_VectorToRotator":return args[0]
        if name=="GetRightVector":return (0.,1.,0.)
        if name=="Dot_VectorVector":return sum(a*b for a,b in zip(*args))
    def test_side_rotates_plus_then_minus45_and_keeps_axis_magnitude(self):
        result=policy.side((10.,20.,30.),(2.,3.,4.),2.,(0.,0.,2.));self.assertEqual(result,{"UseOriginal":False,"Angle L":(12.,24.,36.),"Angle R":(8.,16.,24.)})
        self.assertEqual([args for name,args in self.calls if name=="RotateAngleAxis"],[((2.,3.,4.),45.,(0.,0.,2.)),((2.,3.,4.),-45.,(0.,0.,2.))])
    def test_side_broadcasts_double_trace_distance_via_native_conversion(self):
        policy.side((0.,0.,0.),(1.,0.,0.),16777217.125,(0.,0.,1.));self.assertEqual(self.calls[0],("Conv_DoubleToVector",(16777217.125,)))
    def test_whiz_keeps_float_locals_even_with_double_outputs(self):
        minimum=f32(1000.1);value=policy.whiz((5.,1.,1.),(0.,0.,0.),minimum,(10.,0.,0.))
        self.assertEqual(value["StereoSpread"],f32(f32(math.sqrt(2.))+minimum));self.assertEqual(value["FiringDistance"],f32(math.sqrt(27.)))
        self.assertEqual([name for name,_ in self.calls].count("Conv_DoubleToFloat"),3)
    def test_whiz_zero_side_dot_uses_inclusive_less_equal(self):
        self.assertTrue(policy.whiz((5.,0.,0.),(0.,0.,0.),0.,(10.,0.,0.))["FromTheRight"])
    def test_whiz_side_sign_is_preserved(self):
        self.assertFalse(policy.whiz((5.,10.,0.),(0.,0.,0.),0.,(10.,0.,0.))["FromTheRight"])
        self.assertTrue(policy.whiz((5.,-10.,0.),(0.,0.,0.),0.,(10.,0.,0.))["FromTheRight"])
    def test_whiz_negative_minimum_is_not_clamped(self):
        self.assertEqual(policy.whiz((5.,1.,0.),(0.,0.,0.),-10.,(10.,0.,0.))["StereoSpread"],-9.)
    def test_whiz_closest_point_stays_on_segment(self):
        self.assertEqual(policy.whiz((20.,10.,0.),(0.,0.,0.),0.,(10.,0.,0.))["Location"],(10.,0.,0.))
    def test_degenerate_segment_keeps_native_zero_direction_behavior(self):
        self.assertEqual(policy.whiz((0.,0.,0.),(0.,0.,0.),0.,(0.,0.,0.))["Location"],(0.,0.,0.))
    def test_fallback_only_selects_retained_static_body_with_initialized_outputs(self):
        actor=types.SimpleNamespace();value=policy.LyraWeaponAudioMathBlueprintFallbackProfile.WhizBy(actor,None,None,0.,None,None)
        self.assertTrue(value["UseOriginal"]);self.assertEqual(value["StereoSpread"],0.);self.assertEqual([name for name,_ in self.calls],["MakeVector"])
    def test_two_router_methods_use_explicit_named_outputs(self):
        for cls in (policy.LyraWeaponAudioMathPythonProfile,policy.LyraWeaponAudioMathBlueprintFallbackProfile):
            self.assertEqual(cls.SideAngles.override,policy.SIDE);self.assertEqual(cls.WhizBy.override,policy.WHIZ);self.assertTrue(cls.SideAngles.uep_named_outputs and cls.WhizBy.uep_named_outputs)
