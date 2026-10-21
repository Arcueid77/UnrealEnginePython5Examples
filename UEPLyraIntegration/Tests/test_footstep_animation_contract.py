import copy
import unittest
from uep_lyra_weapons.footstep_animation_contract import FALSE_FIELDS, validate


def report(role='client'):
    rows = []
    for profile in ('BlueprintFallback', 'Python'):
        for index, count in enumerate((6, 4, 6, 6, 6)):
            row = dict(profile=profile, sequence_index=index, expected_context_notifies=count,
                playback_entry='SkeletalMeshComponent.PlayAnimation', single_node_asset_matches=True,
                native_position_advanced=True, native_playback_completed=True, parent_calls=count,
                input_sequence_and_bones_match_original=True, parent_profile_only=True,
                footstep_calls=0 if role == 'server' else count, no_footstep_spawned=role == 'server',
                footstep_profile_only=True, all_native_traces_hit_owned_floor=True,
                all_source_fields_match_native_payload=True, niagara_parameter_samples=count,
                all_niagara_parameters_match_fields=True, native_after_delay_observed=True,
                after_delay_source_validity_branch_preserved=True, after_delay_since_last_motion=3., maximum_world_delta=1./60.)
            rows.append(row)
    result = dict(status='passed', error=None, role=role, native_is_server=role == 'server',
        native_mode='ListenServer' if role == 'server' else 'Client', cases=rows,
        primary_player_unchanged=True, owned_objects_profiles_and_roots_restored=True,
        original_profile_classes_restored=True, native_animation_hashes_unchanged=True)
    result.update(dict.fromkeys(FALSE_FIELDS, False))
    return result


class FootstepAnimationContractTests(unittest.TestCase):
    def test_actual_server_and_client_matrices(self):
        for role in ('server', 'client'):
            self.assertEqual(validate(report(role))['native_context_notifies'], 56)

    def test_playback_entry_without_native_advancement_is_rejected(self):
        for key in ('native_position_advanced', 'native_playback_completed', 'single_node_asset_matches'):
            result = report();result['cases'][0][key] = False
            with self.assertRaises(RuntimeError):
                validate(result)

    def test_missing_or_double_interface_delivery_is_rejected(self):
        for count in (5, 7):
            result = report();result['cases'][0]['parent_calls'] = count
            with self.assertRaises(RuntimeError):
                validate(result)

    def test_report_cannot_redefine_original_notify_inventory(self):
        result = report()
        result['cases'][0].update(expected_context_notifies=0, parent_calls=0, footstep_calls=0)
        with self.assertRaises(RuntimeError):
            validate(result)

    def test_server_footprint_or_wrong_profile_is_rejected(self):
        result = report('server');result['cases'][0]['footstep_calls'] = 1
        with self.assertRaises(RuntimeError):
            validate(result)
        result = report();result['cases'][0]['footstep_profile_only'] = False
        with self.assertRaises(RuntimeError):
            validate(result)

    def test_real_trace_and_native_parameter_outcomes_required(self):
        for key in ('all_native_traces_hit_owned_floor', 'all_source_fields_match_native_payload', 'all_niagara_parameters_match_fields'):
            result = report();result['cases'][0][key] = False
            with self.assertRaises(RuntimeError):
                validate(result)

    def test_original_native_delay_boundary_is_not_widened(self):
        for elapsed in (2.5, 3.5, float('nan')):
            result = report();result['cases'][0]['after_delay_since_last_motion'] = elapsed
            with self.assertRaises(RuntimeError):
                validate(result)

    def test_native_validity_cleanup_branch_is_required(self):
        result = report();result['cases'][0]['after_delay_source_validity_branch_preserved'] = False
        with self.assertRaises(RuntimeError):
            validate(result)

    def test_callback_replay_and_broader_claims_are_rejected(self):
        for key in FALSE_FIELDS:
            result = report();result[key] = True
            with self.assertRaises(RuntimeError):
                validate(result)
