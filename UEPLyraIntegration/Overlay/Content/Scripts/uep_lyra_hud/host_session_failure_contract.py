"""Native invalid-request failures are separate from online-provider failures."""
import argparse
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate(report):
    require(report['status'] == 'passed' and report['error'] is None, 'Host failure runtime did not pass')
    for field in ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested',
                  'physical_button_input_tested', 'online_provider_failure_tested', 'callbacks_replayed', 'health_properties_written'):
        require(report[field] is False, 'Scope overclaim: ' + field)
    require(report['native_mode'] == 'Standalone', 'Standalone native world required')
    require([row['profile'] for row in report['profiles']] == ['BlueprintFallback', 'Python'], 'Both original/Python Profiles required')
    for row in report['profiles']:
        for field in ('native_tile_click_and_spinner', 'selected_experience_invalidated_only_at_prepared_entry',
                      'native_failed_completion_and_error_dialog', 'native_error_ftext_history_preserved',
                      'native_spinner_popped', 'native_acknowledge_button_closed_dialog', 'native_second_failure_did_not_reenter_unbound_widget',
                      'no_late_callbacks_or_world_change'):
            require(row[field] is True, 'Missing native failure observation: ' + field)
        require(row['prepared_calls'] == row['completed_calls'] == row['invalidations'] == 1, 'Duplicate UI failure handling')
        require(row['native_failure_notifications'] == 2, 'Native failure/unbound control missing')
        require(row['exclusive_selected_profile_calls'], 'Python ownership or original baseline is ambiguous')
    require(report['native_failure_notifications'] == 4 and report['source_python_failure_states_match'], 'Failure pair or native control differs')
    require(report['owned_roots_profiles_input_and_loading_class_restored'] and report['profile_methods_restored'] and report['original_gameplay_health_unchanged'], 'Failure cleanup incomplete')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--report', required=True)
    validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))
    print(json.dumps(dict(status='passed', native_failure_profiles=2, native_failure_notifications=4, full_acceptance=False)))
