"""Actual local prediction/authority interaction and native replicated-event gates."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require


def validate(report):
    require(report['status']=='passed' and report['error'] is None,'native interaction peer failed')
    require(report['native_mode']==('DedicatedServer' if report['peer']=='server' else 'Client'),'actual native peer mode differs')
    require(report['selector_and_root_restored'] and report['fixture_cleanup_complete'],'native interaction network ownership leaked')
    require(not any(report[k] for k in ('synthetic_target_events','target_counter_replication','health_writes','inventory_writes','native_interface_replaced')),'native interaction network uses synthetic outcomes')
    owners=report['owners'] if report['peer']=='server' else {report['peer']:report['owner_result']}
    for row in owners.values():
        require(row['trigger_count']==row['customize_count']==2 and row['foreign_trigger_count']==0,'native predicted/authority first-choice count differs')
        require(row['payload_and_actor_info_match'] and row['empty_input_ignored'] and row['scan_found_target'],'native scan/input/customized event failed')
        selected='python_' if report['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_'
        require(row['metrics'][selected+'update']>=3 and row['metrics'][selected+'trigger']==3,'native input did not enter the selected interaction rules')
        require(row['metrics'][other+'update']==row['metrics'][other+'trigger']==0,'wrong native interaction profile entered')
    if report['peer']=='server':require(report['server_waited_for_client_process_exit'],'authority exited before actual owners')
    else:require(report['native_local_input_events']==3 and report['inventory_and_health_unchanged'],'native owner inputs/state differ')


def validate_directory(root):
    rows={p:json.loads((root/(p+'.json')).read_text(encoding='utf-8-sig')) for p in ('server','A','B0')}
    for row in rows.values():validate(row)
    require(len({r['run_id'] for r in rows.values()})==len({r['profile'] for r in rows.values()})==1,'mixed native interaction peers')
    for peer in ('A','B0'):
        a=rows['server']['owners'][peer];b=rows[peer]['owner_result']
        for field in ('trigger_count','customize_count','foreign_trigger_count','payload_and_actor_info_match','empty_input_ignored','scan_found_target'):require(a[field]==b[field],'authority/local prediction result differs: '+field)
    return dict(status='passed',profile=rows['server']['profile'],clients=2,native_local_prediction_and_authority_match=True,native_input_events=6)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);print(json.dumps(validate_directory(p.parse_args().directory),indent=2))
