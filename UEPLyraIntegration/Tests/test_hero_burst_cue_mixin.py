"""Source field, mesh/tag, parameter and asymmetric Timeline cleanup decisions."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');structs=types.ModuleType('unreal_engine.structs');enums=types.ModuleType('unreal_engine.enums')
structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw);enums.EAttachLocation=types.SimpleNamespace(KeepRelativeOffset=0);enums.ENCPoolMethod=types.SimpleNamespace(**{'None':0})
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
outputs=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');outputs.native_outputs=lambda cls,fn,value:value
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._hero_burst_policy',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/hero_burst_cue_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'unreal_engine.enums':enums,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':outputs}):spec.loader.exec_module(policy)


class HeroBurstPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.kill=False;self.meshes=[];self.decals=[]
        self.effect=types.SimpleNamespace(call_function=lambda *a:self.calls.append(('effect',*a)),is_a=lambda cls:True)
        self.timeline=types.SimpleNamespace(call_function=lambda *a:self.calls.append(('timeline',*a)))
        self.data={'SpawnedEffects':[],'TargetActor':'target','SpawningDuration':2.,'DashDeformTimeline':self.timeline,'DeathCubesTimeline':self.timeline}
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=lambda *a:self.calls.append(('actor',*a)))
        self.params=types.SimpleNamespace(NormalizedMagnitude=.25,RawMagnitude=77.25,Normal=(.25,-.5,.75),AggregatedSourceTags='tags')
        native.find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda method,*a,**kw:self.backend(method,a,kw)))
        native.load_object=lambda cls,path:path;native.FVector=lambda *a:a;native.FRotator=lambda:();native.FLinearColor=lambda *a:a
    def write(self,name,value):self.data[name]=value;self.calls.append(('write',name,value))
    def test_append_preserves_null_slots_and_normalizes_dead_component_references(self):
        dead=types.SimpleNamespace(is_a=lambda cls:False);self.data['SpawnedEffects']=[self.effect,None,dead];policy.append(self.actor,self.effect);self.assertEqual(self.data['SpawnedEffects'],[self.effect,None,None,self.effect])
    def backend(self,name,args,kwargs):
        self.calls.append(('native',name,args,kwargs))
        if name=='FindTeamFromObject':return {'DisplayAsset':'team-style','bIsPartOfTeam':True,'TeamId':1}
        if name=='BreakGameplayCueParameters':return {'NormalizedMagnitude':self.params.NormalizedMagnitude,'RawMagnitude':self.params.RawMagnitude,'Normal':self.params.Normal}
        if name=='GetTeamColorWithFallback':return (1.,.2,.3,1.)
        if name=='FindComponentsByClass':return self.decals if args[2] is False else self.meshes
        if name=='Divide_DoubleDouble':return args[0]/args[1] if args[1] else 0.
        if name=='Multiply_DoubleDouble':return args[0]*args[1]
        if name=='SpawnSystemAttached':return self.effect
        if name=='HasTag':return self.kill
        if name=='Conv_LinearColorToVector':return args[0][:3]
    def mesh(self,ignored=False):return types.SimpleNamespace(call_function=lambda *a:ignored)
    def test_dash_stores_source_misspelled_unused_strength_and_direction(self):
        policy.dash(self.actor,'target',self.params);self.assertEqual((self.data['Duration'],self.data['Strenght'],self.data['Direction']),(.25,77.25,(.25,-.5,.75)))
    def test_dash_uses_native_break_conversion_for_quantized_normal(self):
        prior=self.backend;converted=(.1,.2,.3)
        self.backend=lambda name,args,kwargs:{'NormalizedMagnitude':.25,'RawMagnitude':77.25,'Normal':converted} if name=='BreakGameplayCueParameters' else prior(name,args,kwargs)
        policy.dash(self.actor,'target',self.params);self.assertEqual(self.data['Direction'],converted)
    def test_exact_shared_ignore_tag_and_child_search_are_used(self):
        seen=[];self.meshes=[types.SimpleNamespace(call_function=lambda *a:seen.append(a) or True)]
        policy.dash(self.actor,'target',self.params);self.assertEqual(seen,[('ComponentHasTag','ignore')]);self.assertFalse(any(c[:2]==('native','SpawnSystemAttached') for c in self.calls))
        self.assertTrue(next(c[2][2] for c in self.calls if c[:2]==('native','FindComponentsByClass')))
    def test_dash_spawn_keeps_native_autodestroy_and_activation_options(self):
        self.meshes=[self.mesh()];policy.dash(self.actor,'target',self.params);kw=next(c[3] for c in self.calls if c[:2]==('native','SpawnSystemAttached'))
        self.assertEqual((kw['bAutoDestroy'],kw['bAutoActivate'],kw['bPreCullCheck']),(False,True,True))
    def test_source_array_is_appended_not_reset_at_burst(self):
        prior=types.SimpleNamespace(is_a=lambda cls:True);self.data['SpawnedEffects']=[prior];self.meshes=[self.mesh()];policy.dash(self.actor,'target',self.params);self.assertEqual(self.data['SpawnedEffects'],[prior,self.effect])
    def test_dash_sets_twice_duration_and_keeps_normal_unnormalized(self):
        self.meshes=[self.mesh()];policy.dash(self.actor,'target',self.params)
        self.assertIn(('effect','SetVariableFloat','DashDuration',.5),self.calls);self.assertIn(('effect','SetVariableVec3','DashDirection',(.25,-.5,.75)),self.calls)
    def test_native_timeline_rate_and_play_from_start_order(self):
        policy.dash(self.actor,'target',self.params);self.assertEqual([c for c in self.calls if c[0]=='timeline'],[('timeline','SetPlayRate',4.),('timeline','PlayFromStart')])
    def test_team_color_uses_exact_source_pink_fallback(self):
        policy.team(self.actor,'target');entry=next(c for c in self.calls if c[:2]==('native','GetTeamColorWithFallback'));self.assertEqual(entry[2],('team-style','TeamColor',(1.,0.,.721921,1.)))
    def test_death_uses_configured_duration_not_cue_magnitude(self):
        self.meshes=[self.mesh()];policy.death(self.actor,'target',self.params)
        self.assertIn(('effect','SetVariableFloat','KillTimeLength',2.),self.calls);self.assertIn(('timeline','SetPlayRate',.5),self.calls)
    def test_death_spawns_inactive_then_sets_data_and_activates_reset(self):
        self.meshes=[self.mesh()];policy.death(self.actor,'target',self.params);kw=next(c[3] for c in self.calls if c[:2]==('native','SpawnSystemAttached'))
        self.assertIs(kw['bAutoActivate'],False);fx=[c for c in self.calls if c[0]=='effect'];self.assertEqual([c[1] for c in fx],['SetVariableFloat','SetVariableVec3','Activate']);self.assertEqual(fx[-1],('effect','Activate',True))
    def test_killplane_tag_uses_nonexact_match(self):
        policy.death(self.actor,'target',self.params);entry=next(c for c in self.calls if c[:2]==('native','HasTag'));self.assertEqual(entry[2][1].TagName,'Gameplay.Damage.FellOutOfWorld');self.assertIs(entry[2][2],False)
    def test_death_decal_search_excludes_children(self):
        policy.death(self.actor,'target',self.params);searches=[c for c in self.calls if c[:2]==('native','FindComponentsByClass')];self.assertEqual([c[2][2] for c in searches],[True,False])
    def test_dash_updates_distinct_deform_and_ribbon_values(self):
        self.data['SpawnedEffects']=[self.effect];policy.update(self.actor,'dash',.2,.8)
        self.assertIn(('effect','SetVariableFloat','LifetimeMultiplier',.8),self.calls);self.assertTrue(any(c[:2]==('native','SetScalarParameterValueOnAllMeshComponents') and c[2][1:3]==('DashDeform',.2) for c in self.calls))
    def test_death_update_multiplies_edge_glow_and_skips_invalid_effects(self):
        self.data['SpawnedEffects']=[None,self.effect];policy.update(self.actor,'death',.3,.4)
        self.assertIn(('effect','SetFloatParameter','KillTimeline',.3),self.calls);self.assertTrue(any(c[:2]==('native','SetScalarParameterValueOnAllMeshComponents') and c[2][1:3]==('EdgeGlowMagnitude',8.) for c in self.calls))
    def test_dash_invalid_effects_use_retained_native_diagnostics(self):
        self.data['SpawnedEffects']=[None];self.assertIs(policy.update(self.actor,'dash',.2,.3),True);self.assertIs(policy.finish(self.actor,'dash'),True)
    def test_death_finish_only_resets_edge_glow_and_clears_array(self):
        self.data['SpawnedEffects']=[None,self.effect];policy.finish(self.actor,'death');self.assertEqual(self.data['SpawnedEffects'],[])
        setters=[c for c in self.calls if c[:2]==('native','SetScalarParameterValueOnAllMeshComponents')];self.assertEqual(len(setters),1);self.assertEqual(setters[0][2][1:3],('EdgeGlowMagnitude',0.));self.assertIn(('effect','Deactivate'),self.calls)
    def test_fallback_keeps_original_timeline_business(self):
        self.assertIs(policy.LyraHeroBurstBlueprintFallbackProfile.TimelineUpdate(self.actor,.2,.3),True);self.assertIs(policy.LyraHeroBurstBlueprintFallbackProfile.TimelineFinished(self.actor),True);self.assertEqual(self.calls,[])
