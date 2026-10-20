"""Original owner branches,activation,unclamped math and zero diagnostics."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda obj:obj is not None
spec=importlib.util.spec_from_file_location('_replay_runtime_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/replay_runtime_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)
class ReplayRuntimePolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.owner=None;self.playing=False;self.props=dict(TimeScrubberWidget=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('progress',f,*a))));self.obj=types.SimpleNamespace(get_property=self.props.get,set_property=self.set,call_function=self.call);self.sub=types.SimpleNamespace(call_function=self.subcall);policy.ue=native;policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(n,f,a))
    def call(self,f,*args):
        self.calls.append(('object',f,*args))
        if f=='GetOwner':return self.owner
    def set(self,n,v):self.props[n]=v;self.calls.append(('set',n,v))
    def subcall(self,f,*args):
        self.calls.append(('sub',f,*args))
        if f=='IsPlaying':return self.playing
    def library(self,n,f,args):
        self.calls.append((n,f,*args))
        return 0. if f=='Divide_DoubleDouble' else self.sub
    def owner_type(self,replay=False):return types.SimpleNamespace(is_a=lambda n:n=='LyraPlayerController' or replay and n=='LyraReplayPlayerController',call_function=lambda f,*a:self.calls.append(('owner',f,*a)))
    def test_null_and_unrelated_owner_do_nothing(self):
        policy.invoke(self.obj,'handler','begin');self.owner=types.SimpleNamespace(is_a=lambda n:False);policy.invoke(self.obj,'handler','begin');self.assertEqual(self.calls,[('object','GetOwner'),('object','GetOwner')])
    def test_regular_lyra_controller_delegates_record_decision_to_native_controller(self):self.owner=self.owner_type();policy.invoke(self.obj,'handler','begin');self.assertEqual(self.calls[-1],('owner','TryToRecordClientReplay'))
    def test_replay_controller_without_playback_does_not_record_or_create_hud(self):self.owner=self.owner_type(True);policy.invoke(self.obj,'handler','begin');self.assertFalse(any(c[0] in ('owner','set') for c in self.calls))
    def test_playing_replay_controller_stored_before_native_widget_creation(self):self.owner=self.owner_type(True);self.playing=True;policy.invoke(self.obj,'handler','begin');self.assertEqual(self.calls[-2:],[('set','As Lyra Replay Player Controller',self.owner),('object',policy.NATIVE_CREATE)])
    def test_hud_construct_activates_native_widget(self):policy.invoke(self.obj,'hud','construct');self.assertEqual(self.calls,[('object','ActivateWidget')])
    def test_tick_uses_sampled_current_length_and_does_not_clamp(self):policy.invoke(self.obj,'scrub','tick',12.,8.);self.assertEqual(self.calls,[('progress','SetPercent',1.5)])
    def test_tick_zero_length_uses_original_native_warning_and_zero(self):policy.invoke(self.obj,'scrub','tick',1.,0.);self.assertEqual(self.calls,[('KismetMathLibrary','Divide_DoubleDouble',1.,0.),('progress','SetPercent',0.)])
    def test_seek_scales_unclamped_local_x_by_native_replay_length(self):policy.invoke(self.obj,'scrub','seek',20.,-25.,100.);self.assertEqual(self.calls[-1],('sub','SeekInActiveReplay',-5.))
    def test_seek_zero_width_preserves_native_diagnostic(self):policy.invoke(self.obj,'scrub','seek',20.,50.,0.);self.assertIn(('KismetMathLibrary','Divide_DoubleDouble',50.,0.),self.calls);self.assertEqual(self.calls[-1],('sub','SeekInActiveReplay',0.))
    def test_profiles_own_exact_typed_gates_and_no_geometry_pointer_reply(self):
        for kind,prefix in (('handler','Handler'),('hud','HUD'),('scrub','Scrub')):
            for p in ('Python','BlueprintFallback'):
                cls=getattr(policy,'LyraReplay'+prefix+p+'Profile');self.assertEqual({f.override for f in vars(cls).values() if callable(f)},set(policy.GATES[kind].values()));self.assertNotIn('OnMouseButtonDown_0',vars(cls))
