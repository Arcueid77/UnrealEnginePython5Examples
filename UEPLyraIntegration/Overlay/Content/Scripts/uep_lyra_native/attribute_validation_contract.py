"""Native attribute clamp mutation fixture and separate unchanged input phase."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.arena_local_input_contract import validate as input_gate


def require(value,message):
    if not value:raise AssertionError(message)


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_clamp_base_values_written_by_fixture'] and r['base_values_restored_before_input_phase'] and r['cpp_selector_restored'] and r['previous_blueprint_python_fixed'],'native attribute fixture/restoration failed')
    input_gate(r['original_input_phase'])
    require(r['original_input_phase']['neutral_slate_gameplay_unchanged'],'neutral Slate setup changed gameplay')
    require(len(r['clamp_cases'])==16 and [row['player'] for row in r['clamp_cases']]==[0]*8+[1]*8,'two local-player clamp owners missing')
    expected=[3.,3.,0.,1.,200.,800.,1.,1.]*2
    require([row['result'] for row in r['clamp_cases']]==expected,'original native GAS clamp values differ')
    calls=r['rule_metrics']['applied'].get('Attribute.Clamp',0)
    require(calls>0 if r['cpp_profile'] in ('AttributePython','Python') else calls==0,'native/Python attribute route differs')
    require(not r['physical_input_tested'] and not r['network_acceptance'],'attribute scope overclaim')
    return dict(status='passed',native_clamp_trials=16,real_local_players=2,native_bomb_input_refund_trials=2,physical_input_tested=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
