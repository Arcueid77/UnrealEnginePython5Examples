"""Style observations extend all accepted five-helper native regression cases."""
import argparse
import json
from pathlib import Path
from .explorer_helpers_contract import validate as helpers_validate,require

CASES=('fresh','reuse','team-null','team-display','legacy-zero')
def validate(r):
    helpers_validate(r)
    require(r['hardware_output_tested'] is False and r['pixels_tested'] is False,'Explorer appearance overclaim')
    require(r['owned_device_markers_and_roots_released'],'native style observer cleanup missing')
    for row in r['characters']:
        require([c['name'] for c in row['style_cases']]==list(CASES),'original style matrix incomplete')
        require(all(c['native_values_match'] for c in row['style_cases']),'native outline/team/legacy values differ')
        require(row['existing_mid_reused_without_new_blend'] and row['nonlocal_outline_is_noop'],'native outline cache/local guard missing')
        require(row['native_device_count_matches_platform_validity'] and row['native_device_evaluations_and_retirement_observed'],'native style device dispatch missing')
    return dict(status='passed',profile=r['profile'],characters=2,style_cases=10,helper_cases=10,whole_characters_migrated=False,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
