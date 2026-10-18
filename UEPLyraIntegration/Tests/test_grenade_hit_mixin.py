"""Hit policy/unused reflected input models,not native collision/audio proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
base=types.ModuleType("uep_lyra_weapons.grenade_begin_mixin")
class Begin:
    def SetupVFX(self): pass
    def PostLaunchCleanup(self): pass
    def TeleportGrenade(self,a,b): pass
    def DestroyGrenade(self,component): pass
    def ReceiveBeginPlay(self): pass
base.LyraGrenadeBeginPythonProfile=Begin;base.LyraGrenadeBeginBlueprintFallbackProfile=Begin
spec=importlib.util.spec_from_file_location("uep_lyra_weapons._grenade_hit_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_hit_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":helpers,"uep_lyra_weapons.grenade_begin_mixin":base}): spec.loader.exec_module(policy)


class TestGrenadeHitMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.comparison=1;self.handle=object();self.old=object();self.instigator="instigator";self.world="world";self.other="other";self.location="location"
        self.actor=types.SimpleNamespace(get_world=lambda:self.world,get_property=lambda name:self.old if name=="Timer" else self.instigator,
            set_property=lambda *args:self.calls.append(("write",args)),call_function=lambda *args:self.calls.append(("rpc",args)))
        self.teams=types.SimpleNamespace(call_function=lambda *args:self.compare(args));self.clear=(self.handle,)
        native.FRotator=lambda:"zero-rotation";native.load_object=lambda cls,path:path
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda *args,**kw:self.backend(name,args,kw)))
    def compare(self,args): self.calls.append(("compare",args));return self.comparison,2,1
    def backend(self,cls,args,kwargs):
        if cls=="SubsystemBlueprintLibrary": return self.teams
        if cls=="KismetSystemLibrary": self.calls.append(("clear",args));return self.clear
        if cls=="GameplayStatics": self.calls.append(("sound",args,kwargs));return None
        self.fail(cls)
    def run_hit(self): policy.hit(self.actor,self.other,self.location)
    def test_original_order_compare_clear_write_rpc_sound(self): self.run_hit();self.assertEqual([row[0] for row in self.calls],["compare","clear","write","rpc","sound"])
    def test_compare_other_against_instigator_not_reverse(self): self.run_hit();self.assertEqual(self.calls[0][1],("CompareTeams",self.other,self.instigator))
    def test_same_team_only_sound(self): self.comparison=0;self.run_hit();self.assertEqual([row[0] for row in self.calls],["compare","sound"])
    def test_invalid_team_only_sound(self): self.comparison=2;self.run_hit();self.assertEqual(policy.evidence(self.actor)["native_detonate_requests"],0)
    def test_missing_subsystem_default_same_branch(self): self.teams=None;self.run_hit();self.assertEqual(policy.evidence(self.actor)["invalid_team_subsystem_defaults"],1);self.assertEqual(self.calls[0][0],"sound")
    def test_native_clear_ref_output_written(self): self.run_hit();self.assertEqual(self.calls[2],("write",("Timer",self.handle)))
    def test_native_clear_shape_guard(self):
        self.clear=self.handle
        with self.assertRaises(RuntimeError): self.run_hit()
    def test_native_sound_uses_hit_location_and_original_options(self):
        self.run_hit();options=self.calls[-1][2]
        self.assertEqual((options["WorldContextObject"],options["Sound"],options["Location"]),(self.world,policy.SOUND,self.location))
        self.assertEqual((options["VolumeMultiplier"],options["PitchMultiplier"],options["StartTime"],options["bAutoDestroy"]),(1.,1.,0.,True));self.assertEqual(options["AttenuationSettings"],policy.ATTENUATION)
    def test_no_post_rpc_actor_property_access(self):
        def rpc(*args): self.calls.append(("rpc",args));self.actor.get_property=lambda *args:self.fail("destroyed Actor property accessed")
        self.actor.call_function=rpc;self.run_hit();self.assertEqual(self.calls[-1][0],"sound")
    def test_fallback_all_unused_reflected_inputs_preserved(self):
        values=tuple(object() for _ in range(8));self.actor.call_mixin_original=lambda *args:self.calls.append(args)
        policy.LyraGrenadeHitBlueprintFallbackProfile.ReceiveHit(self.actor,*values);self.assertEqual(self.calls,[("ReceiveHit",)+values])
    def test_signature_all_native_inputs(self):
        import inspect
        self.assertEqual(tuple(inspect.signature(policy.LyraGrenadeHitPythonProfile.ReceiveHit).parameters),("self","MyComp","Other","OtherComp","bSelfMoved","HitLocation","HitNormal","NormalImpulse","Hit"))
    def test_existing_aliases_retained(self): self.assertIs(policy.LyraGrenadeHitPythonProfile.ReceiveBeginPlay,Begin.ReceiveBeginPlay)
