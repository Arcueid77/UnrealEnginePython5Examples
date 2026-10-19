"""Reject missing feedback, native completion, offline audio and cleanup evidence."""
import unittest
from uep_lyra_world.control_point_feedback_contract import PROFILES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',natural_map_volumes=3,natural_map_python_ready=3,cases=[],timeline_update_finish_rpc_vfx_audio_business_migrated=True)
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','overlap_callbacks_replayed','timeline_callbacks_replayed','pawn_arrays_written_by_fixture','health_properties_written','audio_energy_measured'):r[k]=False
    for k in ('owned_actors_destroyed','source_scoring_arrays_restored','original_health_unchanged','production_profiles_restored','local_movement_tick_restored'):r[k]=True
    for p in PROFILES:
        stages=[dict(name='one-enter',teams=[1],playing=True),dict(name='mixed',teams=[1,2],playing=False,position=0.),dict(name='capture-one',owner=1,point_owner=1),dict(name='empty',pawns=[]),dict(name='capture-two',owner=2,point_owner=2),dict(name='final-empty',pawns=[])]
        audio={k:True for k in ('locally_viewed','entered','exit_parameter_false','stopped_after_delay','friendly_sound','enemy_sound','capture_playing','remote_and_invalid_noop')}
        entries={k:1 for k in ('Meshes','TimelineUpdate','TimelineFinished','EnterAudio','ExitAudio','CaptureAudio','Music','ActivateVFX','CleanVFX')}
        r['cases'].append(dict(profile=p,ready_entries=1,native_rate=1.,stages=stages,samples=30,all_native_feedback_matches=True,sampled_intermediate_curve=True,native_forward_finishes=2,native_reverse_finishes=1,mesh_list_unique_and_existing_preserved=True,light_native_srgb_reference=True,audio=audio,music_local_overlap=True,local_transform_restored=True,entries=entries,diagnostic_fallbacks=0))
    return r


class FeedbackContractTests(unittest.TestCase):
    def test_complete_native_evidence(self):self.assertEqual(validate(report())['native_feedback_samples'],60)
    def test_no_substitute_for_real_intermediate_feedback_or_clock_completion(self):
        for key,value in (('samples',0),('sampled_intermediate_curve',False),('all_native_feedback_matches',False),('native_reverse_finishes',0),('native_forward_finishes',0),('diagnostic_fallbacks',1)):
            r=report();r['cases'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_audio_selection_activity_delay_and_local_guards_required(self):
        for key in report()['cases'][0]['audio']:
            r=report();r['cases'][0]['audio'][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_no_replays_array_writes_or_energy_claim(self):
        for key in ('overlap_callbacks_replayed','timeline_callbacks_replayed','pawn_arrays_written_by_fixture','audio_energy_measured'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_profile_gate_and_production_state_must_be_restored(self):
        r=report();r['cases'][1]['entries']['CaptureAudio']=0
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['local_movement_tick_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
