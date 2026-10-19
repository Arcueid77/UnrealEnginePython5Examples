"""WhizBy gates and original native audio configuration/order contracts."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");world=types.ModuleType("uep_lyra_world.effect_pad_mixin");world.valid=lambda value:value is not None
trace=types.ModuleType("uep_lyra_abilities.melee_trace_mixin");trace.native_outputs=lambda cls,method,value:value
spec=importlib.util.spec_from_file_location("_weapon_audio_whiz_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_audio_whiz_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":world,"uep_lyra_abilities.melee_trace_mixin":trace}):spec.loader.exec_module(policy)


class Object:
    def __init__(self,**fields):self.fields=fields;self.calls=[]
    def get_property(self,name):return self.fields.get(name)
    def call_function(self,name,*args):self.calls.append((name,args));return self.fields.get(name)


class TestWeaponAudioWhizMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.platform="Windows";self.pawn=Object();self.actor=Object(K2_GetActorLocation="fire-origin");self.cam=Object(GetCameraLocation="listener")
        self.attenuation=types.SimpleNamespace(StereoSpread=200.,KeepAuthored="unchanged")
        self.audio=Object(BP_GetAttenuationSettingsToApply=dict(ReturnValue=False,OutAttenuationSettings=self.attenuation));self.payload=dict(PhysicalMaterial=None,Location="impact")
        self.outputs=("closest",1234.5,True,12345.5);self.router=types.SimpleNamespace()
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.backend))
        native.load_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.backend))
        native.load_object=lambda cls,path:path;native.FRotator=lambda:"zero-rotation"
    def backend(self,name,*args,**kwargs):
        self.calls.append((name,args,kwargs))
        if name=="GetPlatformName":return self.platform
        if name=="EqualEqual_StriStri":return args[0].casefold()==args[1].casefold()
        if name=="GetPlayerPawn":return self.pawn
        if name=="GetPlayerCameraManager":return self.cam
        if name=="BreakGameplayCueParameters":return self.payload
        if name=="Calculate Whiz By":return self.outputs
        if name=="SpawnSoundAtLocation":return self.audio
    def run_schedule(self):return policy.schedule(self.router,self.actor,"cue-params","world")
    def test_platform_gate_is_native_case_insensitive_and_limits_supported_platforms(self):
        for platform in ("Windows","linux","Mac"):
            self.platform=platform;self.assertFalse(self.run_schedule());self.assertTrue(any(name=="SpawnSoundAtLocation" for name,_,_ in self.calls));self.calls=[]
        self.platform="Android";self.assertFalse(self.run_schedule());self.assertNotIn("GetPlayerPawn",[name for name,_,_ in self.calls])
    def test_local_null_actor_and_flesh_surface_skip_math_and_spawn(self):
        for actor in (self.pawn,None):
            self.calls=[];policy.schedule(self.router,actor,"cue","world");self.assertNotIn("Calculate Whiz By",[name for name,_,_ in self.calls])
        self.calls=[];self.payload["PhysicalMaterial"]=Object(SurfaceType=1);self.run_schedule();self.assertNotIn("SpawnSoundAtLocation",[name for name,_,_ in self.calls])
    def test_missing_local_pawn_exits(self):
        self.pawn=None;self.run_schedule();self.assertNotIn("Calculate Whiz By",[name for name,_,_ in self.calls])
    def test_invalid_camera_requests_original_vm_diagnostic_path(self):
        self.cam=None;self.assertTrue(self.run_schedule());self.assertNotIn("SpawnSoundAtLocation",[name for name,_,_ in self.calls])
    def test_existing_static_math_is_called_with_original_context_and_spread(self):
        self.run_schedule();row=next(row for row in self.calls if row[0]=="Calculate Whiz By")
        self.assertEqual(row[1],("listener","fire-origin",1000.,"impact",self.actor))
    def test_native_spawn_uses_original_sound_defaults_and_world_context(self):
        self.run_schedule();row=next(row for row in self.calls if row[0]=="SpawnSoundAtLocation")
        self.assertEqual(row[2],dict(WorldContextObject="world",Sound=policy.SOUND,Location="closest",Rotation="zero-rotation",VolumeMultiplier=1.,PitchMultiplier=1.,StartTime=0.,AttenuationSettings=None,ConcurrencySettings=None,bAutoDestroy=True))
    def test_attenuation_getter_failure_still_preserves_other_fields_and_applies_spread(self):
        self.run_schedule();self.assertEqual(self.attenuation.StereoSpread,1234.5);self.assertEqual(self.attenuation.KeepAuthored,"unchanged")
        self.assertEqual([name for name,_ in self.audio.calls],["BP_GetAttenuationSettingsToApply","AdjustAttenuation","SetFloatParameter","SetFloatParameter","Play"])
    def test_unclamped_onset_and_right_side_parameters_precede_final_play(self):
        self.run_schedule();self.assertEqual(self.audio.calls[-3:],[("SetFloatParameter",("OnsetDelay",12345.5*.000010)),("SetFloatParameter",("SwapLR",1.)),("Play",(0.,))])
        self.audio.calls=[];self.outputs=("closest",1000.,False,0.);self.run_schedule();self.assertEqual(self.audio.calls[-2],("SetFloatParameter",("SwapLR",0.)))
    def test_disabled_audio_spawn_null_stops_before_attenuation_or_parameter_writes(self):
        self.audio=None;self.assertFalse(self.run_schedule());self.assertEqual(policy.evidence(self.router)["native_spawn_requests"],1);self.assertEqual(policy.evidence(self.router)["valid_components"],0)
    def test_named_void_profiles_select_python_or_retained_body(self):
        value=policy.LyraWeaponAudioWhizBlueprintFallbackProfile.Whiz(self.router,None,None,None);self.assertEqual(value,dict(UseOriginal=True));self.assertEqual(self.calls,[])
        for cls in (policy.LyraWeaponAudioWhizPythonProfile,policy.LyraWeaponAudioWhizBlueprintFallbackProfile):self.assertEqual(cls.Whiz.override,policy.METHOD);self.assertTrue(cls.Whiz.uep_named_outputs)
