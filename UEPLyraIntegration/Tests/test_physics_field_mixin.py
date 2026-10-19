"""Exact super transports, material order, break state and inactive Tick policy."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._physics_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/physics_field_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)


class PhysicsPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.data={'TargetGlowAmt':1.,'CurrentGlowAmt':.75,'DynaMat1':'old-a','DynaMat2':'old-b'}
        self.component=types.SimpleNamespace(call_function=self.create);self.data['GeometryCollectionComponent']=self.component
        self.actor=types.SimpleNamespace(call_function=lambda *args:self.calls.append(('call',*args)),call_mixin_original=lambda *args:self.calls.append(('original',*args)),get_property=self.data.get,set_property=self.write)
    def create(self,*args):self.calls.append(('component',*args));return 'material-'+str(args[1])
    def write(self,k,v):self.data[k]=v;self.calls.append(('write',k,v))
    def test_construction_calls_exact_parent_transport(self):
        policy.LyraExamplePhysicsFieldPythonProfile.UserConstructionScript(self.actor);self.assertEqual(self.calls,[('call',policy.PARENTS['construction'])])
    def test_begin_calls_exact_parent_transport(self):
        policy.LyraExamplePhysicsFieldPythonProfile.ReceiveBeginPlay(self.actor);self.assertEqual(self.calls,[('call',policy.PARENTS['begin'])])
    def test_tick_forwards_exact_delta_without_new_clock(self):
        policy.LyraExamplePhysicsFieldPythonProfile.ReceiveTick(self.actor,.03125);self.assertEqual(self.calls,[('call',policy.PARENTS['tick'],.03125)]);self.assertEqual(policy.evidence(self.actor)['last_delta'],.03125)
    def test_negative_tick_delta_is_not_clamped(self):
        policy.LyraExamplePhysicsFieldPythonProfile.ReceiveTick(self.actor,-.25);self.assertEqual(self.calls[0][-1],-.25)
    def test_fallback_construction_uses_original_project_function(self):
        policy.LyraExamplePhysicsFieldBlueprintFallbackProfile.UserConstructionScript(self.actor);self.assertEqual(self.calls,[('original','UserConstructionScript')])
    def test_fallback_begin_uses_original(self):
        policy.LyraExamplePhysicsFieldBlueprintFallbackProfile.ReceiveBeginPlay(self.actor);self.assertEqual(self.calls,[('original','ReceiveBeginPlay')])
    def test_fallback_tick_preserves_delta(self):
        policy.LyraExamplePhysicsFieldBlueprintFallbackProfile.ReceiveTick(self.actor,.02);self.assertEqual(self.calls,[('original','ReceiveTick',.02)])
    def test_shatter_begin_enters_original_native_bind_once(self):
        policy.LyraShatterSpherePythonProfile.ReceiveBeginPlay(self.actor);self.assertEqual(self.calls,[('call',policy.BIND)])
    def test_native_bind_gate_initializes_slots_in_original_order(self):
        self.assertIs(policy.materials(self.actor),False);self.assertEqual(self.calls,[('component','CreateDynamicMaterialInstance',0,None,'None'),('write','DynaMat1','material-0'),('component','CreateDynamicMaterialInstance',1,None,'None'),('write','DynaMat2','material-1')])
    def test_material_creation_null_result_is_stored_and_second_slot_still_created(self):
        self.component.call_function=lambda *args:self.calls.append(args) or None;policy.materials(self.actor);self.assertIsNone(self.data['DynaMat1']);self.assertIsNone(self.data['DynaMat2']);self.assertEqual(len(self.calls),4)
    def test_missing_component_returns_to_original_native_diagnostic_graph(self):
        self.data['GeometryCollectionComponent']=None;self.assertIs(policy.materials(self.actor),True);self.assertEqual(self.calls,[])
    def test_break_ignores_payload_and_only_sets_target_zero(self):
        policy.LyraShatterSpherePythonProfile.SphereIsBroken(self.actor,object());self.assertEqual(self.calls,[('write','TargetGlowAmt',0.)]);self.assertEqual(self.data['CurrentGlowAmt'],.75)
    def test_break_does_not_touch_material_references(self):
        policy.LyraShatterSpherePythonProfile.SphereIsBroken(self.actor,object());self.assertEqual((self.data['DynaMat1'],self.data['DynaMat2']),('old-a','old-b'))
    def test_repeated_break_has_same_source_assignment(self):
        for _ in range(2):policy.LyraShatterSpherePythonProfile.SphereIsBroken(self.actor,object())
        self.assertEqual(self.calls,[('write','TargetGlowAmt',0.)]*2)
    def test_shatter_profile_does_not_activate_disconnected_tick(self):
        for cls in (policy.LyraShatterSpherePythonProfile,policy.LyraShatterSphereBlueprintFallbackProfile):self.assertNotIn('ReceiveTick',vars(cls))
    def test_fallback_after_bind_returns_to_original_material_pipeline(self):self.assertIs(policy.LyraShatterSphereBlueprintFallbackProfile.AfterBind(self.actor),True);self.assertEqual(self.calls,[])
    def test_fallback_break_forwards_original_typed_payload(self):
        payload=object();policy.LyraShatterSphereBlueprintFallbackProfile.SphereIsBroken(self.actor,payload);self.assertEqual(self.calls,[('original','SphereIsBroken',payload)])
