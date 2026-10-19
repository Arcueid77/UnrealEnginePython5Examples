"""Static orchestration keeps native state cast, manager lookup and exact warnings."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");world=types.ModuleType("uep_lyra_world.effect_pad_mixin");world.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location("_general_audio_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_audio/general_audio_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":world}):spec.loader.exec_module(policy)


class Object:
    def __init__(self,cls="Actor",manager=None):self.cls=cls;self.manager=manager;self.calls=[]
    def is_a(self,cls):return self.cls==cls
    def get_component_by_type(self,cls):self.calls.append(("lookup",cls));return self.manager
    def call_function(self,name,*args):self.calls.append((name,args))


class TestGeneralAudioMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.manager=Object();self.state=Object("LyraGameState",self.manager);self.router=types.SimpleNamespace()
        native.find_class=lambda name:name if name=="LyraGameState" else types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.backend));native.load_class=lambda path:path;native.FLinearColor=lambda *args:args
    def backend(self,name,*args):
        self.calls.append((name,args))
        if name=="GetGameState":return self.state
    def test_positive_and_negative_both_forward_once_without_changing_argument(self):
        for positive in (False,True):policy.stinger(self.router,positive,"world")
        self.assertEqual(self.manager.calls,[("Fire Stinger",(False,)),("Fire Stinger",(True,))]);self.assertEqual(policy.evidence(self.router)["manager_calls"],2)
    def test_wrong_native_game_state_has_distinct_source_screen_only_warning(self):
        self.state=Object("OtherState");policy.stinger(self.router,True,"world")
        self.assertEqual(self.calls[-1],("PrintString",("world","FireStinger: LyraGameState not valid.",True,False,(0.,.66,1.,1.),5.,"None")))
    def test_null_game_state_uses_same_cast_failure_branch(self):
        self.state=None;policy.stinger(self.router,False,"world");self.assertEqual(self.calls[-1][1][1],"FireStinger: LyraGameState not valid.")
    def test_missing_manager_uses_other_source_message(self):
        self.state.manager=None;policy.stinger(self.router,False,"world");self.assertEqual(self.calls[-1],("PrintString",("world","FireStinger: MusicManager not valid.",True,False,(0.,.66,1.,1.),5.,"None")))
    def test_python_profile_selects_typed_false_return_and_fallback_does_no_business(self):
        self.assertEqual(policy.LyraGeneralAudioPythonProfile.Fire(self.router,True,"world"),dict(UseOriginal=False));self.calls=[]
        self.assertEqual(policy.LyraGeneralAudioBlueprintFallbackProfile.Fire(self.router,False,"world"),dict(UseOriginal=True));self.assertEqual(self.calls,[])
    def test_only_ordinary_helper_named_method_is_registered(self):
        for cls in (policy.LyraGeneralAudioPythonProfile,policy.LyraGeneralAudioBlueprintFallbackProfile):self.assertEqual(cls.Fire.override,policy.METHOD);self.assertTrue(cls.Fire.uep_named_outputs)
