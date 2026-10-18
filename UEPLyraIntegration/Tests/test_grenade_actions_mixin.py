"""Actor action policy models,not native teleport/physics/destroy acceptance."""
import importlib.util
import math
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

class Vec:
    def __init__(self,x=0.,y=0.,z=0.): self.x,self.y,self.z=x,y,z
native=types.ModuleType("unreal_engine");native.FVector=Vec
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
base=types.ModuleType("uep_lyra_weapons.grenade_cleanup_mixin")
class Base:
    def SetupVFX(self): pass
    def PostLaunchCleanup(self): pass
base.LyraGrenadeCleanupPythonProfile=Base;base.LyraGrenadeCleanupBlueprintFallbackProfile=Base
spec=importlib.util.spec_from_file_location("uep_lyra_weapons._grenade_actions_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_actions_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":helpers,"uep_lyra_weapons.grenade_cleanup_mixin":base}): spec.loader.exec_module(policy)


class Object:
    def __init__(self,**fields): self.fields=fields
    def get_property(self,name): return self.fields[name]
    def set_property(self,name,value): self.fields[name]=value


class TestGrenadeActionsMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.move=Object(Velocity=Vec(3.,4.,0.));self.move.call_function=lambda *args:self.calls.append(("move",args))
        self.trail=types.SimpleNamespace(call_function=lambda *args:self.calls.append(("trail",args)))
        self.actor=Object(ProjectileMovement=self.move,NS_Trail=self.trail,ConservedVelocity=-1.)
        self.actor.call_function=lambda *args,**kw:self.calls.append(("actor",args,kw));self.location=Vec(10.,20.,30.);self.forward=Vec(0.,2.,0.)
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=self.native_math))
    def native_math(self,name,*args):
        if name=="VSize": return math.sqrt(args[0].x**2+args[0].y**2+args[0].z**2)
        if name=="Divide_DoubleDouble": return args[0]/args[1]
        if name=="Multiply_VectorFloat": return Vec(args[0].x*args[1],args[0].y*args[1],args[0].z*args[1])
        self.fail(name)
    def test_conserved_speed_read_before_teleport(self): policy.teleport(self.actor,self.location,self.forward);self.assertEqual(self.actor.fields["ConservedVelocity"],5.)
    def test_original_halves_speed_and_does_not_normalize_forward(self):
        policy.teleport(self.actor,self.location,self.forward);value=self.move.fields["Velocity"];self.assertEqual((value.x,value.y,value.z),(0.,5.,0.))
    def test_zero_speed(self): self.move.fields["Velocity"]=Vec();policy.teleport(self.actor,self.location,self.forward);self.assertEqual(self.move.fields["Velocity"].y,0.)
    def test_native_location_options(self):
        policy.teleport(self.actor,self.location,self.forward);row=next(row for row in self.calls if row[0]=="actor" and row[1][0]=="K2_SetActorLocation")
        self.assertEqual(row[2],dict(NewLocation=self.location,bSweep=False,bTeleport=True))
    def test_native_order_deactivate_location_activate_vfx(self):
        policy.teleport(self.actor,self.location,self.forward);self.assertEqual([row[0] for row in self.calls],["trail","actor","move","actor"])
        self.assertEqual(self.calls[0][1],("Deactivate",));self.assertEqual(self.calls[2][1],("Activate",True));self.assertEqual(self.calls[-1][1],("Setup VFX",))
    def test_missing_trail_still_updates_conserved_speed_only(self):
        self.actor.fields["NS_Trail"]=None;policy.teleport(self.actor,self.location,self.forward);self.assertEqual(self.actor.fields["ConservedVelocity"],5.);self.assertEqual(self.calls,[])
    def test_missing_movement_zero_default_and_continues_vfx(self):
        self.actor.fields["ProjectileMovement"]=None;policy.teleport(self.actor,self.location,self.forward);self.assertEqual(self.actor.fields["ConservedVelocity"],0.);self.assertEqual(self.calls[-1][1],("Setup VFX",))
    def test_destroy_native_entry_once(self):
        policy.LyraGrenadeActionsPythonProfile.DestroyGrenade(self.actor,self.trail);self.assertEqual([row[1] for row in self.calls],[("K2_DestroyActor",)]);self.assertEqual(policy.evidence(self.actor)["native_destroy_calls"],1)
    def test_no_original_fallthrough_python(self):
        self.actor.call_mixin_original=lambda *args:self.fail("unexpected original");policy.LyraGrenadeActionsPythonProfile.TeleportGrenade(self.actor,self.location,self.forward)
    def test_fallback_teleport_arguments_once(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args);policy.LyraGrenadeActionsBlueprintFallbackProfile.TeleportGrenade(self.actor,self.location,self.forward)
        self.assertEqual(self.calls,[("Teleport Grenade",self.location,self.forward)])
    def test_fallback_destroy_once(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args);policy.LyraGrenadeActionsBlueprintFallbackProfile.DestroyGrenade(self.actor,self.trail);self.assertEqual(self.calls,[("Destroy Grenade",self.trail)])
    def test_unused_native_delegate_parameter_preserved(self):
        import inspect
        self.assertEqual(tuple(inspect.signature(policy.LyraGrenadeActionsPythonProfile.DestroyGrenade).parameters),("self","PSystem"))
    def test_existing_helpers_retained(self): self.assertIs(policy.LyraGrenadeActionsPythonProfile.PostLaunchCleanup,Base.PostLaunchCleanup);self.assertIs(policy.LyraGrenadeActionsPythonProfile.SetupVFX,Base.SetupVFX)
    def test_space_names_override(self): self.assertEqual(policy.LyraGrenadeActionsPythonProfile.TeleportGrenade.override,"Teleport Grenade");self.assertEqual(policy.LyraGrenadeActionsPythonProfile.DestroyGrenade.override,"Destroy Grenade")
