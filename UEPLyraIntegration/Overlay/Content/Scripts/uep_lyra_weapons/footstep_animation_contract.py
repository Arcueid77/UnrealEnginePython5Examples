"""Actual native animation -> context notify -> parent -> footstep evidence gate."""
import argparse, json, math
from pathlib import Path
from .hero_burst_cue_contract import require

FALSE_FIELDS = ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested',
    'audio_playback_tested', 'animation_assets_modified', 'notify_callbacks_replayed',
    'motion_callbacks_called_by_fixture', 'animation_position_written', 'native_timer_properties_written')
NOTIFY_COUNTS = (6, 4, 6, 6, 6)


def validate(report):
    require(report['status'] == 'passed' and report['error'] is None, 'native footstep animation validation failed')
    require(report['role'] in ('server', 'client') and report['native_is_server'] is (report['role'] == 'server'), 'real server/client world required')
    require(report['native_mode'] == ('ListenServer' if report['role'] == 'server' else 'Client'), 'native world mode differs')
    for key in FALSE_FIELDS:
        require(report[key] is False, 'footstep animation overclaim: '+key)
    for key in ('primary_player_unchanged', 'owned_objects_profiles_and_roots_restored', 'original_profile_classes_restored', 'native_animation_hashes_unchanged'):
        require(report[key] is True, 'animation cleanup/provenance missing: '+key)
    require(len(report['cases']) == 10 and [(r['profile'], r['sequence_index']) for r in report['cases']] == [(p, i) for p in ('BlueprintFallback', 'Python') for i in range(5)], 'original animation/profile matrix incomplete')
    for row in report['cases']:
        require(row['expected_context_notifies'] == NOTIFY_COUNTS[row['sequence_index']], 'original native notify count differs')
        require(row['playback_entry'] == 'SkeletalMeshComponent.PlayAnimation' and row['single_node_asset_matches'] and row['native_position_advanced'] and row['native_playback_completed'], 'actual native animation advancement missing')
        require(row['parent_calls'] == row['expected_context_notifies'] and row['input_sequence_and_bones_match_original'] and row['parent_profile_only'], 'original notify/interface/parent delivery differs')
        if report['role'] == 'server':
            require(row['footstep_calls'] == 0 and row['no_footstep_spawned'], 'original server no-op branch changed')
        else:
            require(row['footstep_calls'] == row['expected_context_notifies'] and row['footstep_profile_only'], 'native parent did not forward exactly once')
            require(row['all_native_traces_hit_owned_floor'] and row['all_source_fields_match_native_payload'] and row['niagara_parameter_samples'] > 0 and row['all_niagara_parameters_match_fields'], 'original trace/footprint native payload differs')
            require(row['native_after_delay_observed'] and row['after_delay_source_validity_branch_preserved'], 'original delayed cleanup continuation missing')
            elapsed = row['after_delay_since_last_motion'];delta = row['maximum_world_delta']
            require(math.isfinite(elapsed) and 3.-delta-.001 <= elapsed <= 3.+2.*delta+.15, 'original retriggerable three-second delay differs')
    return dict(status='passed', role=report['role'], natural_animation_cases=10,
        native_context_notifies=sum(row['parent_calls'] for row in report['cases']), full_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--report', required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
