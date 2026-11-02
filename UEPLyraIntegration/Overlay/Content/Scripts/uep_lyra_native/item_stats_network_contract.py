"""Keep the inventory lane fixed and compare native replicated stat snapshots."""
import argparse
import json
from pathlib import Path
from .inventory_network_contract import directory as inventory_directory
from .message_validation_contract import require


def validate_stats(r):
    require(r['status']=='passed' and r['error'] is None and r['previous_inventory_profile']==r['profile']=='Python','initial-stat dependency profile changed')
    require(r['stats_profile'] in ('Python','NativeFallback') and r['stats_cdo_overrides_restored'] and r['stats_class_roots_restored'],'initial-stat selector/root cleanup failed')
    require(r['native_replicated_stat_rows'],'native replicated initial-stat values missing')
    if r['peer']=='server':
        require(r['native_stat_creation_calls']==4 and r['other_stat_creation_calls']==0 and r['python_stat_application_calls']==(4 if r['stats_profile']=='Python' else 0),'native initial-stat creation route mismatch')
    else:require(all(v['python_selected']==v['native_selected']==v['python_applied']==0 for v in r['stats_policy_metrics'].values()),'owning client fabricated initialization instead of receiving replication')


def directory(path):
    inventory_directory(path);rows={p:json.loads((path/(p+'.json')).read_text(encoding='utf-8-sig')) for p in ('server','A','B0')}
    for r in rows.values():validate_stats(r)
    require(len({r['stats_profile'] for r in rows.values()})==1,'mixed initial-stat profiles')
    for peer in ('A','B0'):require(rows['server']['native_replicated_stat_rows'][peer]==rows[peer]['native_replicated_stat_rows'],'authority/client initial tag stacks differ')
    return dict(status='passed',profile=rows['server']['stats_profile'],owning_clients=2,native_initial_stat_creations=4,native_client_quickbar_cycles=12,previous_inventory_profile='Python',client_initialization_calls=0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();print(json.dumps(directory(a.directory),indent=2))
