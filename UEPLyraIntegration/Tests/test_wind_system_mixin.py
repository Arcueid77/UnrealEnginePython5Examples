"""Native stateful schedule, original lagging hit cycle and float/audio rules."""
import importlib.util
import math
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");world=types.ModuleType("uep_lyra_world.effect_pad_mixin");world.valid=lambda obj:obj is not None
trace=types.ModuleType("uep_lyra_abilities.melee_trace_mixin");trace.trace_outputs=lambda method,raw:raw;trace.break_hit=lambda hit:hit
spec=importlib.util.spec_from_file_location("_wind_system_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_audio/wind_system_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":world,"uep_lyra_abilities.melee_trace_mixin":trace}):spec.loader.exec_module(policy)


def f32(value):return struct.unpack("<f",struct.pack("<f",value))[0]
class Object:
    def __init__(self,**values):self.values=values;self.calls=[]
    def get_property(self,name):return self.values.get(name)
    def set_property(self,name,value):self.values[name]=value
    def call_function(self,name,*args):self.calls.append((name,args));return self.values.get(name)
    def call_mixin_original(self,name,*args):self.calls.append(("original:"+name,args))


class TestWindSystemMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.audio=Object();self.pawn=Object(K2_GetActorLocation=(10.,20.,30.),GetVelocity=(1550.,0.,0.));self.hit=True
        self.actor=Object(**{"sfx_Amb_Wind_lp_meta":self.audio,"PawnLoc":(10.,20.,30.),"TraceDistance":2000.,"Player":[self.pawn],"Hits":7,"Wind":.777,"Speed":.123,"IsExterior":True})
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.backend));native.FLinearColor=lambda *args:args
    def backend(self,name,*args,**kwargs):
        self.calls.append((name,args,kwargs))
        if name=="GetPlayerPawn":return self.pawn
        if name=="Conv_DoubleToFloat":return f32(args[0])
        if name=="VSize":return math.sqrt(sum(v*v for v in args[0]))
        if name=="MapRangeClamped":return max(0.,min(1.,(args[0]-args[1])/(args[2]-args[1])))
        if name=="MakeVector":return args
        if name=="Conv_DoubleToVector":return (args[0],)*3
        if name=="Multiply_VectorVector":return tuple(a*b for a,b in zip(*args))
        if name=="Add_VectorVector":return tuple(a+b for a,b in zip(*args))
        if name=="LineTraceSingle":return self.hit,dict(Distance=123.456789)
        if name=="SafeDivide":return args[0]/args[1] if args[1] else 0.
    def test_tick_leaves_array_write_to_original_native_entry(self):
        policy.tick(self.actor,9999.);self.assertEqual(self.actor.calls,[(policy.PLAYER_ENTRY,())]);self.assertEqual(self.actor.values["PawnLoc"],(10.,20.,30.));self.assertEqual(len(self.actor.values["Player"]),1)
    def test_invalid_audio_preserves_original_whole_event_path(self):
        self.actor.values["sfx_Amb_Wind_lp_meta"]=None;policy.tick(self.actor,.02);self.assertEqual(self.actor.calls,[("original:ReceiveTick",(.02,))])
    def test_missing_pawn_does_not_advance_native_schedule(self):
        self.pawn=None;policy.tick(self.actor,0.);self.assertEqual(self.actor.calls,[])
    def test_speed_map_and_interior_audio_do_not_overwrite_actor_wind(self):
        self.actor.values["IsExterior"]=False;self.assertFalse(policy.after_player(self.actor));self.assertEqual(self.actor.values["Speed"],.5);self.assertEqual(self.actor.values["Wind"],.777)
        self.assertEqual(self.audio.calls,[("SetFloatParameter",("PawnSpeed",.5)),("SetFloatParameter",("Wind",.5))])
    def test_exterior_delegates_progress_to_original_native_multigate(self):
        policy.after_player(self.actor);self.assertEqual(self.actor.calls,[(policy.SCHEDULE_ENTRY,())]);self.assertNotIn("stage_index",vars(self.actor))
    def test_stage_zero_uses_previous_hits_without_clamping_then_resets_before_trace(self):
        policy.stage(self.actor,0);self.assertEqual(self.actor.values["Wind"],f32(1.-7*.2));self.assertEqual(self.actor.values["Hits"],1)
        self.assertEqual(self.audio.calls[0],("SetFloatParameter",("Wind",f32(1.-7*.2))))
    def test_left_and_right_use_float_macro_distance_and_native_safe_divide(self):
        policy.stage(self.actor,1);self.assertEqual(self.audio.calls[-1],("SetFloatParameter",("Pan.L",f32(123.456789)/2000.)))
        self.actor.values["TraceDistance"]=0.;policy.stage(self.actor,2);self.assertEqual(self.audio.calls[-1],("SetFloatParameter",("Pan.R",0.)))
    def test_miss_uses_authored_distance_and_does_not_increment_hits(self):
        self.hit=False;policy.stage(self.actor,1);self.assertEqual(self.actor.values["Hits"],7);self.assertEqual(self.audio.calls[-1],("SetFloatParameter",("Pan.L",1.)))
        query=next(kwargs for name,args,kwargs in self.calls if name=="LineTraceSingle");self.assertEqual(query["ActorsToIgnore"],[self.pawn]);self.assertFalse(query["bTraceComplex"]);self.assertEqual(query["DrawTime"],5.)
    def test_fallback_stage_only_observes_native_choice_and_preserves_body(self):
        self.assertTrue(policy.LyraWindBlueprintFallbackProfile.Stage(self.actor,3));self.assertEqual(policy.evidence(self.actor)["stages"],[3]);self.assertEqual(self.calls,[])
