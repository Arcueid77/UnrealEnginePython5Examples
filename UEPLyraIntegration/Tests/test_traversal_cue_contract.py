"""Require genuine native device state, local/world conventions and manager paths."""
import copy
import unittest
from uep_lyra_weapons.traversal_cue_contract import validate


def report():
    value=dict(status='passed',error=None,native_mode='Standalone',launcher_pairs=[],teleport_pairs=[],wrong_causer_preserves_partial_assignment=True,real_default_python_manager_tags=2)
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','health_properties_written'):value[k]=False
    for k in ('owned_targets_and_devices_destroyed','owned_effects_removed','original_health_unchanged','production_profiles_restored'):value[k]=True
    for i in range(4):value['launcher_pairs'].append(dict(destroy_target=i==3,burst_entries=[1,1],spawn_counts=[2,2],initial_configuration_match=True,natural_samples=5,all_material_and_raw_niagara_values_match=True,paired_clock_and_state_match=True,source_curve_distinction_observed=True,arrays_cleared=True,all_effects_naturally_inactive=True,finish_glow_zero=True,timeline_stopped_after_target_destroy=i==3,clear_entries=[1,1]))
    for i in range(6):
        state=dict(count=i,positions=[[1.,2.,3.]])
        value['teleport_pairs'].append(dict(original=copy.deepcopy(state),python=state,burst_entries=[1,1],bursts=1,all_native_parameters_match_source=True,native_exit_particle_count=2,entry_count_matches_native_int32=True,destination_count_and_direction_match=True))
    return value


class TraversalContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_teleporter_pairs'],6)
    def test_shader_curve_must_not_be_substituted_for_raw_niagara_time(self):
        value=report();value['launcher_pairs'][0]['all_material_and_raw_niagara_values_match']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_curve_distinction_and_natural_clock_evidence_required(self):
        value=report();value['launcher_pairs'][0]['source_curve_distinction_observed']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_destroyed_target_must_stop_timeline(self):
        value=report();value['launcher_pairs'][-1]['timeline_stopped_after_target_destroy']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_actual_counter_and_direction_required(self):
        value=report();value['teleport_pairs'][0]['destination_count_and_direction_match']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_portal_world_position_mismatch_rejected(self):
        value=report();value['teleport_pairs'][0]['python']['positions'][0][2]=999.
        with self.assertRaises(RuntimeError):validate(value)
    def test_source_append_behavior_required(self):
        value=report();value['teleport_pairs'][-1]['bursts']=2;value['teleport_pairs'][-1]['burst_entries']=[2,2]
        with self.assertRaises(RuntimeError):validate(value)
    def test_real_manager_and_partial_causer_guard_required(self):
        value=report();value['real_default_python_manager_tags']=1
        with self.assertRaises(RuntimeError):validate(value)
    def test_original_health_and_scope_required(self):
        value=report();value['original_health_unchanged']=False
        with self.assertRaises(RuntimeError):validate(value)
        value=report();value['network_acceptance']=True
        with self.assertRaises(RuntimeError):validate(value)
