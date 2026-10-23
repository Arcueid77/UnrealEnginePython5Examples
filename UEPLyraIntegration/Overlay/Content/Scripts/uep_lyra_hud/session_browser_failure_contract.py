"""Source/Python search failure and pending-screen lifetime, not backend cancel."""
import argparse
import json
from pathlib import Path


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report):
    require(report['status']=='passed' and report['error'] is None, 'Browser failure run failed')
    for field in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_button_input_tested',
                  'online_provider_failure_tested','backend_search_cancelled','callbacks_replayed','health_properties_written'):
        require(report[field] is False, 'Browser scope overclaim: '+field)
    require(report['native_mode']=='Standalone', 'Native Standalone required')
    require([r['profile'] for r in report['profiles']]==['BlueprintFallback','Python'], 'Original/Python comparison missing')
    for row in report['profiles']:
        for field in ('native_initial_search_completed','native_bad_player_failure_dialog','native_error_ftext_history_preserved',
                      'native_acknowledgement_and_refresh_recovery','native_pending_screen_close_matches_original',
                      'native_reactivation_started_distinct_request','native_pending_widget_collected_before_completion',
                      'native_request_completed_without_destroyed_widget_callback','exclusive_selected_profile_calls'):
            require(row[field] is True, 'Missing native browser observation: '+field)
        require(row['native_notification_sequence']==[True,False,True,True], 'Native search/failure/retired-request sequence differs')
        require(row['search_calls']==row['results_calls']==row['unlock_calls']==3, 'Missing or duplicate browser callback')
    for field in ('source_python_states_match','owned_roots_profiles_input_and_loading_class_restored','original_gameplay_health_unchanged'):
        require(report[field] is True, 'Browser failure cleanup/comparison failed: '+field)
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))
    print(json.dumps(dict(status='passed',native_profiles=2,native_bad_player_failures=2,native_successful_requests=6,full_acceptance=False)))
