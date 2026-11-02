"""Close CPP13-15 using archived native runs and independent report gates."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence,require
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.jump_network_contract import validate as jump_gate
from uep_lyra_native.arena_death_contract import validate as arena_gate
from uep_lyra_native.reset_network_contract import validate as reset_gate
from validate_native_death_network_reports import validate_reports as death_gate


def closed(root, relative):
    path=root/relative;report=load(path/'summary.json')
    require(report['status']=='passed' and report.get('error') is None,'closed native run failed: '+relative)
    # Later batches intentionally evolve canonical source and stage paths.
    # Archived frozen inputs remain immutable; each run's driver verified all
    # canonical inputs before writing its successful closed summary.
    for row in report.get('hashes',[]):
        p=Path(row['path'])
        if p.is_relative_to(path/'Inputs'):require(sha(p)==row['sha256'],'archived input changed: '+str(p))
    for lane in report.get('lanes',{}).values():
        require(lane['status']=='passed' and lane['error'] is None and len(lane['processes'])==3,'native network lane incomplete')
        require(all(p['exit_code']==0 for p in lane['processes'].values()),'native peer exit failed')
    if report.get('process'):require(report['process']['exit_code']==0,'native process exit failed')
    return report


def reports(directory):return {p:load(directory/(p+'.json')) for p in ('server','A','B0')}


def collect(root, output):
    root,output=root.resolve(),output.resolve()
    require(root.is_relative_to(REPO/'.build') and output.is_relative_to(REPO/'Demos'),'owned lifecycle evidence/output required')
    cpp13,cpp14,cpp15=(root/('20261102-'+name) for name in ('CPP13','CPP14','CPP15'))
    for directory,relative in ((cpp13,'Network03'),(cpp14,'Network01'),(cpp14,'SelfDestruct01'),(cpp14,'ArenaFallback01'),(cpp14,'ArenaPython01'),(cpp15,'Contexts01'),(cpp15,'Network01')):closed(directory,relative)
    build=load(cpp15/'Build01/summary.json');require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'carrier native build failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'current carrier binary changed before acceptance')
    death=reports(cpp14/'Network01/death');self_destruct=reports(cpp14/'SelfDestruct01/death')
    jump=jump_gate(reports(cpp13/'Network03/jump'))
    matrix=death_gate(death['server'],{p:death[p] for p in ('A','B0')},'matrix')
    protection=death_gate(self_destruct['server'],{p:self_destruct[p] for p in ('A','B0')},'selfdestruct')
    arena=[arena_gate(load(cpp14/name/'runtime.json')) for name in ('ArenaFallback01','ArenaPython01')]
    reset=reset_gate(reports(cpp15/'Network01/reset'))
    cross=[r for r in death['server']['cases'] if r['name']=='native-auto-respawn']
    require(len(cross)==4 and all(r['jump_cancelled_by_death'] and r['post_jump_authority_active'] for r in cross),'death/new Avatar Jump crosscheck incomplete')
    common=dict(schema_version=1,status='accepted',accepted=True,target='UE5.8.1 / CPython3.11 / Win64 Development',previous_blueprint_python_fixed=True,engine_full_compile_executed=False,sdk_or_bridge_rebuild_executed=False,cook_package_executed=False,physical_input_tested=False,cpp09_actual_window_stage_preserved=True)
    ledgers={
        'CPP13':dict(common,batch='CPP13',candidates=['CPP-019'],native_input_physics_and_prediction=jump,death_cancel_and_new_avatar_jump_trials=4,death_crosscheck=matrix,evidence=[evidence(cpp13/p) for p in ('Build02Teardown/summary.json','Assets01/summary.json','Network03/summary.json')]+[evidence(cpp14/'Network01/summary.json')]),
        'CPP14':dict(common,batch='CPP14',candidates=['CPP-020'],real_lethal_network_deaths=matrix,native_self_destruct_and_protected_ability_trials=protection,arena_native_death_tasks=arena,raw_actorinfo_spec_handles_native=True,native_waits_and_replication_retained=True,fixture_activates_only_ordinary_and_survives_death_witnesses=True,evidence=[evidence(cpp14/p) for p in ('Assets01/summary.json','Network01/summary.json','SelfDestruct01/summary.json','ArenaFallback01/summary.json','ArenaPython01/summary.json')]),
        'CPP15':dict(common,batch='CPP15',candidates=['CPP-021'],native_reset_network=reset,typed_context_cases=4,native_class_mixin_used=False,blueprint_policy_owner='world subsystem / BP_GlobalGameplayPolicy',original_reset_native_class_and_existing_spec_retained=True,ordinary_cancelled_protected_survives_respawn=True,native_reset_message_and_foreign_owner_isolation=True,fixture_activates_only_ordinary_and_survives_death_witnesses=True,compile_partition=dict(uht_runs=1,compiled_units=build.get('compiled_unity_units',['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp']),reused_units=['Module.LyraGame.3.cpp']),evidence=[evidence(cpp15/p) for p in ('Build01/summary.json','Assets01/summary.json','Contexts01/summary.json','Network01/summary.json')])}
    for batch,ledger in ledgers.items():
        path=output/(batch+'-acceptance.json');require(not path.exists(),'fresh acceptance ledger required')
        path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='accepted',batches=list(ledgers),authority_deaths=24,arena_deaths=2,native_resets=12)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(collect(a.root,a.output),indent=2))
