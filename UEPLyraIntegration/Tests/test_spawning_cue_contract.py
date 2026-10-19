"""Reject missing native time, material, listener and lifetime evidence."""
import copy
import unittest
from uep_lyra_weapons.spawning_cue_contract import PLAN,validate


def report():
    value=dict(status='passed',error=None,native_mode='Standalone',pairs=[],manager_cases=[dict(default_profile='Python',application_entries=1,python_application=True,native_watcher_active=True,watcher_cancelled=True,cache_empty=True)])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','parts_delegate_broadcast_by_fixture','team_properties_written','health_properties_written'):value[k]=False
    for k in ('owned_actors_destroyed','owned_effects_removed','owned_watchers_cancelled','production_profiles_restored','original_health_unchanged'):value[k]=True
    for name,duration,parts,team,switch,late in PLAN:
        state=dict(time=1.,team=[1.,0.,.5,1.],fx_count=3,map_count=3,materials=[dict(slots=0,age=.2),dict(slots=1,age=1.)],fx=[dict(duration=duration,body=[1.,0.,.5],timeline=1.) for _ in range(3)])
        row=dict(name=name,initial_application_entries=[1,1],initial_team_entries=[1,1],initial_fx_counts=[2,2],watchers_native_active=True,initial_system_configuration=True,natural_samples=3,all_samples_match=True,clocks_match=True,part_add_callback_deltas=[2,2],repeat_discovery_does_not_duplicate_effects=True,native_part_callback_entries_match=[2,2],native_team_callback_entries_match=[2,2],switched=switch,late_retry_rebound_after_removal=late,team_change_callback_deltas=[0,0] if late else [1,1],before_final_removal=[state,copy.deepcopy(state)])
        for k in ('removal_cleared_caches','removal_cancelled_watchers','removal_retained_source_handles','removal_did_not_stop_native_clock','native_parts_unbound_after_removal','native_team_unbound_after_removal','source_arrays_and_map_empty'):row[k]=True
        row['removal_observations']=[dict(clear=True,cancel=True,retain=True,clock=True) for _ in range(2 if late else 1)]
        value['pairs'].append(row)
    return value


class SpawningContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_timelines'],8)
    def test_duplicate_binding_or_missing_parts_callback_rejected(self):
        value=report();value['pairs'][0]['part_add_callback_deltas']=[4,2]
        with self.assertRaises(RuntimeError):validate(value)
    def test_clock_and_material_evidence_required(self):
        for key in ('all_samples_match','clocks_match','initial_system_configuration'):
            value=report();value['pairs'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_uncancelled_team_watcher_rejected(self):
        value=report();value['pairs'][0]['native_team_unbound_after_removal']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_late_native_retry_must_retain_source_behavior(self):
        value=report();value['pairs'][-1]['late_retry_rebound_after_removal']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_source_removal_must_retain_handles_and_clock(self):
        for key in ('removal_retained_source_handles','removal_did_not_stop_native_clock'):
            value=report();value['pairs'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_final_native_niagara_parameters_checked_against_source(self):
        value=report()
        for state in value['pairs'][0]['before_final_removal']:state['fx'][0]['duration']=5.
        with self.assertRaises(RuntimeError):validate(value)
    def test_real_manager_default_profile_required(self):
        value=report();value['manager_cases'][0]['default_profile']='BlueprintFallback'
        with self.assertRaises(RuntimeError):validate(value)
    def test_early_removal_cannot_be_hidden_by_later_success(self):
        value=report();value['pairs'][-1]['removal_observations'][0]['clock']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_broad_acceptance_and_callback_replay_rejected(self):
        for key in ('full_acceptance','network_acceptance','timeline_callbacks_replayed','parts_delegate_broadcast_by_fixture'):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
