"""Original EQS boundaries, actor order, fresh locals and native alive/team filter."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.load_class=lambda n:n;native.FVector=lambda *v:tuple(v or (0.,0.,0.))
structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw)
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
outputs=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');outputs.native_outputs=lambda c,f,v:v
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda a:a is not None
ai=types.ModuleType('uep_lyra_world.shooter_ai_mixin');ai.one=lambda v:v[0] if isinstance(v,tuple) and len(v)==1 else v;ai.SPARE='spare'
spec=importlib.util.spec_from_file_location('uep_lyra_world._shooter_eqs_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/shooter_eqs_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_abilities.melee_trace_mixin':outputs,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_world.shooter_ai_mixin':ai}):spec.loader.exec_module(policy)


class EQSPolicyTests(unittest.TestCase):
    def setUp(self):
        self.team=1;self.roster=[];self.item=None;self.maximum=10;self.board=types.SimpleNamespace(call_function=lambda *a:self.target);self.target=None;self.inventory=types.SimpleNamespace(call_function=lambda *a:self.item);self.controller=types.SimpleNamespace(get_component_by_type=lambda c:self.inventory);self.querier=types.SimpleNamespace(is_a=lambda c:c in ('Pawn','LyraCharacter'),call_function=lambda f:self.controller);self.added=[];self.context=types.SimpleNamespace(get_property=lambda n:'TargetEnemy',call_function=self.call);self.teams=types.SimpleNamespace(call_function=lambda f,*a:dict(TeamId=self.team) if f=='FindTeamFromActor' else (a[0].comparison,0,0));policy.actors=lambda *a:self.roster;policy.teams=lambda a:self.teams;policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(n,f,a))
    def call(self,f,*a):
        if f=='GetQuerier':return self.querier
        if f=='AddGeneratedActor':self.added.append(a[0]);return
        raise AssertionError(f)
    def library(self,n,f,a):
        if f=='GetAIController':return self.controller
        if f=='GetBlackboard':return self.board
        if f=='GetDefaultStatFromItemDef':return self.maximum
        raise AssertionError((n,f))
    def point(self,team):return types.SimpleNamespace(get_property=lambda n:team)
    def spawner(self,cooldown,ability=False):
        definition=types.SimpleNamespace(get_property=lambda n:'item-class');return types.SimpleNamespace(is_a=lambda c:ability and c==policy.ABILITY,get_property=lambda n:cooldown if n=='CoolDownPercentage' else definition)
    def character(self,comparison,dead):return types.SimpleNamespace(comparison=comparison,get_property=lambda n:types.SimpleNamespace(call_function=lambda f:dead))
    def test_points_keep_native_enumeration_order_and_exclude_own_team(self):
        a,b,c=self.point(2),self.point(1),self.point(-1);self.roster=[a,b,c];self.assertEqual(policy.points(self.context,self.querier)['Actors'],[a,c])
    def test_no_team_querier_uses_returned_minus_one_even_if_not_in_team(self):
        self.team=-1;a,b=self.point(-1),self.point(0);self.roster=[a,b];self.assertEqual(policy.points(self.context,None)['Actors'],[b])
    def test_context_actor_lists_are_fresh_each_call(self):
        self.roster=[self.point(2)];first=policy.points(self.context,self.querier)['Actors'];self.roster=[];self.assertEqual(policy.points(self.context,self.querier)['Actors'],[]);self.assertEqual(len(first),1)
    def test_target_actor_location_is_not_controller_position(self):
        self.target=types.SimpleNamespace(is_a=lambda c:True,get_actor_location=lambda:(7.,8.,9.));self.assertEqual(policy.enemy(self.context,self.querier)['Location'],(7.,8.,9.))
    def test_missing_or_nonactor_target_leaves_native_out_parameter_unwritten(self):
        self.assertFalse(policy.enemy(self.context,self.querier)['HasResult']);self.target=types.SimpleNamespace(is_a=lambda c:False);self.assertFalse(policy.enemy(self.context,self.querier)['HasResult'])
    def test_real_actor_at_origin_still_writes_valid_zero_location(self):
        self.target=types.SimpleNamespace(is_a=lambda c:True,get_actor_location=lambda:(0.,0.,0.));result=policy.enemy(self.context,self.querier);self.assertTrue(result['HasResult']);self.assertEqual(result['Location'],(0.,0.,0.))
    def test_weapon_context_rejects_nonpawn_without_inventory_access(self):
        self.querier.is_a=lambda c:False;self.assertEqual(policy.weapon(self.context,self.querier)['Actors'],[])
    def test_exact_cooldown_boundary_is_excluded(self):
        a,b,c=self.spawner(.099999),self.spawner(.1),self.spawner(.100001);self.roster=[a,b,c];self.assertEqual(policy.weapon(self.context,self.querier)['Actors'],[a])
    def test_ability_spawner_is_excluded_before_inventory_comparison(self):
        a,b=self.spawner(0.,True),self.spawner(0.);self.roster=[a,b];self.assertEqual(policy.weapon(self.context,self.querier)['Actors'],[b])
    def test_missing_item_included_even_if_definition_default_spare_is_zero(self):
        self.maximum=0;a=self.spawner(0.);self.roster=[a];self.assertEqual(policy.weapon(self.context,self.querier)['Actors'],[a])
    def test_only_spare_ammo_below_default_threshold_matters(self):
        a=self.spawner(0.);self.roster=[a];self.item=types.SimpleNamespace(call_function=lambda *a:9);self.assertEqual(policy.weapon(self.context,self.querier)['Actors'],[a]);self.item.call_function=lambda *a:10;self.assertEqual(policy.weapon(self.context,self.querier)['Actors'],[])
    def test_enemy_generator_rejects_noncharacter_querier(self):
        self.querier.is_a=lambda c:False;policy.enemies(self.context);self.assertFalse(self.added)
    def test_enemy_generator_keeps_only_different_teams_and_alive_actors(self):
        a,b,c,d=self.character(1,False),self.character(0,False),self.character(2,False),self.character(1,True);self.roster=[a,b,c,d];policy.enemies(self.context);self.assertEqual(self.added,[a])
    def test_generator_preserves_actor_enumeration_order(self):
        a,b=self.character(1,False),self.character(1,False);self.roster=[b,a];policy.enemies(self.context);self.assertEqual(self.added,[b,a])
