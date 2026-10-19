"""Original CP array/state/capture/palette/count/score and phase semantics."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(TagName=kw.get('TagName',''))
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
base.LyraScoringBasePythonProfile=base.LyraScoringBaseBlueprintFallbackProfile=Base;base.tag=lambda name:structs.GameplayTag(TagName=name);base.teams=lambda c:None;base.actors=lambda *a:[]
tdm=types.ModuleType('uep_lyra_weapons.tdm_scoring_mixin');tdm.params=lambda ability=1:types.SimpleNamespace(AbilityLevel=ability)
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._cp_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/cp_scoring_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':outputs,'uep_lyra_weapons.hero_burst_cue_mixin':helpers,'uep_lyra_weapons.scoring_base_mixin':base,'uep_lyra_weapons.tdm_scoring_mixin':tdm}):spec.loader.exec_module(policy)


class Pawn:
    def __init__(self,team,state=None):self.team=team;self.state=state
    def get_property(self,n):return self.state


class State:
    def __init__(self,team,log):self.team=team;self.log=log
    def is_a(self,cls):return True
    def call_function(self,*args):self.log.append(('state',self.team,*args))


class CPPolicyTests(unittest.TestCase):
    def setUp(self):
        self.log=[];self.point=object();self.data=dict(ControlPoints=[self.point],ControlPointOwnerTeams=[-1],TeamColors={1:'red'},RawTeamColors=['green','blue'],TeamColorAssignIndex=0,TargetScore=5,LeadingTeam=9,WinningTeamId=0,ActiveUserFacingCue=structs.GameplayTag());self.score_value=5;self.player_count=6;self.owned={1:0,2:0}
        self.c=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.call);native.find_class=lambda n:n;native.FLinearColor=lambda *a:a
        self.system=types.SimpleNamespace(call_function=self.team);base.teams=lambda c:self.system;base.actors=lambda *a:[object() for _ in range(self.player_count)];policy.lib=lambda name:types.SimpleNamespace(call_function=self.backend)
    def write(self,k,v):self.data[k]=v;self.log.append(('write',k,v))
    def call(self,n,*args):
        self.log.append(('call',n,*args))
        if n=='GetPointStatus':return (self.owned[args[0]],0,0)
        if n=='GetTeamScoreCP':return (self.score_value,5,self.score_value>=5)
    def team(self,n,*args):
        self.log.append(('teams',n,*args))
        if n=='FindTeamFromActor':return dict(bIsPartOfTeam=args[0] is not None and args[0].team>=0,TeamId=args[0].team if args[0] is not None else -1)
        if n=='GetTeamTagStackCount':return self.score_value
    def backend(self,n,*args):
        self.log.append(('native',n,*args))
        if n=='Add_IntInt':return ((args[0]+args[1]+2**31)%2**32)-2**31
        if n=='FindTeamFromObject':return dict(TeamId=args[0].team)
        if n=='IsGameplayTagValid':return bool(args[0].TagName)
        if n=='GetGameState':return 'state'
    def test_registration_appends_duplicate_point_and_initializes_new_slot_minus_one(self):
        policy.register(self.c,self.point);self.assertEqual(self.data['ControlPoints'],[self.point,self.point]);self.assertEqual(self.data['ControlPointOwnerTeams'],[-1,-1])
    def test_registration_extends_array_with_native_zero_defaults(self):
        self.data['ControlPoints']=[self.point,self.point];self.data['ControlPointOwnerTeams']=[];policy.register(self.c,None);self.assertEqual(self.data['ControlPointOwnerTeams'],[0,0,-1])
    def test_contest_only_changes_first_duplicate(self):
        self.data['ControlPoints']=[self.point,self.point];self.data['ControlPointOwnerTeams']=[1,2];policy.assign(self.c,self.point,-1,'Contest');self.assertEqual(self.data['ControlPointOwnerTeams'],[-1,2])
    def test_missing_point_preserves_native_negative_index_diagnostics(self):
        self.assertIs(policy.assign(self.c,object(),1,'Recapture'),True);self.assertEqual(self.data['ControlPointOwnerTeams'],[-1])
    def test_recapture_retains_arbitrary_team_id(self):policy.assign(self.c,self.point,77,'Recapture');self.assertEqual(self.data['ControlPointOwnerTeams'],[77])
    def test_capture_first_pawn_decides_owner_and_matching_states_get_award(self):
        a=State(2,self.log);b=State(1,self.log);policy.capture(self.c,[Pawn(2,a),Pawn(1,b),Pawn(2,a)],self.point);self.assertEqual(self.data['ControlPointOwnerTeams'],[2]);self.assertEqual(len([x for x in self.log if x[0]=='state']),2)
    def test_capture_unassigned_first_pawn_does_not_use_later_valid_pawn(self):
        policy.capture(self.c,[Pawn(-1),Pawn(1,State(1,self.log))],self.point);self.assertEqual(self.data['ControlPointOwnerTeams'],[-1]);self.assertFalse(any(x[0]=='state' for x in self.log))
    def test_empty_capture_keeps_original_array_diagnostics(self):self.assertIs(policy.capture(self.c,[],self.point),True)
    def test_unregistered_capture_keeps_original_side_effect_path(self):self.assertIs(policy.capture(self.c,[Pawn(1)],object()),True)
    def test_status_compares_requested_team_before_unowned_minus_one(self):
        self.data['ControlPointOwnerTeams']=[-1,1,2,0];self.assertEqual(policy.status(self.c,-1),dict(UseOriginal=False,OwnedByTeam=1,Unowned=0,OwnedByEnemy=3))
    def test_status_counts_unknown_teams_as_enemy(self):
        self.data['ControlPointOwnerTeams']=[-1,1,2,8];self.assertEqual(policy.status(self.c,1),dict(UseOriginal=False,OwnedByTeam=1,Unowned=1,OwnedByEnemy=2))
    def test_color_cached_value_does_not_advance_index(self):self.assertEqual(policy.color(self.c,1)['Color'],'red');self.assertEqual(self.data['TeamColorAssignIndex'],0)
    def test_color_assigns_current_palette_then_increments_native_int(self):
        self.assertEqual(policy.color(self.c,7)['Color'],'green');self.assertEqual(self.data['TeamColorAssignIndex'],1);self.assertEqual(self.data['TeamColors'][7],'green')
    def test_color_out_of_range_returns_to_original_diagnostics(self):
        self.data['TeamColorAssignIndex']=2;self.assertTrue(policy.color(self.c,7)['UseOriginal']);self.assertNotIn(7,self.data['TeamColors']);self.assertEqual(self.data['TeamColorAssignIndex'],2)
    def test_score_accepts_equal_and_above_target(self):
        for s,v in ((4,False),(5,True),(6,True)):
            self.score_value=s;self.assertEqual(policy.score(self.c,1)['Victory'],v)
    def test_scoring_tie_preserves_leading_team_and_adds_nothing(self):
        self.owned={1:1,2:1};policy.scoring(self.c);self.assertEqual(self.data['LeadingTeam'],9);self.assertFalse(any(x[:2]==('teams','AddTeamTagStack') for x in self.log))
    def test_scoring_awards_one_to_majority_then_checks_victory(self):
        self.owned={1:1,2:2};policy.scoring(self.c);self.assertEqual(self.data['LeadingTeam'],2);self.assertEqual(self.log[-1],('call','HandleVictory',2));add=next(x for x in self.log if x[:2]==('teams','AddTeamTagStack'));self.assertEqual((add[2],add[4]),(2,1))
    def test_game_started_uses_strictly_more_than_six_boundary(self):
        for players,target in ((6,125),(7,150)):
            self.log=[];self.player_count=players;policy.started(self.c);self.assertEqual(self.log,[('call',policy.SET_TARGET,target),('call','ResetAllActivePlayers'),('call','PostWarmup')])
    def test_victory_uses_ability_level_and_native_phase_then_timer_bridge(self):
        policy.victory(self.c,2);self.assertEqual(self.data['WinningTeamId'],2);activate=next(x for x in self.log if x[:2]==('call','ActivateUserFacingCue'));self.assertEqual(activate[3].AbilityLevel,2);self.assertEqual(self.log[-1],('call',policy.POSTGAME))
    def test_clear_invalid_tag_does_not_write(self):policy.clear(self.c);self.assertFalse(any(x[0]=='write' for x in self.log))
    def test_activate_clears_then_stores_then_adds(self):
        tag=base.tag('GameplayCue.Test');policy.activate(self.c,tag,object());self.assertEqual(self.log[0],('call','ClearUserFacingCue'));self.assertEqual(self.log[1],('write','ActiveUserFacingCue',tag));self.assertEqual(self.log[-1][1],'AddGameplayCueOnActor')
    def test_fallback_queries_keep_original_typed_outputs(self):
        self.assertEqual(policy.LyraCPScoringBlueprintFallbackProfile.Status(self.c,1),dict(UseOriginal=True,OwnedByTeam=0,Unowned=0,OwnedByEnemy=0))
