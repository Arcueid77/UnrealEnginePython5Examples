"""Child gates only decide continuation, menu and native team comparison."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");world=types.ModuleType("uep_lyra_world.effect_pad_mixin");world.valid=lambda obj:obj is not None
controls=types.ModuleType("uep_lyra_audio.music_manager_mixin");life=types.ModuleType("uep_lyra_audio.music_manager_lifecycle_mixin")
life.METHODS=tuple(str(i) for i in range(8))
def noop(*args):pass
names=("SetIsMenu","Death","Fire","Stinger","ReceiveTick","ReceiveBeginPlay","EliminationMessage","DamageMessage")
life.LyraMusicLifecyclePythonProfile=type("BasePython",(),{name:noop for name in names});life.LyraMusicLifecycleBlueprintFallbackProfile=type("BaseFallback",(),{name:noop for name in names})
spec=importlib.util.spec_from_file_location("uep_lyra_audio._music_family_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_audio/music_family_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":world,"uep_lyra_audio.music_manager_mixin":controls,"uep_lyra_audio.music_manager_lifecycle_mixin":life}):spec.loader.exec_module(policy)


class Object:
    def __init__(self):self.calls=[]
    def call_function(self,name,*args):self.calls.append((name,args))


class TestMusicFamilyMixin(unittest.TestCase):
    def setUp(self):
        self.component=Object();self.calls=[];self.team=1;self.part=True;self.teams=types.SimpleNamespace(call_function=lambda name,pawn:(self.part,self.team))
        controls.lib=lambda name:types.SimpleNamespace(call_function=self.backend);native.find_class=lambda name:name
    def backend(self,name,*args):
        self.calls.append((name,args))
        if name=="GetWorldSubsystem":return self.teams
        if name=="GetPlayerPawn":return "native-first-pawn"
    def test_start_calls_only_retained_native_delay_and_suppresses_original_fallthrough(self):
        self.assertFalse(policy.start(self.component));self.assertEqual(self.component.calls,[(policy.DELAY_ENTRY,())])
    def test_after_menu_precedes_original_cp_listener_start(self):
        self.assertFalse(policy.after(self.component,False,True));self.assertEqual(self.component.calls,[("SetIsMenu",(False,)),(policy.CP_ENTRY,())])
    def test_front_end_has_menu_true_and_no_capture_listener(self):
        policy.after(self.component,True,False);self.assertEqual(self.component.calls,[("SetIsMenu",(True,))])
    def test_capture_compares_native_team_even_when_part_flag_false(self):
        self.part=False;self.team=0;self.assertFalse(policy.captured(self.component,0));self.assertEqual(self.component.calls,[("Fire Stinger",(True,))])
    def test_capture_other_team_does_not_filter_or_skip_negative_stinger(self):
        policy.captured(self.component,2);self.assertEqual(self.component.calls,[("Fire Stinger",(False,))])
    def test_missing_native_team_subsystem_retains_original_diagnostic_path(self):
        self.teams=None;self.assertTrue(policy.captured(self.component,0));self.assertEqual(self.component.calls,[])
    def test_base_owned_complete_family_exposes_all_inherited_methods(self):
        self.assertEqual(len(policy.METHODS),11)
        for cls in (policy.LyraMusicFamilyPythonProfile,policy.LyraMusicFamilyBlueprintFallbackProfile):self.assertTrue(all(name in vars(cls) for name in (*names,"StartChild","AfterChild","Captured")))
    def test_fallback_gates_do_not_start_new_delay_or_listener(self):
        self.assertTrue(policy.LyraMusicFamilyBlueprintFallbackProfile.StartChild(self.component));self.assertTrue(policy.LyraMusicFamilyBlueprintFallbackProfile.AfterChild(self.component,False,True));self.assertEqual(self.component.calls,[])
