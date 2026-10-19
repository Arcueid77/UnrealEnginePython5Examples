"""TDM thresholds, equality, timer/notify ordering and source GAS/Cue semantics."""
import importlib.util
import math
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))

native=types.ModuleType('unreal_engine');structs=types.ModuleType('unreal_engine.structs')
structs.GameplayTag=lambda **kw:types.SimpleNamespace(TagName=kw.get('TagName',''));structs.GameplayTagContainer=lambda **kw:types.SimpleNamespace(**kw);structs.GameplayEffectContextHandle=lambda:types.SimpleNamespace(empty=True)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
outputs=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');outputs.native_outputs=lambda *args:args[-1]
helpers=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');helpers.lib=lambda name:None
base=types.ModuleType('uep_lyra_weapons.scoring_base_mixin')
class Base:
    def Begin(self):pass
    def Elimination(self,*a):pass
    def Assist(self,*a):pass
    def Reset(self):pass
    def Warmup(self):pass
base.LyraScoringBasePythonProfile=base.LyraScoringBaseBlueprintFallbackProfile=Base;base.tag=lambda name:structs.GameplayTag(TagName=name);base.teams=lambda c:None;base.actors=lambda *args:[]
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._tdm_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/tdm_scoring_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':outputs,'uep_lyra_weapons.hero_burst_cue_mixin':helpers,'uep_lyra_weapons.scoring_base_mixin':base}):spec.loader.exec_module(policy)


class TDMPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.data=dict(TargetScore=15,CountDownTime=2.,WinningTeamId=-1,ActiveUserFacingCue=structs.GameplayTag(),BigTeam=False);self.scores={1:14,2:14};self.player_count=5;self.controllers=2
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.call)
        self.system=types.SimpleNamespace(call_function=lambda fn,team,tag:self.scores.get(team,0));base.teams=lambda c:self.system;base.actors=lambda *args:[object() for _ in range(self.player_count)]
        native.find_class=lambda n:n;native.load_class=lambda n:n;native.FVector=lambda *a:a
        policy.lib=lambda name:types.SimpleNamespace(call_function=lambda fn,*args,**kw:self.backend(fn,args,kw));self.ascs=[types.SimpleNamespace(call_function=lambda *args,i=i:self.calls.append(('asc',i,*args))) for i in range(2)]
        self.mode=types.SimpleNamespace(call_function=lambda *args:self.calls.append(('mode',*args)))
    def write(self,name,value):self.data[name]=value;self.calls.append(('write',name,value))
    def call(self,fn,*args):
        self.calls.append(('call',fn,*args))
        if fn==policy.SET_TIME:self.data['CountDownTime']=args[0]
        if fn==policy.SET_TARGET:self.data['TargetScore']=args[0]
        if fn=='GetTeamScore':return (self.scores[args[0]],self.data['TargetScore'],self.scores[args[0]]==self.data['TargetScore'])
    def backend(self,fn,args,kw):
        self.calls.append(('native',fn,args,kw))
        if fn=='Subtract_DoubleDouble':return args[0]-args[1]
        if fn=='GetGameState':return 'state'
        if fn=='GetGameMode':return self.mode
        if fn=='GetNumPlayerControllers':return self.controllers
        if fn=='GetPlayerController':return 'controller-'+str(args[1])
        if fn=='GetNumPlayerStates':return len(self.ascs)
        if fn=='GetPlayerState':return args[1]
        if fn=='GetAbilitySystemComponent':return self.ascs[args[0]]
        if fn=='IsGameplayTagValid':return bool(args[0].TagName)
        if fn=='MakeGameplayCueParameters':return types.SimpleNamespace(AbilityLevel=kw['AbilityLevel'])
    def test_victory_requires_exact_target_not_above_target(self):
        for value,expected in ((14,False),(15,True),(16,False)):
            self.scores[1]=value;self.assertEqual(policy.score(self.actor,1)['Victory'],expected)
    def test_score_query_preserves_three_original_outputs(self):self.assertEqual(policy.score(self.actor,1),dict(UseOriginal=False,CurrentScore=14,TargetScore=15,Victory=False))
    def test_elimination_prefers_team_one_if_both_exact(self):
        self.scores={1:15,2:15};policy.elimination(self.actor);self.assertEqual([c for c in self.calls if c[:2]==('call','HandleVictory')],[('call','HandleVictory',1)])
    def test_elimination_above_target_does_not_end_game(self):
        self.scores={1:16,2:17};policy.elimination(self.actor);self.assertFalse(any(c[:2]==('call','HandleVictory') for c in self.calls))
    def test_six_character_boundary_sets_source_target_and_duration(self):
        for count,target,duration in ((5,15,720.),(6,30,1200.)):
            self.calls=[];self.player_count=count;policy.started(self.actor);self.assertEqual(self.calls,[('call',policy.SET_TARGET,target),('call',policy.SET_TIME,duration),('call',policy.TIMER),('call','ResetAllActivePlayers'),('call','PostWarmup')])
    def test_game_started_does_not_write_unconnected_big_team_member(self):policy.started(self.actor);self.assertIs(self.data['BigTeam'],False)
    def test_countdown_notifies_before_checking_expiry(self):
        policy.countdown(self.actor);self.assertEqual(self.data['CountDownTime'],1.);self.assertIn(('call',policy.SET_TIME,1.),self.calls);self.assertFalse(any(c[:2]==('call',policy.CLEAR_TIMER) for c in self.calls))
    def test_countdown_tie_uses_draw_zero(self):
        self.data['CountDownTime']=1.;policy.countdown(self.actor);self.assertEqual(self.calls[-1],('call','HandleVictory',0));self.assertIn(('call',policy.CLEAR_TIMER),self.calls)
    def test_countdown_uses_fixed_teams_one_and_two(self):
        self.data['CountDownTime']=0.;self.scores={1:2,2:4};policy.countdown(self.actor);self.assertEqual((self.data['Team0Score'],self.data['Team1Score']),(2,4));self.assertEqual(self.calls[-1],('call','HandleVictory',2))
    def test_negative_countdown_is_not_clamped(self):
        self.data['CountDownTime']=-2.;policy.countdown(self.actor);self.assertEqual(self.data['CountDownTime'],-3.)
    def test_nan_countdown_does_not_take_native_less_equal_zero_branch(self):
        self.data['CountDownTime']=math.nan;policy.countdown(self.actor);self.assertFalse(any(c[:2]==('call',policy.CLEAR_TIMER) for c in self.calls))
    def test_disable_damage_uses_original_effect_level_zero_and_empty_context(self):
        policy.damage(self.actor,False);applies=[c for c in self.calls if c[0]=='asc'];self.assertEqual(len(applies),2);self.assertTrue(all(c[2]=='BP_ApplyGameplayEffectToSelf' and c[3]==policy.IMMUNITY and c[4]==0. and c[5].empty for c in applies))
    def test_enable_damage_removes_only_original_mode_immunity_tag(self):
        policy.damage(self.actor,True);rows=[c for c in self.calls if c[0]=='asc'];self.assertTrue(all(c[2]=='RemoveActiveEffectsWithTags' and c[3].GameplayTags[0].TagName=='TODO.GameModeDamageImmunity' for c in rows))
    def test_missing_asc_keeps_original_diagnostics_without_partial_python_effects(self):
        self.ascs[1]=None;self.assertIs(policy.damage(self.actor,False),True);self.assertFalse(any(c[0]=='asc' for c in self.calls))
    def test_clear_invalid_cue_is_noop(self):policy.clear(self.actor);self.assertFalse(any(c[0]=='write' for c in self.calls))
    def test_clear_removes_before_resetting_cue_tag(self):
        self.data['ActiveUserFacingCue']=base.tag('GameplayCue.Test');policy.clear(self.actor);remove=next(i for i,c in enumerate(self.calls) if c[:2]==('native','RemoveGameplayCueOnActor'));reset=next(i for i,c in enumerate(self.calls) if c[:2]==('write','ActiveUserFacingCue'));self.assertLess(remove,reset)
    def test_activate_clears_then_stores_then_adds(self):
        tag=base.tag('GameplayCue.Test');p=object();policy.activate(self.actor,tag,p);self.assertEqual(self.calls[0],('call','ClearUserFacingCue'));self.assertEqual(self.calls[1],('write','ActiveUserFacingCue',tag));self.assertEqual(self.calls[-1][1],'AddGameplayCueOnActor')
    def test_victory_uses_ability_level_and_retains_timer(self):
        policy.victory(self.actor,2);self.assertEqual(self.data['WinningTeamId'],2);cue=next(c for c in self.calls if c[:2]==('call','ActivateUserFacingCue'));self.assertEqual(cue[3].AbilityLevel,2);self.assertEqual(self.calls[-1],('call',policy.POSTGAME));self.assertNotIn(('call',policy.CLEAR_TIMER),self.calls)
    def test_force_game_over_is_draw(self):
        policy.LyraTDMScoringPythonProfile.Force(self.actor);self.assertEqual(self.calls,[('call','HandleVictory',0)])
    def test_restart_enumerates_native_player_controller_indices(self):
        policy.restart(self.actor);self.assertEqual([c for c in self.calls if c[0]=='mode'],[('mode','RestartPlayer','controller-0'),('mode','RestartPlayer','controller-1')])
    def test_missing_game_mode_returns_to_original_diagnostics(self):self.mode=None;self.assertIs(policy.restart(self.actor),True)
    def test_blueprint_query_gate_returns_use_original_and_typed_defaults(self):self.assertEqual(policy.LyraTDMScoringBlueprintFallbackProfile.Score(self.actor,1),dict(UseOriginal=True,CurrentScore=0,TargetScore=0,Victory=False))
