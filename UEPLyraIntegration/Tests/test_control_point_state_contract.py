"""Require real collision delivery, native capture and unchanged pending scope."""
import copy
import unittest
from uep_lyra_world.control_point_state_contract import PROFILES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',natural_map_volumes=3,natural_map_python_ready=3,cases=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','overlap_callbacks_replayed','timeline_callbacks_replayed','pawn_arrays_written_by_fixture','health_properties_written','timeline_update_finish_rpc_vfx_audio_business_migrated'):r[k]=False
    for k in ('owned_actors_destroyed','source_scoring_arrays_restored','original_health_unchanged','production_profiles_restored'):r[k]=True
    for p in PROFILES:
        stages=[dict(name='one-enter',teams=[1],point_owner=-1,playing=True),dict(name='mixed',teams=[1,2],point_owner=-1,reversing=True),dict(name='capture-one',owner=1,point_owner=1,teams=[1]),dict(name='empty',pawns=[],owner=1,point_owner=1),dict(name='capture-two',owner=2,point_owner=2,teams=[2]),dict(name='final-empty',pawns=[],owner=2,point_owner=2)]
        r['cases'].append(dict(profile=p,ready_entries=1,native_rate=1.,stages=stages,final_enter_entries=3,final_exit_entries=3))
    return r


class PointStateContractTests(unittest.TestCase):
    def test_complete_physical_scenarios(self):self.assertEqual(validate(report())['actual_overlap_stages'],12)
    def test_natural_experience_callback_required(self):
        r=report();r['natural_map_python_ready']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_mixed_teams_must_reverse_same_native_clock(self):
        r=report();r['cases'][0]['stages'][1]['reversing']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_finish_updates_actor_and_scoring_owner(self):
        r=report();r['cases'][0]['stages'][2]['point_owner']=-1
        with self.assertRaises(RuntimeError):validate(r)
    def test_empty_point_keeps_existing_owner(self):
        r=report();r['cases'][0]['stages'][3]['owner']=-1
        with self.assertRaises(RuntimeError):validate(r)
    def test_enter_and_exit_callbacks_must_actually_arrive(self):
        r=report();r['cases'][0]['final_exit_entries']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_no_array_writes_replay_or_future_business_claim(self):
        for k in ('pawn_arrays_written_by_fixture','overlap_callbacks_replayed','timeline_update_finish_rpc_vfx_audio_business_migrated'):
            r=report();r[k]=True
            with self.subTest(key=k),self.assertRaises(RuntimeError):validate(r)
    def test_source_scoring_arrays_restored(self):
        r=report();r['source_scoring_arrays_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
