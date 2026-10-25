import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from uep_lyra_abilities.arena_opponent_bomb_contract import FORBIDDEN,validate,outcome,compare
from uep_lyra_hud.startup import validation_module

def fixture(profile='Python'):
    fire=dict(owner=0,new_bombs=1,instigator_matches_owner=True,saved_state_matches_owner=True,remaining_before=[1.,1.],remaining_after=[0.,1.],foreign_owner_unchanged=True,bomb_profiles_match=True)
    row=dict(drop=fire,health_before=[100.,100.],health_after=[100.,0.],opponent_death=dict(observed=True,health=0.,player_state='opponent',seconds_after_bomb_creation=2.),
        score_delta=[[1,0,0],[0,1,0]],team_score_delta=[1,0],different_native_teams=True,selected_elimination_callbacks=1,other_elimination_callbacks=0,
        selected_input_callbacks=1,other_input_callbacks=0,native_bomb_callbacks=dict(trigger=1,increment=2,destroyed=1),remaining_after_refund=[1.,1.],bombs_destroyed_by_cleanup=0,original_fuse_seconds=2.,original_explosion_radius=2,fixed_timestep_used=False)
    report=dict(status='passed',error=None,profile=profile,map='L_TopDown_LocalMultiplayer',native_mode='Standalone',local_players=2,distinct_player_owners=True,
        ability_granted_by_original_experience=True,input_action_from_original_pawn_data=True,pawn_position_written=True,bounded_pose_fixture_used=True,
        cleanup_complete=True,native_local_player_removed=True,death_observer_closed=True,message_observer_closed=True,input_released=True,owners=[dict(player_state='owner'),dict(player_state='opponent')],result=row,
        native_elimination_messages=[dict(channel='Lyra.Elimination.Message',target='opponent',target_is_opponent=True,instigator_is_null=False,source_owner=0,team_comparison='DifferentTeams')])
    report.update(dict.fromkeys(FORBIDDEN,False));return report

class ArenaOpponentBombContractTests(unittest.TestCase):
    def paths(self,root):
        paths=[];frozen=root/'frozen.py';frozen.write_text('original',encoding='utf-8')
        import hashlib
        for profile in ('BlueprintFallback','Python'):
            path=root/profile;path.mkdir();paths.append(path)
            (path/'result.json').write_text(json.dumps(fixture(profile)),encoding='utf-8')
            summary=dict(status='passed',profile=profile,process=dict(exit_code=0),external_gate=dict(exit_code=0),cpp_compile_executed=False,cook_package_executed=False,
                hashes=[dict(path=str(frozen),sha256=hashlib.sha256(frozen.read_bytes()).hexdigest())])
            (path/'summary.json').write_text(json.dumps(summary),encoding='utf-8')
        return paths
    def test_original_python_outcomes_equal(self):self.assertEqual(outcome(fixture()),outcome(fixture('BlueprintFallback')))
    def test_only_explicit_game_entry_selects_probe(self):
        flag='-UEPArenaOpponentResult=owned.json'
        self.assertEqual(validation_module([flag]),'uep_lyra_abilities.arena_opponent_bomb_validation')
        for args in ([],['-game'],['-UEPArenaOpponentResult'],['-run=Py',flag]):self.assertIsNone(validation_module(args))
    def test_each_fixture_shortcut_rejected(self):
        for key in FORBIDDEN:
            r=fixture();r[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_self_death_foreign_damage_or_wrong_native_victim_rejected(self):
        for health in ([0.,100.],[0.,0.],[100.,100.]):
            r=fixture();r['result']['health_after']=health
            with self.assertRaises(ValueError):validate(r)
        r=fixture();r['result']['opponent_death']['player_state']='owner'
        with self.assertRaises(ValueError):validate(r)
    def test_kill_death_team_points_and_selected_path_required(self):
        for key,value in [('score_delta',[[0,0,0],[0,1,0]]),('team_score_delta',[0,1]),('selected_elimination_callbacks',0),('other_elimination_callbacks',1),('different_native_teams',False)]:
            r=fixture();r['result'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_owner_only_original_input_cost_and_instigator_required(self):
        for key,value in [('owner',1),('new_bombs',2),('instigator_matches_owner',False),('saved_state_matches_owner',False),('remaining_after',[0.,0.]),('bomb_profiles_match',False)]:
            r=fixture();r['result']['drop'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_natural_fuse_refund_and_callbacks_required(self):
        for key,value in [('native_bomb_callbacks',dict(trigger=0,increment=1,destroyed=1)),('remaining_after_refund',[0.,1.]),('bombs_destroyed_by_cleanup',1),('fixed_timestep_used',True)]:
            r=fixture();r['result'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
        for elapsed in (.2,float('nan'),float('inf')):
            r=fixture();r['result']['opponent_death']['seconds_after_bomb_creation']=elapsed
            with self.assertRaises(ValueError):validate(r)
    def test_pose_fixture_and_cleanup_cannot_be_hidden(self):
        for key in ('pawn_position_written','bounded_pose_fixture_used','cleanup_complete','native_local_player_removed','death_observer_closed','message_observer_closed','input_released'):
            r=fixture();r[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):validate(r)
    def test_native_uncredited_death_cannot_be_claimed_as_scored_kill(self):
        r=fixture();r['native_elimination_messages'][0].update(instigator_is_null=True,source_owner=None,team_comparison='InvalidArgument')
        with self.assertRaises(ValueError):validate(r)
        r['result'].update(score_delta=[[0,0,0],[0,0,0]],team_score_delta=[0,0]);validate(r)
        r['native_elimination_messages'][0]['target']='owner'
        with self.assertRaises(ValueError):validate(r)
    def test_failed_process_profile_and_missing_pair_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.paths(Path(directory));self.assertEqual(compare(paths)['native_opponent_eliminations'],2)
            for cases in (paths[:1],[paths[0],paths[0]]):
                with self.assertRaises(ValueError):compare(cases)
            p=paths[0]/'summary.json';summary=json.loads(p.read_text());summary['process']['exit_code']=1;p.write_text(json.dumps(summary))
            with self.assertRaises(ValueError):compare(paths)
    def test_changed_frozen_input_and_unequal_fuse_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=self.paths(Path(directory));p=paths[0]/'result.json';r=json.loads(p.read_text());r['result']['original_fuse_seconds']=2.1;p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):compare(paths)
            p.write_text(json.dumps(fixture('BlueprintFallback')));(Path(directory)/'frozen.py').write_text('changed')
            with self.assertRaises(ValueError):compare(paths)
    def test_report_cli_uses_independent_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.json';path.write_text(json.dumps(fixture()),encoding='utf-8')
            result=subprocess.run([sys.executable,'-B','-X','utf8','-m','uep_lyra_abilities.arena_opponent_bomb_contract','--report',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
