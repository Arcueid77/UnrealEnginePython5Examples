"""Typed source guards, first-effect selection, diagnostics and native audio ABI."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda value:value is not None
outputs=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');outputs.native_outputs=lambda cls,fn,value:value
helpers=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');helpers.lib=lambda name:None
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._small_burst_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/small_burst_cue_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':outputs,'uep_lyra_weapons.hero_burst_cue_mixin':helpers}):spec.loader.exec_module(policy)


class Item:
    def __init__(self,cls,calls=None):self.cls=cls;self.calls=[] if calls is None else calls;self.data={}
    def is_a(self,cls):return self.cls==cls
    def get_property(self,name):return self.data.get(name)
    def call_function(self,*args,**kw):self.calls.append((args,kw))


class SmallBurstPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.original=[];self.fx=Item('NiagaraComponent');self.second=Item('NiagaraComponent');self.spawner=Item(policy.SPAWNER);self.spawner.data['LightColor']='spawner-color';self.grenade=Item(policy.GRENADE);self.grenade.data['Team Color']='grenade-color'
        self.audio=Item('AudioComponent');self.cue=types.SimpleNamespace(call_mixin_original=lambda *args:self.original.append(args),get_property=lambda name:self.audio)
        self.params=object();self.results=types.SimpleNamespace(FxSystemComponents=[self.fx,self.second],AudioComponents=['different-audio'])
        native.find_class=lambda name:name;native.load_class=lambda name:types.SimpleNamespace(get_cdo=lambda:Item(name,self.calls)) if name==policy.AUDIO else name;native.FLinearColor=lambda *args:args
        policy.lib=lambda name:types.SimpleNamespace(call_function=lambda fn,*args,**kw:self.backend(fn,args,kw))
    def backend(self,fn,args,kw):
        self.calls.append((fn,args,kw))
        if fn=='BreakGameplayCueParameters':return {'Instigator':self.spawner}
    def test_pickup_reads_instigator_spawner_and_first_fx_only(self):
        policy.pickup(self.cue,'irrelevant-target',self.params,self.results);self.assertEqual(self.fx.calls,[(('SetVariableLinearColor','GunPad_Color','spawner-color'),{})]);self.assertEqual(self.second.calls,[])
    def test_pickup_uses_native_parameters_break(self):
        policy.pickup(self.cue,None,self.params,self.results);self.assertEqual(self.calls[0],('BreakGameplayCueParameters',(self.params,),{}))
    def test_pickup_null_fx_prints_exact_original_literal_before_instigator_read(self):
        self.results.FxSystemComponents=[None];policy.pickup(self.cue,None,self.params,self.results);self.assertEqual(len(self.calls),1);name,args,kw=self.calls[0];self.assertEqual(name,'PrintString');self.assertEqual(kw,dict(WorldContextObject=self.cue,InString='NOT VALID',bPrintToScreen=True,bPrintToLog=True,TextColor=(0.,.66,1.,1.),Duration=2.,Key='None'))
    def test_pickup_wrong_fx_type_also_prints(self):
        self.results.FxSystemComponents=[Item('ParticleSystemComponent')];policy.pickup(self.cue,None,self.params,self.results);self.assertEqual(self.calls[0][0],'PrintString')
    def test_empty_pickup_array_retains_native_array_diagnostics(self):
        self.results.FxSystemComponents=[];policy.pickup(self.cue,'t',self.params,self.results);self.assertEqual(self.original,[('OnBurst','t',self.params,self.results)]);self.assertEqual(self.calls,[])
    def test_wrong_pickup_instigator_retains_original_null_property_diagnostic(self):
        self.spawner=Item('Actor');policy.pickup(self.cue,'t',self.params,self.results);self.assertEqual(self.original,[('OnBurst','t',self.params,self.results)]);self.assertEqual(self.fx.calls,[])
    def test_null_pickup_instigator_retains_original_diagnostic(self):
        self.spawner=None;policy.pickup(self.cue,'t',self.params,self.results);self.assertEqual(len(self.original),1)
    def test_grenade_color_comes_from_typed_target(self):
        policy.grenade(self.cue,self.grenade,self.params,self.results);self.assertEqual(self.fx.calls,[(('SetVariableLinearColor','Team_Color','grenade-color'),{})]);self.assertEqual(self.calls,[])
    def test_grenade_only_writes_first_fx(self):
        policy.grenade(self.cue,self.grenade,self.params,self.results);self.assertEqual(self.second.calls,[])
    def test_wrong_grenade_target_does_not_even_read_spawn_results(self):
        policy.grenade(self.cue,Item('Actor'),self.params,object());self.assertEqual(self.calls+self.original,[])
    def test_null_grenade_target_is_a_noop(self):
        policy.grenade(self.cue,None,self.params,object());self.assertEqual(self.calls+self.original,[])
    def test_empty_grenade_array_retains_native_diagnostics_after_target_cast(self):
        self.results.FxSystemComponents=[];policy.grenade(self.cue,self.grenade,self.params,self.results);self.assertEqual(self.original,[('OnBurst',self.grenade,self.params,self.results)])
    def test_grenade_null_fx_is_silent(self):
        self.results.FxSystemComponents=[None];policy.grenade(self.cue,self.grenade,self.params,self.results);self.assertEqual(self.calls+self.original,[])
    def test_grenade_wrong_fx_class_is_silent(self):
        self.results.FxSystemComponents=[Item('ParticleSystemComponent')];policy.grenade(self.cue,self.grenade,self.params,self.results);self.assertEqual(self.calls+self.original,[])
    def test_melee_preserves_player_strength_and_world_context(self):
        policy.melee(self.cue,'target');self.assertEqual(self.calls,[(('SendWeaponFire',),dict(Player='target',Strength=.2,__WorldContext=self.cue))])
    def test_melee_does_not_introduce_a_null_player_guard(self):
        policy.melee(self.cue,None);self.assertIsNone(self.calls[0][1]['Player'])
    def test_heal_uses_source_component_and_zero_start_time(self):
        policy.heal(self.cue,'target',self.params,self.results);self.assertEqual(self.audio.calls,[(('Play',0.),{})])
    def test_heal_does_not_stop_or_replace_component_sound(self):
        policy.heal(self.cue,'target',self.params,self.results);self.assertEqual(len(self.audio.calls),1);self.assertEqual(self.original,[])
    def test_missing_heal_component_retains_native_diagnostic(self):
        self.cue.get_property=lambda name:None;policy.heal(self.cue,'target',self.params,self.results);self.assertEqual(self.original,[('OnBurst','target',self.params,self.results)])
    def test_blueprint_fallback_forwards_exact_original_arguments(self):
        policy.LyraSmallBurstBlueprintFallbackProfile.OnBurst(self.cue,'t',self.params,self.results);self.assertEqual(self.original,[('OnBurst','t',self.params,self.results)]);self.assertEqual(policy.evidence(self.cue)['fallback_burst'],1)
