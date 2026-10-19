"""Native constructor/parameter/activation/delegation and retained-scope evidence."""
import unittest
from uep_lyra_world.control_point_helpers_contract import PLAN,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',natural_map_volumes=3,natural_map_python_construction=3,pairs=[],helper_cases=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','construction_replayed','overlap_replayed','timeline_callbacks_replayed','remaining_volume_business_migrated','health_properties_written'):r[k]=False
    for k in ('owned_actors_destroyed','scoring_arrays_restored','original_health_unchanged','production_profiles_restored'):r[k]=True
    for area,duration in PLAN:
        state=dict(scale=[a/10. for a in area],location=[0.,0.,area[2]*5.+1.],offset=[area[0]*5.,area[1]*5.,-area[0]*5.,-area[1]*5.],ribbon=0.,lifetime=duration)
        observations=[dict(before=False,after_first=True,after_second=True,after_direct_native=True,registered=True,system='native-system',helper_evidence=dict(activations=1)) for _ in range(2)]
        r['pairs'].append(dict(area=area,constructor_entries=[1,1],initial_states=[state,state.copy()],paired_native_state_matches=True,fixture_niagara_scalability_disabled_and_solo=True,counter_active_after_two_checks=True,counter_check_entries=[2,2],counter_activation_observations=observations))
        for p in ('BlueprintFallback','Python'):r['helper_cases'].append(dict(profile=p,recaptured=2,contested=-1,recapture_entries=1,contest_entries=1))
    return r


class HelpersContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_constructor_pairs'],3)
    def test_natural_original_map_construction_required(self):
        r=report();r['natural_map_python_construction']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_relative_height_must_follow_post_scale_source_value(self):
        r=report();r['pairs'][0]['initial_states'][0]['location'][2]=0.
        with self.assertRaises(RuntimeError):validate(r)
    def test_niagara_offset_signs_and_components_required(self):
        r=report();r['pairs'][0]['initial_states'][0]['offset'][2]*=-1
        with self.assertRaises(RuntimeError):validate(r)
    def test_actual_counter_activation_required(self):
        r=report();r['pairs'][0]['counter_activation_observations'][0]['after_first']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_original_native_deferred_inactive_outcome_is_preserved(self):
        r=report()
        for x in r['pairs'][0]['counter_activation_observations']:
            x.update(after_first=False,after_second=False,after_direct_native=False);x['helper_evidence']['activations']=2
        self.assertEqual(validate(r)['native_constructor_pairs'],3)
    def test_active_counter_is_not_restarted_by_second_check(self):
        r=report();r['pairs'][0]['counter_activation_observations'][1]['helper_evidence']['activations']=2
        with self.assertRaises(RuntimeError):validate(r)
    def test_scoring_contest_uses_minus_one(self):
        r=report();r['helper_cases'][0]['contested']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_source_arrays_restored(self):
        r=report();r['scoring_arrays_restored']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_remaining_volume_or_replay_cannot_be_claimed(self):
        for k in ('remaining_volume_business_migrated','construction_replayed','network_acceptance'):
            r=report();r[k]=True
            with self.subTest(key=k),self.assertRaises(RuntimeError):validate(r)
