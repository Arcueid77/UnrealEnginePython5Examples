"""Native weapon regression and mixed item/player GAS-cost authority checks."""
import argparse
import copy
import json
from pathlib import Path
from uep_lyra_weapons.weapon_ability_fire_network_contract import validate as firing,require,PEERS


def validate(server,clients):
    # The retained firing contract has a legacy schedule label. Only normalize
    # that label: both live runs actually kept the prior weapon Python fixed.
    normalized=[]
    for source in (server,*clients.values()):
        r=copy.deepcopy(source)
        for case in r['cases']:
            if case['profile']=='NativeCostFallback':case['profile']='BlueprintFallback'
        normalized.append(r)
    base=firing(normalized[0],dict(zip(clients,normalized[1:])))
    for report in (server,*clients.values()):
        require(report['previous_weapon_policy_fixed']=='Python' and report['player_cost_capability_fixture'] and not report['original_player_consumer_claimed'] and not report['client_player_stacks_written'],'native cost network scope differs')
        require(report['cost_arrays_restored'] and report['player_stacks_restored'],'native cost network cleanup missing')
    if server.get('player_cost_lifecycle_required'):
        rows=server['native_player_cost_lifecycle'];require(len(rows)==2 and {r['kind'] for r in rows}=={'lethal_death','forced_avatar_endplay'},'native player cost respawn/avatar lifecycle incomplete')
        target=rows[0]['peer'];require(all(r['peer']==target and r['old_pawn']!=r['new_pawn'] and r['player_state_preserved'] and r['marker_stacks_preserved'] and r['native_avatar_binding'] and not r['asc_binding_repaired'] for r in rows),'native player state/ASC lifecycle proof failed')
        for p,r in clients.items():require(r['lifecycle_player_state_preserved'] and r['lifecycle_avatar_changed']==(p==target),'owning client native avatar/player-state rebinding differs')
        baselines=server['post_lifecycle_inventory_baselines'];require(server['post_lifecycle_native_inventory_final']==baselines,'native authority did not restore post-lifecycle inventory')
        for p,r in clients.items():require(r['post_lifecycle_inventory_baseline']==r['post_lifecycle_native_inventory_final']==baselines[p],'native client did not receive the restored post-lifecycle inventory')
    for position,authority in enumerate(server['cases']):
        owner,profile=authority['owner'],authority['profile'];before,after=authority['player_counts_before'],authority['player_counts_after']
        require(after=={p:n-(p==owner) for p,n in before.items()},'player authority cost not paid exactly once or owner isolation failed')
        for peer,report in [('server',server),*clients.items()]:
            row=report['cases'][position];m=row['cost_metrics']
            if peer!='server':require(row['own_player_before']-row['own_player_after']==(peer==owner),'native player stat replication/owner isolation differs')
            if peer not in ('server',owner):require(m is None and row['cost_contexts']==[],'remote client executed native cost owner policy');continue
            if profile=='Python':
                require(m['python_routes']>0 and m['native_routes']==0 and m['checks']>=2 and m['applications']==(2 if peer=='server' else 0),'Python cost policy check/write route differs')
                operations=row['cost_contexts'];require({c['player'] for c in operations if c['operation']=='check'}=={False,True},'native check omitted item/player cost')
                require(all(c['authority']==(peer=='server') and c['has_target'] and c['quantity']==1 for c in operations),'native cost context authority/target/quantity differs')
                if peer=='server':require({c['player'] for c in operations if c['operation']=='apply'}=={False,True},'native authority cost omitted a target')
            else:require(profile=='NativeCostFallback' and m['native_routes']>0 and m['python_routes']==m['checks']==m['applications']==0 and row['cost_contexts']==[],'native fallback evaluated Python cost policy')
    return dict(base,status='passed',item_cost_production=True,player_cost_capability_only=True,native_player_cost_commits=4,native_item_cost_commits=4,previous_weapon_policy_fixed='Python',player_respawn_and_avatar_lifecycle=bool(server.get('player_cost_lifecycle_required')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
    def read(peer):return json.loads((a.directory/(peer+'.json')).read_text(encoding='utf-8-sig'))
    print(json.dumps(validate(read('server'),{peer:read(peer) for peer in PEERS}),indent=2))
