"""Native curves, actual parameters, profile switches and manager evidence gates."""
import unittest
from uep_lyra_weapons.hero_burst_cue_contract import validate


def report():
    value=dict(status='passed',error=None,native_mode='Standalone',pairs=[],manager_cases=[])
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','native_timer_properties_written','health_properties_written','identical_particle_lifetimes_claimed'):value[key]=False
    for key in ('owned_actors_destroyed','owned_effects_removed','production_profiles_restored','original_health_unchanged'):value[key]=True
    for kind in ('dash','death'):
        for i in range(5):value['pairs'].append(dict(kind=kind,switch=i==4,initial_burst_entries=[1,1],spawn_counts=[2,2],native_start_values_match=True,native_system_configuration_matches=True,natural_samples=4,all_sample_pairs_match=True,all_samples_match_native_curve_parameters=True,finished_entries=[1,1],effect_arrays_cleared=True,all_effects_deactivated=True,native_playback_positions_match=True,completed_after_configured_duration=True,profile_switch_observed=i==4,finish_profiles=['Python','BlueprintFallback'] if i==4 else ['BlueprintFallback','Python'],root_decals_destroyed_child_decals_retained=True,final_edge_glow_zero=True))
        value['manager_cases'].append(dict(kind=kind,default_python_burst_entry=True,native_timeline_playing=True,effects_started=True))
    return value


class HeroBurstContractTests(unittest.TestCase):
    def test_complete_native_timeline_matrix(self):self.assertEqual(validate(report())['actual_native_timelines'],20)
    def test_missing_actual_child_and_ignore_filter_rejected(self):
        value=report();value['pairs'][0]['spawn_counts']=[3,3]
        with self.assertRaises(RuntimeError):validate(value)
    def test_shader_or_niagara_curve_mismatch_rejected(self):
        value=report();value['pairs'][0]['all_samples_match_native_curve_parameters']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_paired_state_and_clock_must_match(self):
        for key in ('all_sample_pairs_match','native_playback_positions_match'):
            value=report();value['pairs'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_live_profile_switch_must_affect_finish_dispatch(self):
        value=report();value['pairs'][4]['finish_profiles']=['BlueprintFallback','Python']
        with self.assertRaises(RuntimeError):validate(value)
    def test_source_decal_child_scope_and_glow_reset_required(self):
        value=report();value['pairs'][-1]['root_decals_destroyed_child_decals_retained']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_actual_finish_and_cleanup_required(self):
        value=report();value['pairs'][0]['effect_arrays_cleared']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_real_manager_default_python_required(self):
        value=report();value['manager_cases'][0]['default_python_burst_entry']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_no_python_clock_or_broad_visual_acceptance(self):
        for key in ('python_timeline_clock_added','timeline_callbacks_replayed','pixels_tested','identical_particle_lifetimes_claimed'):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
