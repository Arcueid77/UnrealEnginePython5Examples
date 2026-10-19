"""Relative construction, exact Niagara names and native helper delegation."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
helpers=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');helpers.lib=lambda n:None
spec=importlib.util.spec_from_file_location('uep_lyra_world._control_point_helpers_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/control_point_helpers_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':helpers}):spec.loader.exec_module(policy)


def vector(x,y,z):return types.SimpleNamespace(x=x,y=y,z=z)


class HelpersPolicyTests(unittest.TestCase):
    def setUp(self):
        self.log=[];self.scale=vector(1,1,1);self.active=False;self.data=dict(AreaScale=vector(20.,40.,6.),TimeRequiredForCapture=3.,OwnerTeamID=2)
        self.cube=types.SimpleNamespace(call_function=self.cube_call,get_property=lambda n:self.scale);self.fx=types.SimpleNamespace(call_function=lambda *a:self.log.append(('fx',*a)));self.counter=types.SimpleNamespace(call_function=self.counter_call);self.scoring=types.SimpleNamespace(call_function=lambda *a:self.log.append(('scoring',*a)));self.data.update(Cube=self.cube,NS_CapturePoint=self.fx,NS_CapturePointCounter=self.counter,ControlPointGameMode=self.scoring)
        self.actor=types.SimpleNamespace(get_property=self.data.get);policy.lib=lambda n:types.SimpleNamespace(call_function=self.math)
    def cube_call(self,fn,*args,**kw):
        self.log.append(('cube',fn,args,kw))
        if fn=='SetRelativeScale3D':self.scale=args[0]
    def counter_call(self,fn,*args):
        self.log.append(('counter',fn,*args))
        if fn=='IsActive':return self.active
    def math(self,fn,*args):
        if fn=='Divide_VectorFloat':v,s=args;return vector(v.x/s,v.y/s,v.z/s)
        if fn=='Multiply_VectorFloat':v,s=args;return vector(v.x*s,v.y*s,v.z*s)
        if fn=='Multiply_DoubleDouble':return args[0]*args[1]
        if fn=='Add_DoubleDouble':return args[0]+args[1]
        if fn in ('MakeVector','MakeVector4'):return args
    def test_construct_sets_relative_scale_before_reading_relative_height(self):
        self.assertIs(policy.construct(self.actor),False);self.assertEqual((self.scale.x,self.scale.y,self.scale.z),(2.,4.,.6));self.assertEqual(self.log[1][3]['NewLocation'],(0.,0.,31.))
    def test_sides_offset_uses_positive_xy_then_negative_xy(self):
        policy.construct(self.actor);self.assertIn(('fx','SetVariableVec4','SidesOffset',(100.,200.,-100.,-200.)),self.log)
    def test_counter_parameter_names_and_order_are_exact(self):
        policy.construct(self.actor);self.assertEqual(self.log[-2:],[('counter','SetVariableFloat','RibbonProgression',0.),('counter','SetVariableFloat','LifeTime',3.)])
    def test_negative_scale_is_preserved(self):
        self.data['AreaScale']=vector(-20.,10.,-4.);policy.construct(self.actor);self.assertEqual(self.log[1][3]['NewLocation'],(0.,0.,-19.));self.assertIn(('fx','SetVariableVec4','SidesOffset',(-100.,50.,100.,-50.)),self.log)
    def test_zero_scale_is_not_clamped(self):
        self.data['AreaScale']=vector(0.,0.,0.);policy.construct(self.actor);self.assertEqual(self.log[1][3]['NewLocation'],(0.,0.,1.))
    def test_missing_component_keeps_original_diagnostic_pipeline_before_partial_writes(self):
        self.data['NS_CapturePoint']=None;self.assertIs(policy.construct(self.actor),True);self.assertEqual(self.log,[])
    def test_relative_location_keeps_native_sweep_and_teleport_false(self):
        policy.construct(self.actor);self.assertEqual((self.log[1][3]['bSweep'],self.log[1][3]['bTeleport']),(False,False))
    def test_inactive_counter_is_activated_with_reset_true(self):
        self.assertIs(policy.check(self.actor),False);self.assertEqual(self.log,[('counter','IsActive'),('counter','Activate',True)])
    def test_active_counter_is_not_restarted(self):
        self.active=True;policy.check(self.actor);self.assertEqual(self.log,[('counter','IsActive')])
    def test_missing_counter_returns_to_original_native_diagnostic(self):
        self.data['NS_CapturePointCounter']=None;self.assertIs(policy.check(self.actor),True)
    def test_contested_delegates_same_actor_to_scoring(self):
        self.assertIs(policy.mark(self.actor,False),False);self.assertEqual(self.log,[('scoring','ContestPoint',self.actor)])
    def test_recaptured_passes_current_owner_team_without_reinterpreting(self):
        self.data['OwnerTeamID']=-7;policy.mark(self.actor,True);self.assertEqual(self.log,[('scoring','RecapturePointByTeam',self.actor,-7)])
    def test_missing_scoring_receiver_keeps_original_diagnostic(self):
        self.data['ControlPointGameMode']=None;self.assertIs(policy.mark(self.actor,True),True);self.assertEqual(self.log,[])
    def test_all_fallback_gates_keep_original_business(self):
        for name in ('Construct','Check','Contest','Recapture'):self.assertIs(getattr(policy.LyraControlPointHelpersBlueprintFallbackProfile,name)(self.actor),True)
        self.assertEqual(self.log,[])
