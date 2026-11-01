"""Closed gates for native interaction interfaces, indicators, GAS and cleanup."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require


def validate(report):
    require(report['status']=='passed' and report['error'] is None,'native interaction runtime failed')
    require([c['profile'] for c in report['cases']]==['NativeFallback','Python'],'native/Python interaction pair missing')
    for case in report['cases']:
        require(all(case['matrix'].values()),'native interaction boundary/indicator/first-choice matrix failed')
        require(case['native_task_counts']==dict(scan=1,wait=1,nearby=1,release=0),'native scan/input/grant task ownership differs')
        for key in ('native_input_triggered','out_of_range_cleared','empty_input_ignored','profile_switch_dispatched','cancel_stopped_tasks','owned_context_destroyed'):require(case[key],'interaction lifecycle failed: '+key)
        selected='python_' if case['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_'
        require(case['metrics'][selected+'update']>0 and case['metrics'][selected+'trigger']>=3 and case['metrics'][other+'trigger']==1,'interaction rule routing or pending switch differs')
        require(case['trigger_count']==3 and case['customize_count']==3,'native GAS/interface customization event counts differ')
    require(report['primary_player_inventory_and_health_unchanged'] and report['selectors_and_owned_roots_restored'],'interaction fixture leaked or changed primary player')
    require(not any(report[k] for k in ('synthetic_target_events','native_interface_replaced','native_scan_task_replaced','network_acceptance','visible_rendering_acceptance')),'native interaction runtime overclaims')
    return dict(status='passed',profiles=2,indicator_and_first_option_matrix=True,native_customized_payload_and_actor_info=True,native_input_scan_grant_and_cancel=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);print(json.dumps(validate(json.loads(p.parse_args().report.read_text(encoding='utf-8-sig'))),indent=2))
