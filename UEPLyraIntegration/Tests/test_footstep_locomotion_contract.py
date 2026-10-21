import unittest
from uep_lyra_weapons.footstep_locomotion_contract import FALSE_FIELDS, PLAN, validate


def report(role='client', profile='Python'):
    rows = [dict(profile=p, name=name, same_real_player_identity=True, same_native_pawn=True,
        native_animation_class_preserved=True, native_movement_distance=280. if name.startswith('walk') else 600.,
        maximum_speed=200. if name.startswith('walk') else 600., stopped_after_release=True,
        native_footstep_actor_calls=0 if role == 'server' else 4, parent_calls=4,
        input_entry='EnhancedInputLocalPlayerSubsystem.InjectInputVectorForAction', actual_animation_sequence_observed=True,
        only_selected_profile_called=True, successful_hits=4, misses_preserve_original_state=True, all_fields_match_native_hit=True,
        niagara_samples=4, all_parameters_match=True) for p, name in PLAN if p == profile]
    result = dict(status='passed', error=None, role=role, requested_profile=profile,
        profile_selected_before_player_creation=True, cases=rows, inventory_and_health_unchanged=True,
        original_animation_class_and_mode_preserved=True, input_released=True,
        profiles_selectors_roots_and_observers_restored=True)
    result.update(dict.fromkeys(FALSE_FIELDS, False))
    return result


class FootstepLocomotionContractTests(unittest.TestCase):
    def test_both_profiles_and_native_roles(self):
        for role in ('server', 'client'):
            for profile in ('BlueprintFallback', 'Python'):
                self.assertEqual(validate(report(role, profile))['real_player_locomotion_cases'], 4)

    def test_requested_profile_must_precede_initial_cache(self):
        value = report();value['profile_selected_before_player_creation'] = False
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_labels_without_actual_profile_dispatch_are_rejected(self):
        value = report();value['cases'][0]['only_selected_profile_called'] = False
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_injected_intent_without_native_displacement_or_speed_is_rejected(self):
        for key in ('native_movement_distance', 'maximum_speed'):
            value = report();value['cases'][0][key] = 0.
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_anim_blueprint_notifies_and_footprint_parameters_are_required(self):
        for key in ('actual_animation_sequence_observed', 'misses_preserve_original_state', 'all_fields_match_native_hit', 'all_parameters_match'):
            value = report();value['cases'][0][key] = False
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_misses_cannot_substitute_for_actual_successful_hits(self):
        value = report();value['cases'][0]['successful_hits'] = 0
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_real_player_pawn_and_animation_class_must_remain(self):
        for key in ('same_real_player_identity', 'same_native_pawn', 'native_animation_class_preserved'):
            value = report();value['cases'][0][key] = False
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_source_server_branch_and_input_release_required(self):
        value = report('server');value['cases'][0]['native_footstep_actor_calls'] = 1
        with self.assertRaises(RuntimeError):
            validate(value)
        value = report();value['input_released'] = False
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_no_playback_replay_or_physical_keyboard_claim(self):
        for key in FALSE_FIELDS:
            value = report();value[key] = True
            with self.assertRaises(RuntimeError):
                validate(value)
