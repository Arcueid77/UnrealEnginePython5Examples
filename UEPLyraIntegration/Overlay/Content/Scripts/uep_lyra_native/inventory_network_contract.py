"""Only affected inventory/RPC paths, with two actual owning clients."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require

PLAN=(('forward',0,1,False),('backward',0,2,False),('forward_wrap',2,0,False),('backward_wrap',0,2,False),('sparse_forward',1,0,True),('sparse_backward',0,1,True))


def validate(r):
    require(r['status']=='passed' and r['error'] is None,'inventory network peer failed')
    require(r['selectors_restored'] and r['original_inventory_restored'] and r['observer_closed'],'inventory network cleanup failed')
    require(not r['local_inventory_written'] and not r['native_rpc_bypassed'] and not r['gameplay_state_delivered_by_files'],'inventory network bypass')
    if r['peer']=='server':
        require(r['native_mode']=='DedicatedServer' and len(r['cases'])==12 and r['server_waited_for_client_process_exit'],'two native owners/exit barrier required')
        require(r['natural_playing_phase'] and all(r['production_inventory_classes'].values()),'native Playing/production inventory initialization missing')
        for c in r['cases']:require(c['authority']==c['client'] and c['other_owner_unchanged'],'owner RPC/replication isolation differs')
        require(all(v==1 for v in r['pickup_grant_counts'].values()),'real static pickup did not enter selected inventory profile')
    else:
        require(r['native_mode']=='Client' and len(r['cases'])==len(PLAN),'actual owning client cases missing')
        for c,(name,initial,expected,empty) in zip(r['cases'],PLAN):
            require(c['name']==name and c['model']['active']==expected and c['model']['equipment_instigator_matches'],'native equipment choice differs')
            require(c['selected_cycle_calls']==1 and c['other_cycle_calls']==0 and c['free']==(2 if empty else -1),'selected native quickbar policy bypassed')
            require(c['active_notifications']>=1 and c['replicated_stack_counts']==[1,2,1],'native OnRep/inventory fast array/subobject results missing')


def directory(path):
    rows={p:json.loads((path/(p+'.json')).read_text(encoding='utf-8-sig')) for p in ('server','A','B0')}
    for r in rows.values():validate(r)
    require(len({r['run_id'] for r in rows.values()})==len({r['profile'] for r in rows.values()})==1,'mixed inventory network pair')
    return dict(status='passed',profile=rows['server']['profile'],owning_clients=2,native_client_cycles=12,native_pickup_grants=2)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);print(json.dumps(directory(p.parse_args().directory),indent=2))
