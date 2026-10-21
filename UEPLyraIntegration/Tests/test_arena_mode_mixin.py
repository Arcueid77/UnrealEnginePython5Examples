import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
def load():
    unreal=types.ModuleType('unreal_engine');unreal.FLinearColor=lambda *v:v;unreal.find_class=lambda name:name;structs=types.ModuleType('unreal_engine.structs');structs.GameplayTag=lambda **v:types.SimpleNamespace(**v);enums=types.ModuleType('unreal_engine.enums');enums.ELyraTeamComparison=types.SimpleNamespace(DifferentTeams=1);native=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');native.native_outputs=lambda cls,name,value:value;valid=types.ModuleType('uep_lyra_world.effect_pad_mixin');valid.valid=lambda obj:obj is not None
    spec=importlib.util.spec_from_file_location('uep_lyra_world.arena_mode_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/arena_mode_mixin.py');p=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'unreal_engine':unreal,'unreal_engine.structs':structs,'unreal_engine.enums':enums,'uep_lyra_abilities.melee_trace_mixin':native,'uep_lyra_world.effect_pad_mixin':valid}):spec.loader.exec_module(p)
    return p
class ArenaModePolicyTests(unittest.TestCase):
    def test_begin_keeps_native_factory_sequence(self):
        p=load();calls=[];w=types.SimpleNamespace(call_function=lambda *a:calls.append(a));self.assertIs(p.LyraArenaModePythonProfile.Begin(w),False);self.assertEqual(calls,[(p.START,)])
    def test_elimination_keeps_team_add_before_partial_source_target_casts(self):
        p=load();calls=[];p.teams=lambda w:types.SimpleNamespace(call_function=lambda n,*a:{'ReturnValue':1,'TeamIdA':1,'TeamIdB':2} if n=='CompareTeams' else calls.append(n));source=types.SimpleNamespace(is_a=lambda c:False);target=object();w=types.SimpleNamespace(call_function=lambda n:calls.append(n));p.LyraArenaModePythonProfile.Elimination(w,types.SimpleNamespace(Instigator=source,Target=target));self.assertEqual(calls,['AddTeamTagStack'])
    def test_elimination_hook_only_after_both_player_state_casts(self):
        p=load();calls=[];p.teams=lambda w:types.SimpleNamespace(call_function=lambda n,*a:{'ReturnValue':1,'TeamIdA':1,'TeamIdB':2} if n=='CompareTeams' else calls.append(n));source=types.SimpleNamespace(is_a=lambda c:True,call_function=lambda n,*a:calls.append('kill'));target=types.SimpleNamespace(is_a=lambda c:True,call_function=lambda n,*a:calls.append('death'));w=types.SimpleNamespace(call_function=lambda n:calls.append(n));p.LyraArenaModePythonProfile.Elimination(w,types.SimpleNamespace(Instigator=source,Target=target));self.assertEqual(calls,['AddTeamTagStack','kill','death','OnEliminationScored'])
    def test_remaining_output_is_named_and_uses_server_clock_clamp(self):
        p=load();p.state=lambda w:types.SimpleNamespace(call_function=lambda n:10.);p.lib=lambda n:types.SimpleNamespace(call_function=lambda method,a,b:a-b if method=='Subtract_DoubleDouble' else max(a,b));w=types.SimpleNamespace(get_property=lambda n:True if n=='IsPlaying' else 9.);self.assertEqual(p.LyraArenaModePythonProfile.GetRoundTimeRemaining(w),{'SecondsRemaining':0.});self.assertTrue(p.LyraArenaModePythonProfile.GetRoundTimeRemaining.uep_named_outputs)
    def test_warmup_sets_playing_then_exact120s_end(self):
        p=load();calls=[];p.state=lambda w:types.SimpleNamespace(call_function=lambda n:10.);p.lib=lambda n:types.SimpleNamespace(call_function=lambda method,a,b:a+b);w=types.SimpleNamespace(set_property=lambda *a:calls.append(a));p.LyraArenaModePythonProfile.WarmupEnded(w);self.assertEqual(calls,[('IsPlaying',True),('ServerWorld_GameEndTime',130.)])
    def test_expired_tick_clears_flag_before_native_postgame(self):
        p=load();calls=[];p.lib=lambda n:types.SimpleNamespace(call_function=lambda method,a,b:a==b);w=types.SimpleNamespace(get_property=lambda n:True,call_function=lambda n:(0.,) if n=='GetRoundTimeRemaining' else calls.append(n),set_property=lambda *a:calls.append(a));p.LyraArenaModePythonProfile.Tick(w);self.assertEqual(calls,[('IsPlaying',False),p.POSTGAME])
    def test_local_users_skip_first_and_keep_native_spawn_controller_flag(self):
        p=load();calls=[];users=[object(),object(),object()];p.lib=lambda n:types.SimpleNamespace(call_function=lambda method,*a:{'ReturnValue':3,'OutUsers':users} if method=='GetAllActiveUsers' else calls.append(a));w=types.SimpleNamespace();p.LyraArenaModePythonProfile.SpawnLocalUsers(w);self.assertEqual(calls,[(w,users[1],True),(w,users[2],True)])
    def test_client_child_begin_prints_but_does_not_spawn(self):
        p=load();calls=[];p.lib=lambda n:types.SimpleNamespace(call_function=lambda *a:calls.append(a[0]));owner=types.SimpleNamespace(call_function=lambda n:False);w=types.SimpleNamespace(call_function=lambda n:owner);p.LyraArenaModePythonProfile.LocalAfterParent(w);self.assertEqual(calls,['PrintString'])
