"""Timer callback policy models,not native timer/physics acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");native.find_class=lambda name:name
helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
vfx=types.ModuleType("uep_lyra_weapons.grenade_vfx_mixin")
class Vfx:
    def SetupVFX(self): pass
vfx.LyraGrenadeVFXPythonProfile=Vfx;vfx.LyraGrenadeVFXBlueprintFallbackProfile=Vfx
spec=importlib.util.spec_from_file_location("uep_lyra_weapons._grenade_cleanup_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_cleanup_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":helpers,"uep_lyra_weapons.grenade_vfx_mixin":vfx}): spec.loader.exec_module(policy)


class Object:
    def __init__(self,**fields): self.fields=fields
    def get_property(self,name): return self.fields[name]


class TestGrenadeCleanupMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.capsule=types.SimpleNamespace(call_function=lambda *args:self.calls.append(("capsule",args)))
        self.mesh=types.SimpleNamespace(call_function=lambda *args:self.calls.append(("mesh",args)))
        self.movement=types.SimpleNamespace(set_property=lambda *args:self.calls.append(("rotation",args)))
        self.pawn=Object(CapsuleComponent=self.capsule);self.pawn.is_a=lambda cls:True
        self.actor=Object(Instigator=self.pawn,Mesh=self.mesh,ProjectileMovement=self.movement)
    def test_character_capsule_then_mesh_then_rotation(self):
        policy.cleanup(self.actor);self.assertEqual([row[0] for row in self.calls],["capsule","mesh","rotation"])
        self.assertEqual(self.calls[0][1],("IgnoreActorWhenMoving",self.actor,False));self.assertEqual(self.calls[1][1],("IgnoreActorWhenMoving",self.pawn,False))
    def test_native_rotation_flag_assignment(self): policy.cleanup(self.actor);self.assertEqual(self.calls[-1],("rotation",("bRotationFollowsVelocity",True)))
    def test_noncharacter_cast_failure_still_cleans_mesh_and_rotation(self):
        self.pawn.is_a=lambda cls:False;policy.cleanup(self.actor);self.assertEqual([row[0] for row in self.calls],["mesh","rotation"]);self.assertEqual(policy.evidence(self.actor)["non_character_skips"],1)
    def test_null_instigator_passed_to_native_mesh_noop(self):
        self.actor.fields["Instigator"]=None;policy.cleanup(self.actor);self.assertEqual(self.calls[0],("mesh",("IgnoreActorWhenMoving",None,False)))
    def test_missing_capsule_does_not_skip_other_native_operations(self):
        self.pawn.fields["CapsuleComponent"]=None;policy.cleanup(self.actor);self.assertEqual([row[0] for row in self.calls],["mesh","rotation"])
    def test_missing_mesh_still_restores_rotation(self): self.actor.fields["Mesh"]=None;policy.cleanup(self.actor);self.assertEqual(policy.evidence(self.actor)["rotation_writes"],1)
    def test_missing_movement_keeps_collision_steps(self): self.actor.fields["ProjectileMovement"]=None;policy.cleanup(self.actor);self.assertEqual([row[0] for row in self.calls],["capsule","mesh"])
    def test_no_original_fallthrough_python(self):
        self.actor.call_mixin_original=lambda *args:self.fail("unexpected original fallback");policy.LyraGrenadeCleanupPythonProfile.PostLaunchCleanup(self.actor)
    def test_fallback_calls_original_once(self):
        self.actor.call_mixin_original=lambda *args:self.calls.append(args);policy.LyraGrenadeCleanupBlueprintFallbackProfile.PostLaunchCleanup(self.actor);self.assertEqual(self.calls,[("PostLaunchCleanup",)])
    def test_vfx_alias_retained_both_profiles(self):
        self.assertIs(policy.LyraGrenadeCleanupPythonProfile.SetupVFX,Vfx.SetupVFX);self.assertIs(policy.LyraGrenadeCleanupBlueprintFallbackProfile.SetupVFX,Vfx.SetupVFX)
    def test_policy_does_not_schedule_or_replay_native_timer(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_cleanup_mixin.py").read_text(encoding="utf-8")
        for value in ("add_ticker","K2_SetTimer","call_function(\"ReceiveBeginPlay\"","set_property(\"Velocity\""): self.assertNotIn(value,text)
