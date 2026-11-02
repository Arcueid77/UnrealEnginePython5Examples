"""Close native GAS cost comparisons; role fixtures never establish networking."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['kind'] in ('item','player'),'native cost boundary lane failed')
    require(len(report['cases'])==36,'native cost boundary matrix incomplete')
    for name in {r['name'] for r in report['cases']}:
        pair=[r for r in report['cases'] if r['name']==name]
        require(len(pair)==2 and {r['profile'] for r in pair}=={'Python','NativeCostFallback'} and pair[0]['outcome']==pair[1]['outcome'],'native/Python cost boundary differs')
    require(report['fixture_actors_removed'] and report['class_root_restored'] and report['curve_root_released'],'cost boundary fixture leaked')
    require(report['simulated_native_role_fixture'] and not report['actual_network_acceptance'] and not report['raw_actor_info_exposed'] and not report['fixtures_saved'],'cost boundary lane overclaims')
    return dict(status='passed',kind=report['kind'],profiles=2,boundary_scenarios=18,native_gas_owned_ability_instances=True,actual_network_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);a=p.parse_args();print(json.dumps(validate(json.loads(a.report.read_text(encoding='utf-8-sig'))),indent=2))
