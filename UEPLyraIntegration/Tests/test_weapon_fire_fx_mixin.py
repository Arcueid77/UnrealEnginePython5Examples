"""Native cache/retrigger/parameter decisions independent of Niagara rendering."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");enums=types.ModuleType("unreal_engine.enums")
enums.EAttachLocation=types.SimpleNamespace(KeepRelativeOffset=0);enums.ENCPoolMethod=types.SimpleNamespace(**{"None":0})
enums.ERelativeTransformSpace=types.SimpleNamespace(RTS_Actor=1,RTS_World=0)
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda obj:obj is not None
trace=types.ModuleType("uep_lyra_abilities.melee_trace_mixin");trace.native_outputs=lambda cls,method,value:value
spec=importlib.util.spec_from_file_location("_weapon_fire_fx_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/weapon_fire_fx_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"unreal_engine.enums":enums,"uep_lyra_world.effect_pad_mixin":helpers,"uep_lyra_abilities.melee_trace_mixin":trace}):spec.loader.exec_module(policy)


class Component:
    def __init__(self,owner,active=True):self.owner,self.active=owner,active
    def call_function(self,method,*args):
        self.owner.calls.append(("component",method,args))
        return self.active if method=="IsActive" else None


class TestWeaponFireFXMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.new=None
        self.data={"DefaultSceneRoot":"root","Skeletal Mesh Component":None,"ImpactPositions":[(10.,0.,0.)],"Shell Eject Mesh":"mesh"}
        for flag,field,system,trigger,_ in policy.STAGES:self.data.update({flag:True,field:Component(self),system:system,trigger:False})
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=lambda *args:self.calls.append(("actor",args)))
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda method,*args,**kw:self.backend(method,args,kw)))
        native.FVector=lambda:(0.,0.,0.);native.FRotator=lambda *args:args
    def write(self,name,value):self.calls.append(("write",name,value));self.data[name]=value
    def backend(self,method,args,kw):
        self.calls.append((method,args,kw))
        if method=="SpawnSystemAttached":return self.new
        if method=="Subtract_VectorVector":return tuple(a-b for a,b in zip(*args))
        if method=="Normal":return args[0]
        return None
    def test_active_components_reused_without_native_spawn(self):policy.fire(self.actor);self.assertEqual(policy.evidence(self.actor)["reuses"],3);self.assertFalse(any(row[0]=="SpawnSystemAttached" for row in self.calls))
    def test_trigger_toggles_each_original_branch(self):policy.fire(self.actor);policy.fire(self.actor);self.assertTrue(all(self.data[trigger] is False for _,_,_,trigger,_ in policy.STAGES))
    def test_disabled_branch_preserves_cached_component_and_trigger(self):
        self.data["Enable Shell Eject"]=False;self.data["Shell Eject Trigger"]=True;old=self.data["NS_ShellEject"];policy.fire(self.actor)
        self.assertIs(self.data["NS_ShellEject"],old);self.assertIs(self.data["Shell Eject Trigger"],True)
    def test_inactive_valid_component_is_replaced(self):
        self.data["NS_ShellEject"].active=False;self.new=Component(self);policy.fire(self.actor);self.assertIs(self.data["NS_ShellEject"],self.new)
    def test_replacement_resets_old_trigger_before_toggle(self):
        self.data["NS_ShellEject"]=None;self.data["Shell Eject Trigger"]=True;self.new=Component(self);policy.fire(self.actor)
        self.assertEqual([row[2] for row in self.calls if row[:2]==("write","Shell Eject Trigger")],[False,True])
    def test_failed_spawn_still_preserves_native_bool_writes(self):
        self.data["NS_ShellEject"]=None;policy.fire(self.actor);self.assertIs(self.data["Shell Eject Trigger"],True);self.assertIsNone(self.data["NS_ShellEject"])
    def test_original_native_spawn_options(self):
        self.data["NS_ShellEject"]=None;policy.fire(self.actor);kw=next(row[2] for row in self.calls if row[0]=="SpawnSystemAttached")
        self.assertEqual((kw["AttachToComponent"],kw["Rotation"],kw["bAutoDestroy"],kw["bAutoActivate"],kw["bPreCullCheck"]),("root",(0.,0.,90.),True,True,True))
    def test_static_mesh_written_only_on_shell_creation(self):
        self.data["NS_ShellEject"]=None;self.new=Component(self);policy.fire(self.actor)
        self.assertIn(("component","SetVariableStaticMesh",("User.ShellEjectStaticMesh","mesh")),self.calls)
    def test_tracer_copies_current_native_impact_array(self):policy.fire(self.actor);self.assertTrue(any(row[0]=="SetNiagaraArrayVector" and row[1][1:]==("User.ImpactPositions",[(10.,0.,0.)]) for row in self.calls))
    def test_all_disabled_still_requests_original_delay(self):
        for flag,_,_,_,_ in policy.STAGES:self.data[flag]=False
        policy.fire(self.actor);self.assertEqual(self.calls,[("actor",(policy.DELAY,))])
    def test_cleanup_checks_validity_even_if_all_inactive(self):
        for _,field,_,_,_ in policy.STAGES:self.data[field].active=False
        policy.cleanup(self.actor);self.assertEqual(self.calls,[("actor",(policy.DELAY,))])
    def test_no_valid_components_destroys_without_new_timer(self):
        for _,field,_,_,_ in policy.STAGES:self.data[field]=None
        policy.cleanup(self.actor);self.assertEqual(self.calls,[("actor",("K2_DestroyActor",))])
    def test_fallback_preserves_native_latent_continuation(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args)
        policy.LyraWeaponFireFXBlueprintFallbackProfile.AfterDelay(self.actor);self.assertEqual(self.calls,[(policy.AFTER,)])
