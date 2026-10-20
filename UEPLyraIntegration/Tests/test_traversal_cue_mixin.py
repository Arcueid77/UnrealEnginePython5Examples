"""Causer guards, native integer semantics and external curve/raw-time policies."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');enums=types.ModuleType('unreal_engine.enums');enums.EAttachLocation=types.SimpleNamespace(KeepRelativeOffset=0);enums.ENCPoolMethod=types.SimpleNamespace(**{'None':0})
macros=types.ModuleType('uep_lyra_weapons.macro_policies');macros.ignore_tag=lambda mesh:bool(mesh.call_function('ComponentHasTag','ignore'))
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
outputs=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');outputs.native_outputs=lambda cls,fn,value:value
helpers=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin')
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._traversal_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/traversal_cue_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_weapons.macro_policies':macros,'unreal_engine.enums':enums,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':outputs,'uep_lyra_weapons.hero_burst_cue_mixin':helpers}):
    helpers.lib=lambda name:None;helpers.components=lambda *a:[];helpers.team=lambda *a:None;spec.loader.exec_module(policy)


class TraversalPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.fx=types.SimpleNamespace(call_function=lambda *a:self.calls.append(('effect',*a)))
        self.timeline=types.SimpleNamespace(call_function=lambda *a:self.calls.append(('timeline',*a)))
        self.curve=types.SimpleNamespace(call_function=lambda fn,value:value*value)
        self.data={'SpawnedEffects':[self.fx],'ExitParticles':[],'TargetActor':'target','MaterialEffectCurve':self.curve,'LauncherMaterialEffect_Timeline':self.timeline,'MaterialEffectDuration':.5}
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=lambda *a:self.calls.append(('actor',*a)),call_mixin_original=lambda *a:self.calls.append(('original',*a)))
        self.teledata={'TeleporterEntered':0,'Niagara':self.fx,'TeleporterHeight':320.,'TeleporterPhase':-37.,'TeleporterDestination':None}
        self.tele=types.SimpleNamespace(get_property=self.teledata.get,set_property=lambda k,v:self.teledata.__setitem__(k,v),is_a=lambda cls:True)
        policy.lib=lambda name:types.SimpleNamespace(call_function=lambda fn,*a,**kw:self.backend(fn,a,kw));policy.components=lambda *a:[];policy.team=lambda *a:'team-color'
        native.find_class=lambda n:n;native.load_class=lambda n:n;native.load_object=lambda cls,path:path;native.FVector=lambda *a:a;native.FRotator=lambda:()
    def write(self,k,v):self.data[k]=v;self.calls.append(('write',k,v))
    def backend(self,fn,args,kw):
        self.calls.append(('native',fn,args,kw))
        if fn=='Add_IntInt':return ((args[0]+args[1]+2**31)%2**32)-2**31
        if fn=='Percent_IntInt':return args[0]-int(args[0]/args[1])*args[1]
        if fn=='SelectFloat':return args[0] if args[2] else args[1]
        if fn=='Divide_DoubleDouble':return args[0]/args[1]
        if fn=='Add_DoubleDouble':return args[0]+args[1]
        if fn=='MakeVector':return args
        if fn=='BreakGameplayCueParameters':return {'EffectCauser':self.tele}
    def test_counter_uses_native_int32_add_and_signed_remainder(self):
        for start,expected in ((0,1),(999999,0),(-2,-1),(2147483647,-483648)):
            self.teledata['TeleporterEntered']=start;policy.increment(self.actor,self.tele,True);self.assertEqual(self.teledata['TeleporterEntered'],expected)
            self.assertIn(('effect','SetVariableInt','SystemEntered',expected),self.calls)
    def test_entry_and_exit_direction_select_exact_source_values(self):
        policy.increment(self.actor,self.tele,True);policy.increment(self.actor,self.tele,False)
        self.assertIn(('effect','SetVariableFloat','UseDirection',1.),self.calls);self.assertIn(('effect','SetVariableFloat','UseDirection',-.8),self.calls)
    def test_portal_center_is_local_half_height_plus_phase(self):self.assertEqual(policy.center(self.tele),(0.,0.,123.))
    def test_material_curve_and_niagara_raw_time_are_distinct(self):
        self.assertIs(policy.update(self.actor,.4),False)
        self.assertIn(('effect','SetVariableFloat','LaunchPadGCNLValue',.4),self.calls)
        entry=next(c for c in self.calls if c[:2]==('native','SetScalarParameterValueOnAllMeshComponents'));self.assertAlmostEqual(entry[2][2],.16)
    def test_invalid_target_clears_and_stops_original_timeline(self):
        self.data['TargetActor']=None;policy.update(self.actor,.4);self.assertEqual(self.calls,[('actor','Clear Trails'),('timeline','Stop')])
    def test_missing_curve_uses_retained_native_diagnostics(self):
        self.data['MaterialEffectCurve']=None;self.assertIs(policy.update(self.actor,.4),True)
    def test_invalid_effect_preserves_native_update_diagnostic_path(self):
        self.data['SpawnedEffects']=[None];self.assertIs(policy.update(self.actor,.4),True)
    def test_clear_skips_invalid_effects_clears_array_then_resets_glow(self):
        self.data['SpawnedEffects']=[None,self.fx];policy.clear(self.actor);self.assertEqual(self.data['SpawnedEffects'],[])
        self.assertEqual(self.calls[0],('effect','Deactivate'));self.assertEqual(self.calls[1],('write','SpawnedEffects',[]));self.assertEqual(self.calls[2][2][1:3],('EdgeGlowMagnitude',0.))
    def test_clear_preserves_target_and_does_not_reset_curve_time(self):
        policy.clear(self.actor);self.assertEqual(self.data['TargetActor'],'target');self.assertFalse(any(c[0]=='timeline' for c in self.calls))
    def test_launcher_invalid_target_does_not_assign_fields(self):policy.launcher(self.actor,None,object());self.assertEqual(self.calls,[])
    def test_launcher_wrong_causer_retains_partial_target_assignment(self):
        self.tele.is_a=lambda cls:False;policy.launcher(self.actor,'new-target',object());self.assertEqual(self.data['TargetActor'],'new-target');self.assertFalse(any(c[:2]==('native','SpawnSystemAttached') for c in self.calls))
    def test_teleporter_wrong_causer_also_retains_only_target_assignment(self):
        self.tele.is_a=lambda cls:False;policy.teleport(self.actor,'new-target',object());self.assertEqual(self.data['TargetActor'],'new-target');self.assertNotIn('As B Teleport',self.data)
    def test_teleporter_no_destination_still_increments_entry(self):
        policy.teleport(self.actor,None,object());self.assertEqual(self.teledata['TeleporterEntered'],1);self.assertEqual(policy.evidence(self.actor)['exit_increments'],0)
    def test_exit_particle_array_append_does_not_discard_old_entries(self):
        old=object();self.data['ExitParticles']=[old];policy.append(self.actor,'ExitParticles',self.fx);self.assertEqual(self.data['ExitParticles'],[old,self.fx])
    def test_attached_system_options_remain_explicit(self):
        policy.spawn_attached('mesh','system',True,True,False);kw=self.calls[-1][3];self.assertEqual((kw['bAutoDestroy'],kw['bAutoActivate'],kw['bPreCullCheck']),(True,True,False))
    def test_fallback_update_keeps_original_curve_pipeline(self):
        self.assertIs(policy.LyraLauncherCueBlueprintFallbackProfile.TimelineUpdate(self.actor,.4),True);self.assertEqual(self.calls,[])
