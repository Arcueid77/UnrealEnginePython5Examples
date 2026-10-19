"""Spawn Cue ordering, cache membership, native dispatch and lifecycle policy."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');enums=types.ModuleType('unreal_engine.enums');enums.EAttachLocation=types.SimpleNamespace(KeepRelativeOffset=0);enums.ENCPoolMethod=types.SimpleNamespace(**{'None':0})
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda value:value is not None
helpers=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');helpers.lib=lambda name:None;helpers.components=lambda *args:[]
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._spawning_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/spawning_cue_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.enums':enums,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_weapons.hero_burst_cue_mixin':helpers}):spec.loader.exec_module(policy)


class Mesh:
    def __init__(self,ignored=False):self.ignored=ignored
    def call_function(self,name,tag):return self.ignored


class SpawningPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.fx=types.SimpleNamespace(call_function=lambda *args:self.calls.append(('effect',*args)))
        self.timeline=types.SimpleNamespace(call_function=lambda *args:self.calls.append(('timeline',*args)))
        self.watcher=types.SimpleNamespace(call_function=lambda *args:self.calls.append(('watcher',*args)))
        self.data={'NiagaraSystemTemplates':['system-a','system-b'],'TargetActor':'old-target','Spawn Linear Time':.6,'TemplateToUse':'system-a','SpawnedEffectMap':{},'SpawnedEffects':[],'SpawningDuration':.5,'TeamColor':'team','SpawnTimeline':self.timeline,'TeamColorWatcherHandle':self.watcher,'PawnCosmeticSystem':'parts'}
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=lambda *args:self.calls.append(('actor',*args)),call_mixin_original=lambda *args:self.calls.append(('original',*args)))
        policy.lib=lambda name:types.SimpleNamespace(call_function=lambda fn,*args,**kw:self.backend(fn,args,kw));policy.components=lambda *args:[]
        native.FVector=lambda *args:args;native.FRotator=lambda *args:args;native.FLinearColor=lambda *args:args
    def write(self,key,value):self.data[key]=value;self.calls.append(('write',key,value))
    def backend(self,fn,args,kw):
        self.calls.append(('native',fn,args,kw))
        if fn=='RandomInteger':return 1
        if fn=='Divide_DoubleDouble':return args[0]/args[1]
        if fn=='SpawnSystemAttached':return self.fx
        if fn=='Conv_LinearColorToVector':return 'rgb'
        if fn=='GetTeamColorWithFallback':return 'new-team'
    def test_application_uses_one_native_random_call(self):
        policy.application(self.actor,'target','p','r');self.assertEqual(self.data['TemplateToUse'],'system-b');self.assertEqual([c for c in self.calls if c[:2]==('native','RandomInteger')],[('native','RandomInteger',(2,),{})])
    def test_application_preserves_duplicate_native_parts_entries(self):
        policy.application(self.actor,'target','p','r');self.assertEqual([c[1] for c in self.calls if c[0]=='actor'],[policy.WATCH,policy.PARTS,policy.PARTS,'SpawnEffectForEachMeshComponent','UpdateActorColors'])
    def test_application_resets_linear_time_without_clearing_existing_fx(self):
        self.data['SpawnedEffects']=[self.fx];policy.application(self.actor,'target','p','r');self.assertEqual(self.data['Spawn Linear Time'],0.);self.assertEqual(self.data['SpawnedEffects'],[self.fx]);self.assertEqual(self.calls[-2:],[('timeline','SetPlayRate',2.),('timeline','PlayFromStart')])
    def test_empty_templates_enter_source_diagnostics_before_partial_writes(self):
        self.data['NiagaraSystemTemplates']=[];policy.application(self.actor,'target','p','r');self.assertEqual(self.calls,[('original','OnApplication','target','p','r')]);self.assertEqual(self.data['TargetActor'],'old-target')
    def test_spawn_skips_ignored_meshes_and_uses_children(self):
        seen=[];policy.components=lambda *args:seen.append(args) or [Mesh(True),Mesh()];policy.spawn(self.actor);self.assertEqual(seen,[('old-target','SkeletalMeshComponent',True)]);self.assertEqual(len(self.data['SpawnedEffects']),1)
    def test_cache_contains_key_with_invalid_value_still_skips(self):
        mesh=Mesh();self.data['SpawnedEffectMap']={mesh:None};policy.components=lambda *args:[mesh];policy.spawn(self.actor);self.assertEqual(self.calls,[]);self.assertEqual(policy.evidence(self.actor)['existing_meshes'],1)
    def test_spawn_appends_instead_of_replacing_old_array(self):
        self.data['SpawnedEffects']=['old'];policy.components=lambda *args:[Mesh()];policy.spawn(self.actor);self.assertEqual(self.data['SpawnedEffects'],['old',self.fx])
    def test_spawn_duration_parameter_preserves_source_spelling(self):
        policy.components=lambda *args:[Mesh()];policy.spawn(self.actor);self.assertIn(('effect','SetVariableFloat','SpawnTImeLength',.5),self.calls);self.assertIn(('effect','SetVariableVec3','BodyColor','rgb'),self.calls)
    def test_spawn_options_match_original(self):
        policy.components=lambda *args:[Mesh()];policy.spawn(self.actor);kw=next(c[3] for c in self.calls if c[:2]==('native','SpawnSystemAttached'));self.assertEqual((kw['bAutoDestroy'],kw['bAutoActivate'],kw['bPreCullCheck']),(False,True,True))
    def test_missing_template_preserves_original_diagnostic_graph(self):
        self.data['TemplateToUse']=None;policy.spawn(self.actor);self.assertEqual(self.calls,[('original','SpawnEffectForEachMeshComponent')])
    def test_team_change_skips_invalid_effects_without_updating_materials(self):
        self.data['SpawnedEffects']=[None,self.fx];policy.team(self.actor,'display');self.assertEqual(self.data['TeamColor'],'new-team');self.assertEqual(self.calls[-1],('effect','SetVariableVec3','BodyColor','rgb'));self.assertFalse(any(c[0]=='actor' for c in self.calls))
    def test_team_fallback_color_is_exact_source_literal(self):
        policy.team(self.actor,None);call=self.calls[0];self.assertEqual(call[2],(None,'TeamColor',(1.,0.,.721921,1.)))
    def test_update_preserves_raw_native_curve_and_validity_guards(self):
        self.data['SpawnedEffects']=[None,self.fx];self.assertIs(policy.update(self.actor,.37),False);self.assertEqual(self.data['Spawn Linear Time'],.37);self.assertEqual(self.calls[-1],('effect','SetVariableFloat','SpawnTimeline',.37))
    def test_colors_updates_kill_edge_then_spawn_age(self):
        policy.colors(self.actor);self.assertEqual([(c[1],c[2][1]) for c in self.calls],[('SetColorParameterValueOnAllMeshComponents','KillEdgeColor'),('SetScalarParameterValueOnAllMeshComponents','SpawnAge')])
    def test_removal_order_clears_caches_then_cancels_then_unbinds(self):
        self.data['SpawnedEffects']=[None,self.fx];policy.removal(self.actor);self.assertEqual([c[:2] for c in self.calls],[('native','SetScalarParameterValueOnAllMeshComponents'),('effect','Deactivate'),('write','SpawnedEffects'),('write','SpawnedEffectMap'),('watcher','Cancel'),('actor','StopWatchingForParts')])
    def test_removal_retains_source_fields_and_does_not_stop_timeline(self):
        policy.removal(self.actor);self.assertEqual((self.data['Spawn Linear Time'],self.data['TargetActor'],self.data['PawnCosmeticSystem'],self.data['TeamColorWatcherHandle']),(.6,'old-target','parts',self.watcher));self.assertFalse(any(c[0]=='timeline' for c in self.calls))
    def test_missing_watcher_still_unbinds_parts(self):
        self.data['TeamColorWatcherHandle']=None;policy.removal(self.actor);self.assertEqual(self.calls[-1],('actor','StopWatchingForParts'));self.assertFalse(any(c[0]=='watcher' for c in self.calls))
    def test_parts_callback_ignores_payload_and_keeps_spawn_before_colors(self):
        policy.LyraSpawningCuePythonProfile.OnCharacterPartsChanged(self.actor,object());self.assertEqual(self.calls,[('actor','SpawnEffectForEachMeshComponent'),('actor','UpdateActorColors')])
    def test_stop_uses_source_delegate_identity_transport(self):
        policy.LyraSpawningCuePythonProfile.StopWatchingForParts(self.actor);self.assertEqual(self.calls,[('actor',policy.STOP)])
    def test_fallback_update_returns_to_original_timeline_business(self):
        self.assertIs(policy.LyraSpawningCueBlueprintFallbackProfile.TimelineUpdate(self.actor,.25),True);self.assertEqual(self.calls,[])
