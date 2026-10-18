"""Isolated policy models,not native Niagara rendering/replication proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");enums=types.ModuleType("unreal_engine.enums")
enums.EAttachLocation=types.SimpleNamespace(KeepRelativeOffset=0);enums.ENCPoolMethod=types.SimpleNamespace(**{"None":0})
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location("_grenade_vfx_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_vfx_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.enums":enums,"uep_lyra_world.effect_pad_mixin":helpers}): spec.loader.exec_module(policy)


class Object:
    def __init__(self,**fields): self.fields=fields;self.calls=[]
    def get_property(self,name): return self.fields[name]
    def set_property(self,name,value): self.calls.append((name,value));self.fields[name]=value


class TestGrenadeVFXMixin(unittest.TestCase):
    def setUp(self):
        self.spawned=Object();self.spawned.call_function=lambda *args,**kw:self.calls.append(("parameter",args,kw))
        self.actor=Object(Mesh="mesh",Instigator="pawn",**{"NS_Trail":"old","Team Color":"old-color"})
        self.calls=[];self.team=(True,1);self.subsystem=types.SimpleNamespace(call_function=lambda *args:self.team)
        self.backend=types.SimpleNamespace(FVector=lambda: "zero-vector",FRotator=lambda:"zero-rotation",FLinearColor=lambda *args:args,
            load_object=lambda cls,path:path)
        def find(name):
            if name=="SubsystemBlueprintLibrary": return types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda *args:self.subsystem))
            return types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda method,**kw:self.spawn(method,kw)))
        self.backend.find_class=find
        item=patch.object(policy,"ue",self.backend);item.start();self.addCleanup(item.stop)
    def spawn(self,method,kwargs): self.calls.append(("spawn",method,kwargs));return self.spawned
    def test_red_only_team_one(self): policy.setup(self.actor);self.assertEqual(self.actor.fields["Team Color"],(1.,.05,.01,1.))
    def test_team_zero_blue(self): self.team=(True,0);policy.setup(self.actor);self.assertEqual(self.actor.fields["Team Color"],(.01,.15,1.,1.))
    def test_missing_team_blue(self): self.team=(False,-1);policy.setup(self.actor);self.assertEqual(self.actor.fields["Team Color"],(.01,.15,1.,1.))
    def test_bool_output_not_branch_condition(self): self.team=(False,1);policy.setup(self.actor);self.assertEqual(policy.evidence(self.actor)["red_choices"],1)
    def test_invalid_spawn_does_not_write_old_reference_or_color(self):
        self.spawned=None;policy.setup(self.actor);self.assertEqual(self.actor.fields["NS_Trail"],"old");self.assertEqual(self.actor.fields["Team Color"],"old-color");self.assertEqual(self.actor.calls,[])
    def test_missing_subsystem_native_default_blue(self): self.subsystem=None;policy.setup(self.actor);self.assertEqual(policy.evidence(self.actor)["missing_team_subsystem_defaults"],1);self.assertEqual(policy.evidence(self.actor)["blue_choices"],1)
    def test_actual_native_attached_spawn_options(self):
        policy.setup(self.actor);options=self.calls[0][2];self.assertEqual(options["SystemTemplate"],policy.TRAIL);self.assertEqual(options["AttachToComponent"],"mesh")
        self.assertEqual((options["AttachPointName"],options["LocationType"],options["bAutoDestroy"],options["bAutoActivate"],options["PoolingMethod"],options["bPreCullCheck"]),("None",0,False,True,0,True))
    def test_native_parameter_name_and_color(self): policy.setup(self.actor);self.assertEqual(self.calls[-1][1],("SetVariableLinearColor","Team_Color",(1.,.05,.01,1.)))
    def test_original_space_name_override(self): self.assertEqual(policy.LyraGrenadeVFXPythonProfile.SetupVFX.override,"Setup VFX")
    def test_fallback_original_once(self):
        self.actor.call_mixin_original=lambda name:self.calls.append(name);policy.LyraGrenadeVFXBlueprintFallbackProfile.SetupVFX(self.actor)
        self.assertEqual(self.calls,["Setup VFX"]);self.assertEqual(policy.evidence(self.actor)["fallback_calls"],1)
    def test_native_out_shape_guard(self):
        self.team=1
        with self.assertRaises(RuntimeError): policy.setup(self.actor)
    def test_native_out_order_guard(self):
        self.team=(1,True)
        with self.assertRaises(RuntimeError): policy.setup(self.actor)
