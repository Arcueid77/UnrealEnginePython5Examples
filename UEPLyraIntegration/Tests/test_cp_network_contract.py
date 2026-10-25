import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_weapons.cp_network_contract import FALSE,PEERS,SOUNDS,validate,validate_all,compare_profiles
from uep_lyra_hud.startup import validation_module

def report(peer):
    roster={p:dict(player_id=i+1,state_wire=['Legacy',str(i+3)],pawn_wire=['Legacy',str(i+5)],team=i+1,name=p) for i,p in enumerate(('A','B0'))}
    row=dict(roster=roster,point_wire=['Legacy','20'],team_scores=[1,0],capture_stats=[1,0],point_owner=1,target_score=1,healths=[100.,100.],damage_immunity=[True,True],capture_audio_owner_teams=[1],capture_audio_sounds=[SOUNDS.get(peer)],capture_audio_playing=[peer!='server'],native_score_widgets=0 if peer=='server' else 1,hud={} if peer=='server' else dict(ally='1' if peer=='A' else '0',enemy='0' if peer=='A' else '1',target='1'),match_decided_cue_actors=1,native_postgame=True,native_playing=False,selected_capture_calls=1,selected_victory_calls=1,real_overlap_observed=True)
    row['effective_profiles']=dict.fromkeys(('scoring','point') if peer=='server' else ('scoring','point','score_widget'),'Python')
    r=dict(status='passed',error=None,peer=peer,run_id='run',requested_profile='Python',result=row,server_waited_for_client_process_exit=peer=='server')
    r.update(dict.fromkeys(FALSE,False));r.update(dict.fromkeys(('profiles_selected_before_component_creation','initial_canonical_healthy_owners','native_scores_and_capture_stats_restored','target_score_restored','observer_profiles_restored','boot_selectors_restored','observer_class_roots_restored','observer_references_released'),True));return r
class CPNetworkContractTests(unittest.TestCase):
    def test_three_real_peer_results(self):
        with tempfile.TemporaryDirectory() as folder:
            for p in PEERS:(Path(folder)/(p+'.json')).write_text(json.dumps(report(p)))
            self.assertEqual(validate_all(folder)['real_clients'],2)
    def test_score_phase_and_capture_cannot_be_substituted(self):
        for field,value in (('team_scores',[0,1]),('capture_stats',[0,0]),('native_postgame',False),('real_overlap_observed',False),('selected_victory_calls',0)):
            r=report('server');r['result'][field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_local_audio_and_actual_widget_must_match_owner(self):
        for field,value in (('capture_audio_sounds',['Enemy']),('capture_audio_playing',[False]),('hud',dict(ally='0',enemy='1',target='1')),('native_score_widgets',0)):
            r=report('A');r['result'][field]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_owned_cleanup_and_native_exit_barrier_required(self):
        for field in ('server_waited_for_client_process_exit','initial_canonical_healthy_owners','native_scores_and_capture_stats_restored','target_score_restored','observer_profiles_restored','boot_selectors_restored','observer_class_roots_restored','observer_references_released'):
            r=report('server');r[field]=False
            with self.assertRaises(RuntimeError):validate(r)
    def test_manually_replayed_capture_or_repaired_avatar_rejected(self):
        for field in FALSE:
            r=report('server');r[field]=True
            with self.assertRaises(RuntimeError):validate(r)
    def test_actual_instance_profile_is_required(self):
        r=report('A');r['result']['effective_profiles']['score_widget']='BlueprintFallback'
        with self.assertRaises(RuntimeError):validate(r)
    def test_actual_capture_sound_asset_is_required(self):
        r=report('A');r['result']['capture_audio_sounds']=['unrelatedFriendly']
        with self.assertRaises(RuntimeError):validate(r)
    def test_original_python_comparison_requires_independent_complete_groups(self):
        original={p:report(p) for p in PEERS};python=copy.deepcopy(original)
        for r in original.values():
            r['run_id']='original';r['requested_profile']='BlueprintFallback';r['result']['effective_profiles']=dict.fromkeys(r['result']['effective_profiles'],'BlueprintFallback')
        self.assertEqual(compare_profiles(original,python)['natural_capture_cases'],2)
        with self.assertRaises(RuntimeError):compare_profiles(python,python)
        python['B0']['result']['native_postgame']=False
        with self.assertRaises(RuntimeError):compare_profiles(original,python)
    def test_explicit_startup_never_runs_as_commandlet(self):
        self.assertEqual(validation_module(['-UEPCPNetworkResult=r']),'uep_lyra_weapons.cp_network_validation')
        self.assertIsNone(validation_module([]));self.assertIsNone(validation_module(['-run=Test','-UEPCPNetworkResult=r']))
