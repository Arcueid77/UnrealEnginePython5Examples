"""Source score ordering, partial casts, reset filters and native lifecycle entry."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw);structs.GameplayEventData=lambda:types.SimpleNamespace(default_payload=True)
enums=types.ModuleType('unreal_engine.enums');enums.ELyraTeamComparison=types.SimpleNamespace(DifferentTeams=1)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
outputs=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');outputs.native_outputs=lambda cls,fn,value:value
helpers=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');helpers.lib=lambda name:None
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._scoring_base_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/scoring_base_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'unreal_engine.enums':enums,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':outputs,'uep_lyra_weapons.hero_burst_cue_mixin':helpers}):spec.loader.exec_module(policy)


class Object:
    def __init__(self,label,log,ps=True):self.label=label;self.log=log;self.ps=ps;self.controller=object();self.asc=None;self.spawning=False
    def is_a(self,cls):return self.ps
    def call_function(self,fn,*args):
        self.log.append((self.label,fn,args))
        if fn=='GetController':return self.controller
        if fn=='HasMatchingGameplayTag':return self.spawning


class ScoringBasePolicyTests(unittest.TestCase):
    def setUp(self):
        self.log=[];self.component=Object('component',self.log);self.source=Object('source',self.log);self.target=Object('target',self.log);self.message=types.SimpleNamespace(Instigator=self.source,Target=self.target,Magnitude=-33.)
        self.system=Object('teams',self.log);self.relation=1;self.all=[];native.find_class=lambda n:n;native.load_class=lambda n:n
        self.system.call_function=self.team_call;policy.lib=lambda name:types.SimpleNamespace(call_function=self.backend);policy.actors=lambda component,cls:self.all
    def backend(self,fn,*args):
        self.log.append(('native',fn,args))
        if fn=='GetWorldSubsystem':return self.system
        if fn=='GetAbilitySystemComponent':return args[0].asc
    def team_call(self,fn,*args):
        self.log.append(('teams',fn,args))
        if fn=='CompareTeams':return dict(ReturnValue=self.relation,TeamIdA=7,TeamIdB=8)
    def writes(self):return [(who,fn) for who,fn,args in self.log if fn in ('AddTeamTagStack','AddStatTagStack','OnEliminationScored')]
    def test_begin_uses_original_listener_entry_and_blocks_duplicate_source(self):
        self.assertIs(policy.LyraScoringBasePythonProfile.Begin(self.component),False);self.assertEqual(self.log,[('component',policy.START,())])
    def test_enemy_score_order_is_team_then_kill_then_death_then_virtual_hook(self):
        self.assertIs(policy.elimination(self.component,self.message),False);self.assertEqual(self.writes(),[('teams','AddTeamTagStack'),('source','AddStatTagStack'),('target','AddStatTagStack'),('component','OnEliminationScored')])
    def test_team_id_and_literal_stack_count_come_from_native_compare(self):
        policy.elimination(self.component,self.message);args=next(a for w,f,a in self.log if f=='AddTeamTagStack');self.assertEqual((args[0],args[1].TagName,args[2]),(7,'ShooterGame.Score.Eliminations',1))
    def test_player_kill_and_death_tags_are_distinct(self):
        policy.elimination(self.component,self.message);values=[(w,a[0].TagName,a[1]) for w,f,a in self.log if f=='AddStatTagStack'];self.assertEqual(values,[('source','ShooterGame.Score.Eliminations',1),('target','ShooterGame.Score.Deaths',1)])
    def test_same_team_does_not_even_add_target_death(self):
        self.relation=0;policy.elimination(self.component,self.message);self.assertEqual(self.writes(),[])
    def test_invalid_relation_is_a_noop(self):
        self.relation=2;policy.elimination(self.component,self.message);self.assertEqual(self.writes(),[])
    def test_non_player_instigator_retains_partial_team_add(self):
        self.source.ps=False;policy.elimination(self.component,self.message);self.assertEqual(self.writes(),[('teams','AddTeamTagStack')])
    def test_non_player_target_retains_team_and_instigator_only(self):
        self.target.ps=False;policy.elimination(self.component,self.message);self.assertEqual(self.writes(),[('teams','AddTeamTagStack'),('source','AddStatTagStack')])
    def test_missing_team_subsystem_returns_to_original_diagnostics(self):
        self.system=None;self.assertIs(policy.elimination(self.component,self.message),True);self.assertEqual(self.writes(),[])
    def test_assist_ignores_team_target_and_magnitude(self):
        self.message.Target=None;self.assertIs(policy.assist(self.component,self.message),False);self.assertEqual(self.log[0][2][0].TagName,'ShooterGame.Score.Assists');self.assertEqual(self.log[0][2][1],1)
    def test_assist_wrong_type_is_silent(self):
        self.source.ps=False;policy.assist(self.component,self.message);self.assertEqual(self.log,[])
    def test_assist_null_instigator_is_silent(self):
        self.message.Instigator=None;policy.assist(self.component,self.message);self.assertEqual(self.log,[])
    def test_reset_skips_asc_then_controller_then_nonexact_spawning_tag(self):
        missing=Object('no-asc',self.log);uncontrolled=Object('no-controller',self.log);uncontrolled.asc=Object('asc1',self.log);uncontrolled.controller=None
        spawning=Object('spawning',self.log);spawning.asc=Object('asc2',self.log);spawning.asc.spawning=True;ready=Object('ready',self.log);ready.asc=Object('asc3',self.log);self.all=[missing,uncontrolled,spawning,ready]
        self.assertIs(policy.reset(self.component),False);sent=[a for w,f,a in self.log if f=='SendGameplayEventToActor'];self.assertEqual(len(sent),1);self.assertIs(sent[0][0],ready);self.assertEqual(sent[0][1].TagName,'GameplayEvent.RequestReset');self.assertTrue(sent[0][2].default_payload)
        counts=policy.evidence(self.component);self.assertEqual([counts[k] for k in ('reset_seen','reset_missing_asc','reset_missing_controller','reset_spawning_skips','reset_sent')],[4,1,1,1,1])
    def test_reset_does_not_query_controller_when_asc_missing(self):
        self.all=[self.source];policy.reset(self.component);self.assertFalse(any(w=='source' and f=='GetController' for w,f,a in self.log))
    def test_reset_empty_world_is_a_noop(self):self.assertIs(policy.reset(self.component),False);self.assertEqual(self.log,[])
    def test_warmup_resets_spawners_before_destroying_grenades(self):
        pad=Object('pad',self.log);grenade=Object('grenade',self.log);seen=[]
        def actors(component,cls):seen.append(cls);return [None,pad] if cls==policy.SPAWNER else [None,grenade]
        policy.actors=actors;self.assertIs(policy.warmup(self.component),False);self.assertEqual(seen,[policy.SPAWNER,policy.GRENADE]);self.assertEqual(self.log,[('pad','ResetCoolDown',()),('grenade','K2_DestroyActor',())])
    def test_fallback_gates_return_to_original_business_without_new_side_effects(self):
        for name,args in (('Begin',()),('Elimination',(self.message,)),('Assist',(self.message,)),('Reset',()),('Warmup',())):self.assertIs(getattr(policy.LyraScoringBaseBlueprintFallbackProfile,name)(self.component,*args),True)
        self.assertEqual(self.log,[])
