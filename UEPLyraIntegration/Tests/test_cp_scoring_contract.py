"""Reject absent CP-map startup, wrong sentinel/majority and fake clock/phase."""
import copy
import unittest
from uep_lyra_weapons.cp_scoring_contract import PROFILES,TIMER_CASES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',natural_startup=dict(python_Begin=1,python_GameStarted=1,python_Register=3),actual_point_count=3,controlled_victory_receiver_for_intermediate_timer_cases=True,array_cases=[],capture_cases=[],query_cases=[],palette_cases=[],timer_cases=[],cue_cases=[],actual_victory=dict(winner=2,phase_active=True,manager_cue_count=1,timer_active=False,handle_valid=False))
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callback_replayed','timer_callback_replayed','physical_capture_overlap_tested','health_properties_written'):r[k]=False
    for k in ('owned_actors_destroyed','owned_components_destroyed','native_scores_restored','production_profiles_restored'):r[k]=True
    for p in PROFILES:
        r['array_cases'].append(dict(profile=p,point_count=3,initial=[-1,-1,-1],recaptured=[2,-1,-1],contested=[-1,-1,-1]));r['capture_cases'].append(dict(profile=p,owners=[2],stat_deltas=[0,2],native_gate_entries=1))
        for team in (-1,1,2):r['query_cases'].append(dict(profile=p,kind='status',team=team,outputs=[1,0,3] if team==-1 else [1,1,2]))
        for s in (4,5,6):r['query_cases'].append(dict(profile=p,kind='score',score=s,outputs=[s,5,s>=5]))
        r['palette_cases'].append(dict(profile=p,colors=[[.2,.4,.6,.8],[.7,.5,.3,1.],[.2,.4,.6,.8]],index=2,cached_teams=[7,8]));r['cue_cases'].append(dict(profile=p,manager_actor_count=1,cleared=True))
    for p,owners,w in TIMER_CASES:r['timer_cases'].append(dict(profile=p,owners=owners,expected=w,ticks=1,scores=[0,0] if w==0 else [1,0] if w==1 else [0,1],leading=9 if w==0 else w,winners=[] if w==0 else [w],timer_active=False,handle_valid=False))
    return r


class CPContractTests(unittest.TestCase):
    def test_complete_native_cp_matrix(self):self.assertEqual(validate(report())['native_timer_cases'],6)
    def test_natural_volume_registration_required(self):
        r=report();r['natural_startup']['python_Register']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_duplicate_registration_is_not_deduplicated(self):
        r=report();r['array_cases'][0]['point_count']=2
        with self.assertRaises(RuntimeError):validate(r)
    def test_first_pawn_team_and_duplicate_capture_awards_required(self):
        r=report();r['capture_cases'][0]['stat_deltas']=[1,1]
        with self.assertRaises(RuntimeError):validate(r)
    def test_score_above_target_is_victory(self):
        r=report();r['query_cases'][5]['outputs'][2]=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_palette_query_does_not_advance_cached_team_again(self):
        r=report();r['palette_cases'][0]['index']=3
        with self.assertRaises(RuntimeError):validate(r)
    def test_tie_preserves_previous_leader(self):
        r=report();r['timer_cases'][0]['leading']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_majority_only_adds_one_point(self):
        r=report();r['timer_cases'][1]['scores']=[2,0]
        with self.assertRaises(RuntimeError):validate(r)
    def test_actual_postgame_stops_and_invalidates_timer(self):
        r=report();r['actual_victory']['handle_valid']=True
        with self.assertRaises(RuntimeError):validate(r)
    def test_physical_overlap_or_network_cannot_be_claimed(self):
        for key in ('physical_capture_overlap_tested','timer_callback_replayed','network_acceptance'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
