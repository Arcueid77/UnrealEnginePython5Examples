"""Require native lifecycle, loading delegates, localized format and layout proof."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','culture_switch_tested','physical_dialog_input_tested','native_tick_or_activation_replayed','loading_host_unbind_added','localized_text_roundtripped','health_properties_written')
TRUE_FIELDS=('source_python_state_pairs_match','all_widget_roots_and_profile_selectors_restored','original_loading_content_class_restored','original_live_player_health_unchanged')
ROW_FIELDS=('actual_native_dialog_activation_animation','actual_native_reason_construct_and_ticks','localized_reason_format_history_preserved','actual_native_aspect_construct_and_brush_copy','actual_native_spinner_preconstruct_and_desired_size','loading_host_actual_construct_and_fallback','native_loading_class_change_delegate_once','same_class_direct_callback_creates_new_child','rooted_removed_loading_host_keeps_original_delegate')

def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','native foundation widgets failed')
    for k in FALSE_FIELDS:require(r[k] is False,'foundation widgets scope overclaim: '+k)
    require([p['profile'] for p in r['profiles']]==list(PROFILES),'foundation widgets Profiles incomplete')
    for p in r['profiles']:
        for k in ROW_FIELDS:require(p[k] is True,'foundation widget evidence missing: '+k)
        require(p['aspect_brush_cases']==3 and p['spinner_size_cases']==3 and p['native_reason_ticks']>=3 and p['native_loading_changes']==2,'foundation widget matrix incomplete')
    for k in TRUE_FIELDS:require(r[k] is True,'foundation widget cleanup/parity missing: '+k)
    return dict(status='passed',native_profile_matrices=2,native_widget_trials=10,native_loading_changes=4,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
