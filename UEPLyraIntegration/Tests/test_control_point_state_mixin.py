"""Exact authority overlap and contest/recapture/Timeline decision policy."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
outputs=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');outputs.native_outputs=lambda *a:a[-1]
libmodule=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libmodule.lib=lambda n:None
helpers=types.ModuleType('uep_lyra_world.control_point_helpers_mixin');helpers.CLASS='volume-class'
class Helpers:
    def Construct(self):pass
    def Check(self):pass
    def Contest(self):pass
    def Recapture(self):pass
helpers.LyraControlPointHelpersPythonProfile=helpers.LyraControlPointHelpersBlueprintFallbackProfile=Helpers
spec=importlib.util.spec_from_file_location('uep_lyra_world._point_state_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/control_point_state_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':outputs,'uep_lyra_weapons.hero_burst_cue_mixin':libmodule,'uep_lyra_world.control_point_helpers_mixin':helpers}):spec.loader.exec_module(policy)


class PointStateTests(unittest.TestCase):
    def setUp(self):
        self.log=[];self.playing=True;self.authority=True;self.timeline_playing=True;self.teams={'a':1,'b':2,'c':1,None:None}
        self.timeline=types.SimpleNamespace(call_function=self.clock);self.scoring=types.SimpleNamespace(call_function=self.score);self.state=types.SimpleNamespace(call_function=lambda *a:self.scoring)
        self.data={'OverlappingPawns':[],'OverlappingTeams':[99],'OwnerTeamID':-1,'ControlPointGameMode':self.scoring,'TL_ConvertPoint':self.timeline,'TimeRequiredForCapture':2.}
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.call);policy.lib=lambda n:types.SimpleNamespace(call_function=lambda fn,*args:self.backend(n,fn,args));native.find_class=lambda n:n;native.load_class=lambda n:n;native.FLinearColor=lambda *a:a
    def write(self,k,v):self.data[k]=v;self.log.append(('write',k,v))
    def call(self,fn,*a):
        if fn=='HasAuthority':return self.authority
        self.log.append(('actor',fn,*a))
    def clock(self,fn,*a):
        self.log.append(('timeline',fn,*a))
        if fn=='IsPlaying':return self.timeline_playing
    def score(self,fn,*a):
        self.log.append(('scoring',fn,*a))
        if fn=='GetTeamColor':return ('color-'+str(a[0]),)
    def backend(self,library,fn,args):
        if fn=='GetGameState':return self.state
        if fn=='GetWorldSubsystem':return types.SimpleNamespace(call_function=lambda fn,*a:self.backend('subsystem',fn,a))
        if fn=='FindTeamFromActor':return dict(bIsPartOfTeam=self.teams.get(args[0]) is not None,TeamId=self.teams.get(args[0],-1))
        if fn=='IsPhaseActive':return self.playing
        if fn=='Divide_DoubleDouble':return args[0]/args[1]
    def test_ready_assigns_then_registers_then_sets_native_rate(self):
        self.assertIs(policy.ready(self.actor),False);self.assertEqual(self.log,[('write','ControlPointGameMode',self.scoring),('scoring','RegisterControlPoint',self.actor),('timeline','SetPlayRate',.5)])
    def test_remote_ready_only_assigns_receiver(self):
        self.authority=False;policy.ready(self.actor);self.assertEqual(self.log,[('write','ControlPointGameMode',self.scoring)])
    def test_authority_missing_scoring_destroys_actor(self):
        self.scoring=None;policy.ready(self.actor);self.assertEqual(self.log,[('actor','K2_DestroyActor')])
    def test_enter_add_unique_before_recompute_then_audio(self):
        policy.overlap(self.actor,'a',True);self.assertEqual(self.data['OverlappingPawns'],['a']);self.assertEqual(self.log[-2:],[('actor','RecomputeContest'),('actor','Enter Audio ','a')])
    def test_duplicate_enter_still_recomputes_and_plays_source_audio(self):
        self.data['OverlappingPawns']=['a'];policy.overlap(self.actor,'a',True);self.assertEqual(self.data['OverlappingPawns'],['a']);self.assertEqual(self.log[-1],('actor','Enter Audio ','a'))
    def test_pure_failed_pawn_cast_null_is_not_filtered(self):policy.overlap(self.actor,None,True);self.assertEqual(self.data['OverlappingPawns'],[None])
    def test_exit_removes_all_matching_items(self):
        self.data['OverlappingPawns']=['a','b','a'];policy.overlap(self.actor,'a',False);self.assertEqual(self.data['OverlappingPawns'],['b']);self.assertEqual(self.log[-1],('actor','Exit Audio','a'))
    def test_nonplaying_overlap_keeps_list_mutation_without_recompute_or_audio(self):
        self.playing=False;policy.overlap(self.actor,'a',True);self.assertEqual(self.log,[('write','OverlappingPawns',['a'])])
    def test_recompute_preserves_first_seen_unique_team_order(self):
        self.data['OverlappingPawns']=['b',None,'a','c'];policy.recompute(self.actor);self.assertEqual(self.data['OverlappingTeams'],[2,1])
    def test_single_enemy_contests_then_sets_owner_and_target_colors_then_rpc_play(self):
        self.data['OverlappingPawns']=['a'];self.data['OwnerTeamID']=2;policy.recompute(self.actor);self.assertEqual(self.data['OwningTeamColor'],'color-2');self.assertEqual(self.data['TargetColor'],'color-1');self.assertEqual(self.log[-2:],[('actor','Activate VFX'),('timeline','Play')])
    def test_unowned_source_color_is_white(self):
        self.data['OverlappingPawns']=['a'];policy.recompute(self.actor);self.assertEqual(self.data['OwningTeamColor'],(1.,1.,1.,1.))
    def test_single_owner_team_only_recaptures_without_timeline_operation(self):
        self.data['OwnerTeamID']=1;self.data['OverlappingPawns']=['a'];policy.recompute(self.actor);self.assertEqual(self.log[-1],('actor','MarkThisPointRecaptured'));self.assertFalse(any(x[0]=='timeline' for x in self.log))
    def test_multiple_teams_contest_and_reverse_only_playing_timeline(self):
        self.data['OverlappingPawns']=['a','b'];policy.recompute(self.actor);self.assertEqual(self.log[-3:],[('actor','MarkThisPointContested'),('timeline','IsPlaying'),('timeline','Reverse')])
    def test_no_teams_recaptures_existing_owner_and_reverses(self):
        policy.recompute(self.actor);self.assertEqual(self.log[-3:],[('actor','MarkThisPointRecaptured'),('timeline','IsPlaying'),('timeline','Reverse')])
    def test_stopped_timeline_is_not_reversed(self):
        self.timeline_playing=False;policy.recompute(self.actor);self.assertFalse(any(x[:2]==('timeline','Reverse') for x in self.log))
    def test_missing_receiver_returns_to_original_diagnostics_before_clear(self):
        self.data['ControlPointGameMode']=None;self.assertIs(policy.recompute(self.actor),True);self.assertEqual(self.data['OverlappingTeams'],[99])
    def test_fallback_gates_preserve_original_business(self):
        for name,args in (('Ready',()),('Enter',('a',)),('Exit',('a',)),('Recompute',())):self.assertIs(getattr(policy.LyraControlPointStateBlueprintFallbackProfile,name)(self.actor,*args),True)
        self.assertEqual(self.log,[])
