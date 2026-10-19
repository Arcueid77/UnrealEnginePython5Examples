"""Reject nominal-only timer/notify/phase evidence and weakened equality rules."""
import unittest
from uep_lyra_weapons.tdm_scoring_contract import PROFILES,COUNTDOWN_CASES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',natural_startup=dict(python_Begin=1,python_GameStarted=1),controlled_victory_receiver_used_for_decision_matrix=True,query_cases=[],countdown_cases=[],damage_cases=[],cue_cases=[],message_cases=[],restart_cases=[],actual_victory=dict(winning_team=2,phase_active=True,cue_tag='GameplayCue.ShooterGame.UserMessage.MatchDecided',manager_cue_count=1,python_victory_entries=1))
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callback_replayed','timer_callbacks_replayed','health_properties_written'):r[k]=False
    for k in ('owned_actors_destroyed','owned_components_destroyed','diagnostic_sender_root_removed','native_scores_restored','production_profiles_restored'):r[k]=True
    for p in PROFILES:
        for s in (14,15,16):r['query_cases'].append(dict(profile=p,score=s,outputs=[s,15,s==15],native_target_notify_count=1))
        r['damage_cases'].append(dict(profile=p,initial_count=0,after_apply=1,after_remove=1,fixture_effects_restored=True));r['cue_cases'].append(dict(profile=p,stored_tag='tag',actual_manager_actors=1,cleared=True));r['restart_cases'].append(dict(profile=p,pawn_still_valid=True,entries=1))
        for w in (1,2):r['message_cases'].append(dict(profile=p,winner=w,actual_winners=[w],team_scores=[5,4] if w==1 else [4,5]))
    for p,a,b,w in COUNTDOWN_CASES:r['countdown_cases'].append(dict(profile=p,scores=[a,b],winners=[w],notifications=[1.,0.],time=0.,timer_active=False,handle_valid=False,gate_entries=1,cached_scores=[a,b]))
    return r


class TDMContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_countdown_cases'],6)
    def test_above_target_is_not_a_victory(self):
        r=report();r['query_cases'][2]['outputs'][2]=True
        with self.assertRaises(RuntimeError):validate(r)
    def test_real_native_notify_required(self):
        r=report();r['query_cases'][0]['native_target_notify_count']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_expiry_must_clear_and_invalidate_timer(self):
        r=report();r['countdown_cases'][0]['handle_valid']=True
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_countdown_repnotify_values_required(self):
        r=report();r['countdown_cases'][0]['notifications']=[0.]
        with self.assertRaises(RuntimeError):validate(r)
    def test_fixture_immunity_effects_must_be_removed(self):
        r=report();r['damage_cases'][0]['fixture_effects_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_actual_message_cue_manager_required(self):
        r=report();r['cue_cases'][0]['actual_manager_actors']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_real_gms_elimination_must_reach_victory(self):
        r=report();r['message_cases'][0]['actual_winners']=[]
        with self.assertRaises(RuntimeError):validate(r)
    def test_final_postgame_must_be_real(self):
        r=report();r['actual_victory']['phase_active']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_timer_replay_or_broad_acceptance_rejected(self):
        for key in ('timer_callbacks_replayed','network_acceptance','health_properties_written'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
