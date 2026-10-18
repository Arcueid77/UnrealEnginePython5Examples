"""BeginPlay sequencing models; not native owner-bound timer acceptance."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType("unreal_engine");helpers=types.ModuleType("uep_lyra_world.effect_pad_mixin");helpers.valid=lambda value:value is not None
base=types.ModuleType("uep_lyra_weapons.grenade_actions_mixin")
class Actions:
    def SetupVFX(self): pass
    def PostLaunchCleanup(self): pass
    def TeleportGrenade(self,a,b): pass
    def DestroyGrenade(self,component): pass
base.LyraGrenadeActionsPythonProfile=Actions;base.LyraGrenadeActionsBlueprintFallbackProfile=Actions
spec=importlib.util.spec_from_file_location("uep_lyra_weapons._grenade_begin_model",Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_begin_mixin.py")
policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{"unreal_engine":native,"uep_lyra_world.effect_pad_mixin":helpers,"uep_lyra_weapons.grenade_actions_mixin":base}): spec.loader.exec_module(policy)


class Object:
    def __init__(self,**fields): self.fields=fields
    def get_property(self,name): return self.fields[name]
    def set_property(self,name,value): self.fields[name]=value


class TestGrenadeBeginMixin(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.handle=object();self.material=types.SimpleNamespace(call_function=lambda *args,**kw:self.calls.append(("material",args,kw)))
        self.capsule=types.SimpleNamespace(call_function=lambda *args:self.calls.append(("capsule",args)))
        self.mesh=types.SimpleNamespace(call_function=lambda *args:self.calls.append(("mesh",args)))
        self.pawn=Object(CapsuleComponent=self.capsule);self.pawn.is_a=lambda cls:True
        self.actor=Object(MaterialExplosion=self.material,Instigator=self.pawn,Mesh=self.mesh,TimeBeforeExplode=2.,Timer=None)
        self.actor.call_function=lambda *args:self.calls.append(("vfx",args))
        self.system=types.SimpleNamespace(call_function=lambda *args,**kw:self.timer(args,kw))
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:self.system) if name=="KismetSystemLibrary" else name
    def timer(self,args,kwargs): self.calls.append(("timer",args,kwargs));return self.handle
    def test_original_order(self): policy.begin(self.actor);self.assertEqual([row[0] for row in self.calls],["material","capsule","mesh","vfx","timer","timer"])
    def test_material_native_options(self):
        policy.begin(self.actor);self.assertEqual(self.calls[0][2],dict(OverrideForceMiplevelsToBeResident=True,bForceMiplevelsToBeResidentValue=True,ForceDuration=3.,CinematicTextureGroups=0,bFastResponse=True))
    def test_character_reverse_ignores(self): policy.begin(self.actor);self.assertEqual(self.calls[1][1],("IgnoreActorWhenMoving",self.actor,True));self.assertEqual(self.calls[2][1],("IgnoreActorWhenMoving",self.pawn,True))
    def test_noncharacter_skips_both_initial_ignores(self):
        self.pawn.is_a=lambda cls:False;policy.begin(self.actor);self.assertEqual([row[0] for row in self.calls],["material","vfx","timer","timer"])
    def test_null_instigator_still_vfx_and_timers(self): self.actor.fields["Instigator"]=None;policy.begin(self.actor);self.assertEqual(policy.evidence(self.actor)["cleanup_timers"],1)
    def test_invalid_material_keeps_other_work(self): self.actor.fields["MaterialExplosion"]=None;policy.begin(self.actor);self.assertEqual(policy.evidence(self.actor)["material_requests"],0);self.assertEqual(policy.evidence(self.actor)["detonate_timers"],1)
    def test_named_native_actor_timer_not_lambda(self):
        policy.begin(self.actor);timers=[row for row in self.calls if row[0]=="timer"]
        self.assertEqual([(row[2]["FunctionName"],row[2]["Time"]) for row in timers],[("Detonate",2.),("PostLaunchCleanup",.16)])
        self.assertTrue(all(row[2]["Object"] is self.actor and row[1]==("K2_SetTimer",) for row in timers))
    def test_native_timer_no_loop_delay_or_jitter(self):
        policy.begin(self.actor);timers=[row for row in self.calls if row[0]=="timer"]
        self.assertTrue(all(not row[2]["bLooping"] and not row[2]["bMaxOncePerFrame"] and row[2]["InitialStartDelay"]==row[2]["InitialStartDelayVariance"]==0. for row in timers))
    def test_real_returned_opaque_handle_stored(self): policy.begin(self.actor);self.assertIs(self.actor.fields["Timer"],self.handle)
    def test_fallback_once(self): self.actor.call_mixin_original=lambda *args:self.calls.append(args);policy.LyraGrenadeBeginBlueprintFallbackProfile.ReceiveBeginPlay(self.actor);self.assertEqual(self.calls,[("ReceiveBeginPlay",)])
    def test_existing_action_aliases_retained(self): self.assertIs(policy.LyraGrenadeBeginPythonProfile.TeleportGrenade,Actions.TeleportGrenade);self.assertIs(policy.LyraGrenadeBeginPythonProfile.PostLaunchCleanup,Actions.PostLaunchCleanup)
    def test_no_native_event_replay_or_ticker(self):
        text=(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_weapons/grenade_begin_mixin.py").read_text(encoding="utf-8")
        for value in ("add_ticker","lambda ","CreateDelegate","call_function(\"PostLaunchCleanup\"","call_function(\"Detonate\""): self.assertNotIn(value,text)
