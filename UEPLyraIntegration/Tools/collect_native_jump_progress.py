"""Record verified CPP13 input/physics without claiming the pending death crosscheck."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence,require
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.jump_network_contract import validate


def collect(root,output):
    root,output=root.resolve(),output.resolve();require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed jump evidence and fresh progress required')
    build=load(root/'Build02Teardown/summary.json');assets=load(root/'Assets01/summary.json');network=root/'Network03';summary=load(network/'summary.json');stage=Path(load(root/'Build02Teardown/Plan/plan.json')['stage'])
    require(build['status']=='built_requires_native_acceptance' and summary['status']=='passed' and assets['status']=='passed','native Jump build/assets/network failed')
    for r in build['products']:require(sha(Path(r['path']))==r['sha256'],'native Jump binary changed')
    for r in load(root/'Build02Teardown/SourcePatch/summary.json')['sources']:require(sha(Path(r['path']))==r['patched_sha256'] and sha(Path(r['original']))==r['original_sha256'],'native Jump original/patch changed')
    for r in assets['assets']:require(sha(stage/r['relative'])==sha(REPO/'Demos/UEPLyraIntegration/Overlay'/r['relative'])==r['sha256'],'native Jump declaration changed')
    for r in assets['retained_abilities']:require(sha(stage/r['relative'])==r['sha256'],'original Jump Blueprint changed')
    result=validate({peer:load(network/'jump'/(peer+'.json')) for peer in ('server','A','B0')})
    for r in summary['hashes']:require(sha(Path(r['path']))==r['sha256'],'final Jump frozen input changed')
    ledger=dict(schema_version=1,status='implemented_pending_death_lifecycle_crosscheck',accepted=False,batch='CPP13',candidates=['CPP-019'],target='UE5.8.1 / CPython3.11 / Win64 Development',native_input_physics_and_prediction=result,
        shared_native_adapter_candidates=['CPP-019','CPP-020','CPP-021'],death_and_reset_bindings_enabled=False,cpp14_death_respawn_crosscheck_pending=True,previous_jump_blueprint_python_fixed=True,original_jump_blueprint_bytes_preserved=True,explicit_teardown_guard_uses_original_native_stop=True,
        compile_partition=dict(initial_units=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp'],reused=['Module.LyraGame.3.cpp'],private_body_repair=['Module.LyraGame.1.cpp'],uht_runs=1),engine_full_compile_executed=False,sdk_or_bridge_rebuild_executed=False,cook_package_executed=False,physical_input_tested=False,
        retained_attempts=['Network01: old observer assumed the Character had no registered production mixins; observer now wraps and restores those profiles.','Network02: all 28 movement trials completed, but profile teardown reentered a stopped native policy router; explicit native teardown guards repaired Jump and Death bodies without rerunning UHT.'],
        evidence=[evidence(root/p) for p in ('Build01/summary.json','Build02Teardown/summary.json','Assets01/summary.json','Network03/summary.json','Network03/jump/independent-gate-stdout.log')])
    output.write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status=ledger['status'],accepted=False,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.output),indent=2))
