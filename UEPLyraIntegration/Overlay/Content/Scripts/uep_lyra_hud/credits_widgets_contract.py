"""Require original natural Delay/TimerManager callbacks and visibility semantics."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_tap_input_tested','native_delay_or_timer_callback_replayed','new_business_ticker_or_python_timer_used','production_timer_deactivation_cleanup_added','health_properties_written')
TRUE_FIELDS=('source_python_state_pairs_match','original_hundred_line_construct_rich_text_matches','actual_native_remount_appends_another_hundred_lines','native_const_focus_remains_null','native_one_second_delay_then_desired_size_capture_and_timer','native_looping_timer_callbacks_advance_scroll','native_endpoint_clears_handle_resets_scroll_and_collapses_bar','native_end_does_not_rearm_timer','rooted_deactivated_removed_widget_keeps_original_timer','only_owned_timers_explicitly_stopped_by_fixture','all_widget_roots_and_profile_selectors_restored','original_live_player_health_unchanged')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native credits widgets failed')
    for k in FALSE_FIELDS:require(r[k] is False,'credits scope overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'credits evidence missing: '+k)
    require(r['native_timer_callbacks_per_profile_min']>=3 and r['visibility_cases']==10 and r['manual_scroll_edge_cases']==3,'credits native/edge matrices incomplete')
    require(r['owned_fixture_scroll_speed_overridden'] is True and r['owned_fixture_endpoint_overridden_after_capture'] is True,'owned fixture bounds not declared')
    return dict(status='passed',native_profile_matrices=2,natural_timer_min_callbacks_per_profile=3,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
