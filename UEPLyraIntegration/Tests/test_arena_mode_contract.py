import copy,unittest
from uep_lyra_world.arena_mode_contract import validate,CLOCK
from uep_lyra_weapons.scoring_base_contract import CASES,EXPECTED
from test_arena_phases_contract import report as cycle
def report(mode='Python'):
    counts={p+k:0 for p in ('python_','fallback_') for k in ('begin','ready','warmup','localbegin','localspawn')}
    if mode!='Baseline':
        for key in ('begin','ready','warmup','localbegin','localspawn'):counts[('python_' if mode=='Python' else 'fallback_')+key]=1
    return dict(status='passed',error=None,mode=mode,cycle=cycle('Python'),full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,callbacks_replayed=False,begin_play_replayed=False,python_subscription_roots_added=False,native_proxy_cancelled_by_fixture=False,actual_round_properties_written=False,cleanup_complete=True,scores_restored=True,owned_actors_destroyed=True,owned_component_destroyed=True,pause_restored=True,natural_components=[{'class':'Lives_C','counts':copy.deepcopy(counts)},{'class':'SpawnLocalPlayers_C','counts':copy.deepcopy(counts)}],natural_local_user_count=1,natural_local_player_count=1,fixture_native_begin=True,fixture_native_message_proxies=2,scoring_recipients=3,message_cases=[dict(name=name,delta=[v//2*3 for v in EXPECTED[name]]) for name,*_ in CASES],clock_cases=[dict(playing=p,offset=o,remaining=v) for p,o,v in CLOCK],native_proxy_gi_refs_released=True,engine_gc_frames=3,owned_fixture_started_phase_after_cycle_only=True)
class ArenaModeContractTests(unittest.TestCase):
    def test_native_cycle_and_all_profiles(self):
        for mode in ('Baseline','Python','BlueprintFallback'):self.assertEqual(validate(report(mode))['native_score_messages'],8)
    def test_partial_cast_team_before_player_order_rejected_if_changed(self):
        r=report();row=next(v for v in r['message_cases'] if v['name']=='pawn-source');row['delta']=[0]*8
        with self.assertRaises(RuntimeError):validate(r)
    def test_wrong_named_time_output_or_lifetime_leak_rejected(self):
        r=report();r['clock_cases'][1]['remaining']=-1.
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['native_proxy_gi_refs_released']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_base_static_parent_and_child_startup_profiles_required(self):
        r=report('BlueprintFallback');r['natural_components'][1]['counts']['fallback_localspawn']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_fixture_must_not_replace_default_cycle_or_cancel_native_proxies(self):
        r=report();r['owned_fixture_started_phase_after_cycle_only']=False
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['native_proxy_cancelled_by_fixture']=True
        with self.assertRaises(RuntimeError):validate(r)
