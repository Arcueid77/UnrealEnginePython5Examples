"""Collect closed failure recovery and bounded runtime stability evidence."""
import argparse
import ast
import json
from pathlib import Path
import runpy
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence,require
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.hardening_validation_contract import validate
from check_hardening_log import validate as log_gate
from check_hardening_stability import validate as stability_gate

def closed(path):
    report=load(path/'summary.json');require(report['status']=='passed' and report.get('error') is None,'closed hardening run failed: '+str(path))
    require(report['process']['exit_code']==0,'native hardening process did not exit cleanly')
    for row in report.get('hashes',[]):
        p=Path(row['path'])
        if p.is_relative_to(path/'Inputs'):require(sha(p)==row['sha256'],'archived hardening input changed')
    return report

def collect(root,group,output):
    root,output=root.resolve(),output.resolve()
    require(root.is_relative_to(REPO/'.build') and output.is_relative_to(REPO/'Demos') and not output.exists(),'owned closed evidence and fresh acceptance ledger required')
    common=dict(schema_version=1,status='accepted',group=group,target='UE5.8.1 / CPython3.11 / Win64 Development',cpp09_actual_desktop_input_user_deferred=True,physical_input_tested=False,new_migration_candidates_claimed=False,engine_full_compile_executed=False,cook_package_executed=False)
    if group=='H01':
        run=root/'H01-Exceptions05';closed(run);result=load(run/'runtime.json');actual=validate(result);log_gate((run/'runtime.log').read_text(encoding='utf-8-sig'),13)
        normal=root/'H01-DefaultFrontend01';closed(normal)
        from uep_lyra_native.world_validation_contract import validate as frontend_gate
        frontend=frontend_gate(load(normal/'runtime.json'))
        builds=[]
        for name,unit in (('H01-BodyBuild01',3),('H01-ResetBuild01',1)):
            x=load(root/name/'summary.json');p=load(root/name/'Plan/plan.json')
            require(x['status']=='built_requires_native_acceptance' and x['error'] is None and not x['header_generation_executed'],'body-only build/UHT reuse differs')
            require(p['compiled_unity_units']==[f'Module.LyraGame.{unit}.cpp'] and p['compiler_dependency_partition_verified'],'wrong compiler dependency partition')
            builds.append(dict(unit=unit,uht_reused=True,summary=evidence(root/name/'summary.json')))
        latest=load(root/'H01-ResetBuild01/summary.json')
        for row in latest['products']:require(sha(Path(row['path']))==row['sha256'],'current hardening binary differs')
        ledger=dict(common,actual_native_failure_recovery=actual,normal_default_frontend=frontend,compiled_body_units=builds,sdk_bridge_and_other_units_reused=True,real_equipped_item_spec_actorinfo_and_magazine_used=True,original_editor_only_fixture_factory_not_used_in_final_game_test=True,
            native_world_policy_incomplete_outputs_rejected_without_engine_ensure=True,native_reset_incomplete_plan_ends_without_resetting_or_broadcasting_pawn=True,
            reward_payload_supplied_by_fixture=True,reward_tag_snapshots_detached_before_native_map_mutation=True,
            retained_attempts=['H01-Exceptions01: incomplete policy emitted an engine ensure; the test also incorrectly called the editor-only cost factory in a game world and asserted.','H01-Exceptions02: damage and real equipped-item cost exception/recovery passed nine cases.','H01-Exceptions03/04: the reward observer exposed borrowed tag-map values invalidated by replacing their source map. Detached value snapshots restore the native observation baseline.'],
            evidence=[evidence(root/p) for p in ('H01-BodyBuild01/summary.json','H01-ResetBuild01/summary.json','H01-Exceptions05/summary.json','H01-Exceptions05/runtime.json','H01-DefaultFrontend01/summary.json')])
    else:
        require(group=='H02','supported hardening ledger group required')
        run=root/'H02-Soak20Minutes01';summary=closed(run);runtime=load(run/'runtime.json');soak=validate(runtime)
        require(soak['long_soak'] and runtime['duration_requested']>=1200,'primary twenty-minute activity required')
        log_gate((run/'runtime.log').read_text(encoding='utf-8-sig'),0);stability=stability_gate(runtime,load(run/'os-samples.json'))
        bench=root/'H02-Benchmark01';closed(bench);timing=load(bench/'runtime.json')
        contract=bench/'Inputs/Overlay/Content/Scripts/uep_lyra_native/hardening_validation_contract.py';archived=runpy.run_path(str(contract));archived['validate'](timing)
        def function(path,name):return ast.dump(next(n for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
        old=bench/'Inputs/Overlay/Content/Scripts/uep_lyra_native/hardening_activity.py';current=SCRIPTS/'uep_lyra_native/hardening_activity.py'
        require(function(old,'start_benchmark')==function(current,'start_benchmark'),'timing algorithm changed after its run')
        ledger=dict(common,actual_sustained_gameplay=soak,post_warmup_stability=stability,benchmarks=timing['benchmarks'],timing_scope=timing['timing_scope'],timing_function_unchanged=True,
            reset_body_only_change_after_benchmark_did_not_recompile_benchmark_units_2_or_3=True,rendered_frame_rate_or_universal_memory_guarantee_claimed=False,
            retained_attempts=['H02-SoakPilot01 completed two native respawns but its sample raced newly allocated query/respawn contexts. Work is now paused through two full scheduled GC passes, outside respawn setup.','H02-SoakPilot02 passed sixty seconds, two original native Reset/respawns and quiescent context bounds.'],
            evidence=[evidence(root/p) for p in ('H02-Benchmark01/summary.json','H02-Benchmark01/runtime.json','H02-SoakPilot02/summary.json','H02-Soak20Minutes01/summary.json','H02-Soak20Minutes01/runtime.json','H02-Soak20Minutes01/os-samples.json','H01-ResetBuild01/summary.json')])
    output.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='accepted',group=group,ledger=str(output))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--group',choices=('H01','H02'),required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.group,a.output)))
