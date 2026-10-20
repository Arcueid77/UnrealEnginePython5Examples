"""Source AI branch order, integer overflow, stale blackboard and fresh locals."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n
structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw);structs.GameplayEventData=lambda **kw:types.SimpleNamespace(EventMagnitude=kw.get('EventMagnitude',0.))
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda a:a is not None
spec=importlib.util.spec_from_file_location('uep_lyra_world._shooter_ai_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/shooter_ai_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.effect_pad_mixin':validity}):spec.loader.exec_module(policy)


def int32(n):return (int(n)+2**31)%2**32-2**31


class ShooterPolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.data=dict(TotalAmmo=999,OutOfAmmo='ammo-key',TargetEnnemy='enemy-key',SetFocus=False,EnemyNameKey='TargetEnemy',BTAsset='tree');self.current=self.item(3,0);self.other=self.item(0,0);self.roster=[self.current,self.other];self.equipped=types.SimpleNamespace(call_function=lambda f:self.current);self.manager=types.SimpleNamespace(call_function=lambda f:self.roster);self.equipment=types.SimpleNamespace(call_function=lambda *a:self.equipped);self.pawn=types.SimpleNamespace(get_component_by_type=lambda c:self.equipment);self.controller=types.SimpleNamespace(get_component_by_type=lambda c:self.manager,call_function=lambda f,*a:self.calls.append(('controller',f,*a)));self.brain=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('brain',f,*a)));self.board=types.SimpleNamespace(call_function=lambda f,*a:self.calls.append(('board',f,*a)));self.data.update(BrainComponent=self.brain,AIPerception=types.SimpleNamespace(call_function=lambda f:self.calls.append(('perception',f))));self.a=types.SimpleNamespace(get_property=self.data.get,set_property=self.set_property,call_function=self.call);self.target=object();self.bb=[];self.may_attack=True;policy.lib=lambda n:types.SimpleNamespace(call_function=lambda f,*a:self.library(n,f,a))
    def item(self,mag,spare):
        values={policy.MAGAZINE:mag,policy.SPARE:spare};return types.SimpleNamespace(values=values,call_function=lambda f,tag:values[tag.TagName],is_a=lambda c:True)
    def set_property(self,k,v):
        if k not in self.data:raise AssertionError('function locals cannot become node properties: '+k)
        self.data[k]=v
    def call(self,f,*a):
        if f=='GetCurrentWeapon':return (policy.weapon(self.a,*a)['CanShoot'],)
        self.calls.append(('node',f,*a))
    def library(self,n,f,a):
        if f=='Add_IntInt':return int32(a[0]+a[1])
        if f=='SetBlackboardValueAsBool':self.bb.append(bool(a[-1]));return
        if f=='GetBlackboardValueAsActor':return self.target
        if f=='GetAIController':return self.controller
        if f=='GetBlackboard':return self.board
        if f=='CanPlayerBotsAttack':return self.may_attack
        if f=='SendGameplayEventToActor':self.calls.append(('event',a[1].TagName,a[2].EventMagnitude));return
        raise AssertionError((n,f,a))
    def test_total_ammo_resets_each_tick_and_uses_every_inventory_item(self):
        self.other.values[policy.SPARE]=7;policy.ammo(self.a,self.controller);self.assertEqual(self.data['TotalAmmo'],10);policy.ammo(self.a,self.controller);self.assertEqual(self.data['TotalAmmo'],10);self.assertEqual(self.bb,[False,False])
    def test_total_ammo_preserves_native_int32_wrap(self):
        self.current.values.update({policy.MAGAZINE:2147483647,policy.SPARE:1});policy.ammo(self.a,self.controller);self.assertEqual(self.data['TotalAmmo'],-2147483648);self.assertEqual(self.bb,[True])
    def test_empty_inventory_marks_out_of_ammo(self):
        self.roster=[];policy.ammo(self.a,self.controller);self.assertEqual(self.bb,[True])
    def test_reload_sends_empty_payload_to_controlled_pawn(self):
        policy.reload(self.a,self.pawn);self.assertEqual(self.calls,[('event',policy.RELOAD,0.)])
    def test_focus_set_uses_selected_blackboard_actor(self):
        self.data['SetFocus']=True;policy.focus(self.a,self.controller);self.assertEqual(self.calls,[('controller','K2_SetFocus',self.target)])
    def test_focus_clear_does_not_need_target(self):
        policy.focus(self.a,self.controller);self.assertEqual(self.calls,[('controller','K2_ClearFocus')])
    def test_loaded_weapon_does_not_clear_stale_out_of_ammo(self):
        self.assertTrue(policy.weapon(self.a,self.pawn,self.controller)['CanShoot']);self.assertFalse(self.bb)
    def test_spare_only_weapon_still_returns_true_before_later_branch(self):
        self.current.values.update({policy.MAGAZINE:0,policy.SPARE:7});self.assertTrue(policy.weapon(self.a,self.pawn,self.controller)['CanShoot']);self.assertFalse(self.calls)
    def test_invalid_pawn_returns_false_without_side_effects(self):
        self.assertFalse(policy.weapon(self.a,None,self.controller)['CanShoot']);self.assertFalse(self.calls)
    def test_no_equipment_does_not_invent_inventory_switch(self):
        self.equipped=None;self.other.values[policy.MAGAZINE]=3;self.assertFalse(policy.weapon(self.a,self.pawn,self.controller)['CanShoot']);self.assertFalse(self.calls)
    def test_first_other_item_with_ammo_uses_inventory_index(self):
        self.current.values[policy.MAGAZINE]=0;self.other.values[policy.MAGAZINE]=5;self.roster=[self.item(0,0),self.current,self.other];self.assertTrue(policy.weapon(self.a,self.pawn,self.controller)['CanShoot']);self.assertEqual(self.calls,[('event',policy.SLOT,2.)])
    def test_query_locals_reset_between_invocations(self):
        self.current.values[policy.MAGAZINE]=0;self.other.values[policy.MAGAZINE]=5;self.assertTrue(policy.weapon(self.a,self.pawn,self.controller)['CanShoot']);self.other.values[policy.MAGAZINE]=0;self.assertFalse(policy.weapon(self.a,self.pawn,self.controller)['CanShoot']);self.assertEqual(self.bb,[True]);self.assertNotIn('HasMoreWeapon',self.data)
    def test_source_total_guard_can_reach_later_false_branch_for_negative_magazine(self):
        self.current.values.update({policy.MAGAZINE:-3,policy.SPARE:2});self.assertFalse(policy.weapon(self.a,self.pawn,self.controller)['CanShoot']);self.assertFalse(self.calls);self.assertFalse(self.bb)
    def test_slot_selection_and_fire_stay_in_same_tick_order(self):
        self.current.values[policy.MAGAZINE]=0;self.other.values[policy.MAGAZINE]=5;policy.shoot(self.a,self.controller,self.pawn);self.assertEqual(self.calls,[('event',policy.SLOT,1.),('event',policy.FIRE,0.)])
    def test_false_weapon_query_does_not_fire(self):
        self.current.values[policy.MAGAZINE]=0;policy.shoot(self.a,self.controller,self.pawn);self.assertFalse(self.calls)
    def test_ready_runs_original_tree_then_native_death_binding(self):
        policy.ready(self.a);self.assertEqual(self.calls,[('node','RunBehaviorTree','tree'),('node',policy.BACKENDS['bind'])])
    def test_possess_starts_brain_before_native_team_observer(self):
        policy.possess(self.a);self.assertEqual(self.calls,[('brain','StartLogic'),('node',policy.BACKENDS['observe'])])
    def test_possess_without_brain_still_observes_team(self):
        self.data['BrainComponent']=None;policy.possess(self.a);self.assertEqual(self.calls,[('node',policy.BACKENDS['observe'])])
    def test_death_clears_enemy_before_stopping_brain(self):
        policy.death(self.a);self.assertEqual(self.calls,[('board','ClearValue','TargetEnemy'),('brain','StopLogic','Dead')])
    def test_allowed_uses_native_development_setting(self):
        self.may_attack=False;self.assertEqual(policy.allowed(self.a),dict(UseOriginal=False,Allowed=False))
