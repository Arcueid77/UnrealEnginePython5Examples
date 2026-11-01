"""Independent expected native slot boundaries and ordered pickup stacks."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require


def validate(r):
    require(r['status']=='passed' and r['error'] is None,'inventory runtime/finalizer failed')
    require(len(r['cases'])==14 and [c['active'] for c in r['cases']]==[-1,-1,-1,-1,-1,1,1,0,1,2,0,2,0,1],'quickbar native boundary results differ')
    require([e['count'] for e in r['pickup_entries']]==[2,1,3] and [e['definition'].split('/')[-1].split('.')[0] for e in r['pickup_entries']]==['ID_Rifle','ID_Shotgun','ID_Rifle'],'pickup native template order/count differs')
    selected='python_' if r['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_'
    require(r['quickbar_metrics'][selected+'forward']==8 and r['quickbar_metrics'][selected+'backward']==6 and r['quickbar_metrics'][selected+'free']>=14,'selected quickbar implementation bypassed')
    require(r['inventory_metrics'][selected+'grant']==2 and r['inventory_metrics'][other+'grant']==0,'selected pickup implementation or native guard differs')
    require(all(r['quickbar_metrics'][other+k]==0 for k in ('forward','backward','free')),'wrong quickbar policy executed')
    require(all(r[k] for k in ('natural_components','static_pickup_interface_entry_executed','original_inventory_restored','selectors_restored')),'native inventory/cleanup proof incomplete')
    require(not any(r[k] for k in ('native_rpc_bypassed','native_inventory_replication_replaced','existing_instance_grant_runtime_tested')),'inventory validation overclaims native TODO')


def compare(a,b):
    validate(a);validate(b)
    for key in ('cases','pickup_entries'):require(a[key]==b[key],'native/Python inventory result differs: '+key)
    return dict(status='passed',quickbar_cases=14,native_template_pickup_entries=3,existing_instance_native_unimplemented_retained=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--python',type=Path,required=True);a=p.parse_args();print(json.dumps(compare(json.loads(a.native.read_text(encoding='utf-8-sig')),json.loads(a.python.read_text(encoding='utf-8-sig'))),indent=2))
