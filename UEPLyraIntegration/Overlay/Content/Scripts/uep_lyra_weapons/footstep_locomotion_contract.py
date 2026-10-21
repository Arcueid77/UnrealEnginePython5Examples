"""Native Enhanced Input -> actual player movement/AnimBP -> footstep proof."""
import argparse, json
from pathlib import Path
from .hero_burst_cue_contract import require

PLAN = [(profile, name) for profile in ('BlueprintFallback', 'Python')
        for name in ('walk-forward', 'walk-back', 'jog-forward', 'jog-back')]
FALSE_FIELDS = ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested',
    'audio_playback_tested', 'physical_keyboard_tested', 'animation_playback_called',
    'animation_position_written', 'animation_assets_modified', 'motion_callbacks_called_by_fixture',
    'notify_callbacks_replayed', 'movement_input_receiver_called_by_fixture', 'velocity_or_movement_mode_written')


def validate(report):
    require(report['status'] == 'passed' and report['error'] is None and report['role'] in ('server', 'client'), 'normal locomotion validation failed')
    for key in FALSE_FIELDS:
        require(report[key] is False, 'locomotion overclaim: '+key)
    for key in ('inventory_and_health_unchanged', 'original_animation_class_and_mode_preserved',
                'input_released', 'profiles_selectors_roots_and_observers_restored'):
        require(report[key], 'locomotion cleanup missing: '+key)
    require(report['requested_profile'] in ('BlueprintFallback', 'Python') and report['profile_selected_before_player_creation'], 'normal-play profile must precede initial router caching')
    expected = [row for row in PLAN if row[0] == report['requested_profile']]
    require([(r['profile'], r['name']) for r in report['cases']] == expected, 'normal locomotion profile/direction matrix incomplete')
    for row in report['cases']:
        require(row['same_real_player_identity'] and row['same_native_pawn'] and row['native_animation_class_preserved'], 'actual playable character changed')
        require(row['native_movement_distance'] > 40. and row['maximum_speed'] > (50. if row['name'].startswith('walk') else 250.), 'native walking/jogging did not advance')
        require(row['stopped_after_release'], 'input release did not stop native movement')
        if report['role'] == 'server':
            require(row['native_footstep_actor_calls'] == 0, 'original native server no-effect branch changed')
        if report['role'] == 'client':
            require(row['input_entry'] == 'EnhancedInputLocalPlayerSubsystem.InjectInputVectorForAction' and row['parent_calls'] >= 1 and row['native_footstep_actor_calls'] == row['parent_calls'], 'normal input/AnimBP notify forwarding missing')
            require(row['actual_animation_sequence_observed'] and row['only_selected_profile_called'] and row['successful_hits'] >= 1 and row['misses_preserve_original_state'] and row['all_fields_match_native_hit'] and row['niagara_samples'] >= 1 and row['all_parameters_match'], 'native locomotion hit/miss footprint semantics missing')
    return dict(status='passed', role=report['role'], profile=report['requested_profile'], real_player_locomotion_cases=len(expected), full_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--report', required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
