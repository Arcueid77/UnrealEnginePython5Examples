"""Original movement/task gates, holding prior BP policy fixed for native rules."""
import argparse
import copy
import json
from pathlib import Path
from uep_lyra_abilities.jump_contract import validate as movement,require,PLAN


def client(report):
    r=copy.deepcopy(report)
    for case in r['cases']:
        for key in ('blueprint','python'):
            side=case[key]
            if side['profile_after']=='NativeLifecycleFallback':side['profile_after']='BlueprintFallback'
    result=movement(r);require(report['previous_blueprint_policy_fixed']=='Python' and len(report['admission_boundaries'])==6,'native Jump admission/prior policy coverage incomplete')
    for row in report['admission_boundaries']:require(row['result']==(row['case']=='valid'),'native Jump null/valid actor info gate differs')
    for case in report['cases']:
        for key in ('blueprint','python'):
            m=case[key]['native_lifecycle_counts'];require(m['jump_start']==int(key=='python'),'native Jump start policy dispatch differs')
            require(m['jump_native']>0 if key=='blueprint' else m['jump_python']>0,'native Jump selector bypassed')
    return dict(result,cpp_native_jump_rules=True,previous_blueprint_policy_fixed='Python')


def validate(reports):
    s=reports['server'];require(s['status']=='passed' and s['error'] is None and s['server_waited_for_client_process_exit'] and len(s['cases'])==28,'native Jump authority barrier/matrix failed')
    require(s['previous_blueprint_policy_fixed']=='Python' and len(set(s['player_ids'].values()))==2,'native Jump prior policy/owners differ')
    for peer in ('A','B0'):client(reports[peer]);require(reports[peer]['player_id']==s['player_ids'][peer],'native Jump owner differs')
    for row in s['cases']:
        expected=('NativeLifecycleFallback','Python')[row['index']%2];require(row['profile']==expected and row['native_active_observed'] and row['max_authority_rise']>20 and row['authority_final_inactive'] and row['authority_final_grounded'] and row['other_owner_stayed_idle'],'native authority Jump/ownership/physics differs')
        require(row['client']['row']==reports[row['target']]['cases'][row['index']//2]['blueprint' if row['index']%2==0 else 'python'],'native Jump client/authority acknowledgment differs')
        counts=row['authority_counters'];require(all(counts[k]==1 for k in ('activations','states_created','releases_created','scopes_created','scopes_closed')),'previous authority Jump Python policy did not remain fixed')
    m=s['policy_shutdown'];require(m['activations']==m['scopes_created']==m['scopes_closed']==28 and m['active_count']==0 and m['errors']==[],'native Jump authority task cleanup differs')
    return dict(status='passed',owners=2,native_jump_trials=28,admission_boundary_calls=12,physical_input_tested=False,previous_blueprint_policy_fixed='Python',death_respawn_crosscheck_pending=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();print(json.dumps(validate({peer:json.loads((a.directory/(peer+'.json')).read_text(encoding='utf-8-sig')) for peer in ('server','A','B0')}),indent=2))
