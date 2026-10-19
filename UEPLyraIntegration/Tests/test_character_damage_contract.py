"""Reject replaced RNG, missing native effects/RPC boundaries and overclaims."""
import unittest
from uep_lyra_weapons.character_damage_contract import validate


def report():
    value=dict(status='passed',error=None,native_mode='Standalone',weak_cases=[],selector_cases=[],parent_cases=[],timer_cases=[])
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','health_properties_written','native_rng_values_injected','rpc_function_overridden','parent_effects_disabled','native_timer_properties_written'):value[key]=False
    for key in ('production_profiles_restored','music_fields_and_providers_restored','probe_unrooted','original_health_unchanged','owned_material_roots_released','owned_decal_components_removed','number_pop_state_restored'):value[key]=True
    for i in range(24):value['weak_cases'].append(dict(actual=i%4==0,expected=i%4==0,dispatch_entries=1))
    for profile in ('BlueprintFallback','Python'):
        for path in ('direct','blueprint'):
            for i in range(16):value['selector_cases'].append(dict(profile=profile,path=path,returned='native-montage',allowed=['native-montage'],actual_native_group='group',expected_group='group',actual_positive=True,expected_positive=True,dispatch_entries=1))
        for surface in (0,2):
            for decoy in (False,True):value['parent_cases'].append(dict(profile=profile,surface=surface,cue_instigator_decoy=decoy,native_return=False,burst_entries=1,execute_entries=1,rpc_body_entries=1,actual_messages=1,message_target_matches=True,number_pop_added=1,native_pop_value=-5. if surface else 5.,expected_pop_value=-5. if surface else 5.,native_pop_location=[1.,2.,3.],expected_pop_location=[1.,2.,3.],context_instigator_is_local_state=True,selected_montage_in_allowed_set=True,native_character_montage_playing=True,actual_new_decals=1 if surface else 0,decal_attachment_and_native_properties_match=True,actual_lens_updates=1,actual_native_lens_parameters_match=True))
        value['timer_cases'].append(dict(profile=profile,visible_before_deadline=True,native_recycled_after_minimum_lifetime=True,elapsed=5.1))
    value.update(natural_manager_python_burst_entries=1,natural_manager_python_execute_entries=1,natural_manager_typed_message_entries=1)
    return value


class CharacterDamageContractTests(unittest.TestCase):
    def test_complete_native_boundaries(self):self.assertEqual(validate(report())['native_parent_cases'],8)
    def test_native_rng_data_family_must_follow_geometry(self):
        value=report();value['selector_cases'][0]['actual_native_group']='different'
        with self.assertRaises(RuntimeError):validate(value)
    def test_missing_actual_bp_selector_path_rejected(self):
        value=report();value['selector_cases']=[r for r in value['selector_cases'] if r['path']=='direct']
        with self.assertRaises(RuntimeError):validate(value)
    def test_wrong_exact_weak_tag_result_rejected(self):
        value=report();value['weak_cases'][0]['actual']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_actual_native_popup_value_required(self):
        value=report();value['parent_cases'][0]['native_pop_value']=0.
        with self.assertRaises(RuntimeError):validate(value)
    def test_native_popup_must_use_the_hit_location(self):
        value=report();value['parent_cases'][0]['native_pop_location']=[100.,200.,300.]
        with self.assertRaises(RuntimeError):validate(value)
    def test_native_position_comparison_uses_backend_float32_storage(self):
        import struct
        value=report();raw=[-4499.019166608091,7.545330071816023,-301.28548857990336]
        value['parent_cases'][0]['expected_pop_location']=raw;value['parent_cases'][0]['native_pop_location']=list(struct.unpack('<3f',struct.pack('<3f',*raw)))
        self.assertEqual(validate(value)['native_parent_cases'],8)
    def test_parent_rpc_and_message_dispatch_required(self):
        for key in ('burst_entries','execute_entries','rpc_body_entries','actual_messages'):
            value=report();value['parent_cases'][0][key]=0
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_actual_lens_parameters_and_decal_properties_required(self):
        value=report();value['parent_cases'][0]['actual_native_lens_parameters_match']=False
        with self.assertRaises(RuntimeError):validate(value)
        value=report();value['parent_cases'][2]['decal_attachment_and_native_properties_match']=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_native_minimum_lifetime_cannot_be_shortened(self):
        value=report();value['timer_cases'][0]['elapsed']=1.
        with self.assertRaises(RuntimeError):validate(value)
    def test_real_manager_default_python_path_required(self):
        value=report();value['natural_manager_typed_message_entries']=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_unchanged_health_restoration_and_bounded_claims_required(self):
        value=report();value['number_pop_state_restored']=False
        with self.assertRaises(RuntimeError):validate(value)
        value=report();value['network_acceptance']=True
        with self.assertRaises(RuntimeError):validate(value)
