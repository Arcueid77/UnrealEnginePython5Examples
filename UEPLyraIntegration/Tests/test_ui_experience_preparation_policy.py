"""Shared pure class-cast semantics and setter-before-continuation order."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location('_ui_experience_preparation_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/experience_preparation_policy.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)
class UIExperiencePreparationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.sub=types.SimpleNamespace(call_function=lambda fn,*args:self.calls.append(('subsystem',fn,*args)));self.w=types.SimpleNamespace(call_function=lambda fn,*args:self.calls.append(('widget',fn,*args)));policy.ue=native;policy.lib=lambda n:types.SimpleNamespace(call_function=lambda fn,*args:self.lookup(n,fn,args))
    def lookup(self,name,fn,args):self.calls.append((name,fn,*args));return self.sub
    def test_valid_user_widget_class_is_set_before_original_continuation(self):
        cls=types.SimpleNamespace(is_child_of=lambda parent:parent=='UserWidget');policy.finish(self.w,cls);self.assertEqual(self.calls[-2:],[('subsystem','SetLoadingScreenContentWidget',cls),('widget',policy.AFTER)])
    def test_null_class_clears_loading_widget_and_still_continues(self):policy.finish(self.w,None);self.assertEqual(self.calls[-2:],[('subsystem','SetLoadingScreenContentWidget',None),('widget',policy.AFTER)])
    def test_wrong_class_clears_loading_widget_and_still_continues(self):policy.finish(self.w,types.SimpleNamespace(is_child_of=lambda parent:False));self.assertEqual(self.calls[-2:],[('subsystem','SetLoadingScreenContentWidget',None),('widget',policy.AFTER)])
    def test_owning_widget_is_the_original_subsystem_world_context(self):
        policy.finish(self.w,None);self.assertEqual(self.calls[0],('SubsystemBlueprintLibrary','GetGameInstanceSubsystem',self.w,'LyraLoadingScreenSubsystem'))
    def test_no_synchronous_asset_load_or_replacement_clock(self):
        policy.finish(self.w,None);self.assertEqual(len(self.calls),3);self.assertEqual(self.calls[1][1],'SetLoadingScreenContentWidget')
