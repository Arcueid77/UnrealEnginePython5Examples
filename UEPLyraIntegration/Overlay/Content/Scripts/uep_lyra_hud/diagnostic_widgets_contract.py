"""Require same-frame native performance pairs and original localized UI text."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','graph_pixels_tested','culture_switch_tested','native_tick_replayed','stat_cache_written','controller_or_user_subsystem_state_written','login_requested','health_properties_written')
TRUE_FIELDS=('same_frame_performance_pairs_match','native_build_text_and_localized_history_match','native_watermark_available_and_missing_controller_cases_match','all_widget_roots_and_profile_selectors_restored','original_live_player_health_unchanged')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native diagnostic widgets failed')
    for k in FALSE_FIELDS:require(r[k] is False,'diagnostic scope overclaim: '+k)
    for k in TRUE_FIELDS:require(r[k] is True,'diagnostic parity/cleanup missing: '+k)
    require(r['native_cached_stat_subsystem_valid'] is True,'native performance subsystem not active')
    require(r['same_frame_performance_cases']==8 and r['native_performance_tick_observations']>=24,'same-frame performance matrix incomplete')
    require(r['native_format_value_cases']==24 and r['native_format_fractional_digit_variants']==3,'native numeric formatting matrix incomplete')
    require(r['native_watermark_player_cases']==4 and r['native_missing_controller_localized_status_verified'] is True,'native watermark matrix incomplete')
    require(r['native_valid_user_branch_exercised'] in (True,False),'available CommonUser branch evidence missing')
    return dict(status='passed',same_frame_performance_cases=8,native_format_value_cases=24,native_watermark_player_cases=4,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
