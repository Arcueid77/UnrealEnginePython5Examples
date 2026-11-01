"""Collect closed CPP01 evidence without broadening its platform/package claims."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[3]
SCRIPTS=REPO/'Demos/UEPLyraIntegration/Overlay/Content/Scripts'
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.message_validation_contract import compare,require
from uep_lyra_native.message_network_contract import validate_directory


def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def evidence(path):return dict(path=path.relative_to(REPO).as_posix(),sha256=sha(path))


def collect(root,network,output):
    root,output=root.resolve(),output.resolve();network=root/network
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed evidence and fresh ledger required')
    build=load(root/'Build02/summary.json');assets=load(root/'Assets03/summary.json')
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'native build failed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==7,'asset family failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'built module changed')
    stage=Path(load(root/'Build02/Plan/plan.json')['stage'])
    overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    for row in assets['assets']:
        require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'authored asset changed')
    patch=load(root/'Build02/SourcePatch/summary.json')
    for row in patch['sources']:
        require(sha(Path(row['original']))==row['original_sha256'],'official reference changed')
        require(sha(Path(row['path']))==row['patched_sha256'],'staged native source changed')
    runtime=load(root/'Runtime01/summary.json');net=load(network/'summary.json')
    require(runtime['status']==net['status']=='passed' and runtime['error'] is net['error'] is None,'closed runtime/network run failed')
    boundary=compare(load(root/'Runtime01/NativeFallback/runtime.json'),load(root/'Runtime01/Python/runtime.json'))
    actual={p:validate_directory(network/p) for p in ('NativeFallback','Python')}
    native=load(network/'NativeFallback/server.json');python=load(network/'Python/server.json')
    require(native['result']['native_messages']==python['result']['native_messages'],'native/Python actual damage/reward messages differ')
    for name in ('message_rules.py','message_processors.py'):
        current=SCRIPTS/'uep_lyra_native'/name
        for archived in (root/'Runtime01/Inputs/Overlay/Content/Scripts/uep_lyra_native'/name,network/'Inputs/Overlay/Content/Scripts/uep_lyra_native'/name):
            require(sha(current)==sha(archived),'accepted production Python code changed: '+name)
    retained=[dict(directory=name,status=load(root/name/'summary.json')['status'],error=load(root/name/'summary.json').get('error'))
              for name in ('Build01','Assets01','Assets02','Network01','Network02')]
    result=dict(schema_version=1,status='accepted',batch='CPP01',candidates=['CPP-001','CPP-002','CPP-003'],
        target='UE5.8.1 / CPython3.11 / Win64 Development',
        production_event_entrypoints=4,persistent_processor_classes=3,asset_family_count=7,
        native_message_differential=boundary,actual_damage_network=actual,
        native_python_actual_payload_order_equal=True,native_processors_server_only=True,
        native_damage_specs_per_profile=6,native_eliminations_per_profile=5,
        authority_and_two_client_score_delta=python['result']['stat_delta'],
        native_listener_teardown_verified=True,official_reference_unchanged=True,
        engine_full_compile_executed=False,cook_package_executed=False,visible_render_acceptance=False,
        full_cpp_migration_acceptance=False,new_platform_acceptance=False,
        retained_attempts=retained,network_restart_note='Network02 was stopped during unrelated graphical shader compilation; Network03 uses actual non-rendering clients.',
        evidence=[evidence(root/'Build02/summary.json'),evidence(root/'Assets03/summary.json'),
                  evidence(root/'Runtime01/summary.json'),evidence(root/'Runtime01/comparison.json'),evidence(network/'summary.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='accepted',batch='CPP01',candidates=3,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(collect(a.root,a.network,a.output),indent=2))
