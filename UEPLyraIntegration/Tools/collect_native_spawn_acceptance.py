"""Close native spawning rules only with real geometry, restart and peer evidence."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.spawn_validation_contract import compare,require
from uep_lyra_native.message_network_contract import validate_directory


def collect(root,runtime,network,output):
    root,output=root.resolve(),output.resolve();runtime=root/runtime;network=root/network
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed spawning evidence and fresh ledger required')
    build=load(root/'Build02/summary.json');assets=load(root/'Assets01/summary.json')
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None and len(build['products'])==2,'native spawning module pair failed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==2,'native spawning asset family failed')
    plan=load(root/'Build02/Plan/plan.json');stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'spawning native module changed')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'spawning asset changed')
    for row in load(root/'Build02/SourcePatch/summary.json')['sources']:
        require(sha(Path(row['original']))==row['original_sha256'],'official spawning reference changed')
        require(sha(Path(row['path']))==row['patched_sha256'],'staged spawning source changed')
    require(load(runtime/'summary.json')['status']==load(network/'summary.json')['status']=='passed','closed spawning runtime/network failed')
    rules=compare(load(runtime/'NativeFallback/runtime.json'),load(runtime/'Python/runtime.json'))
    peers={p:validate_directory(network/p) for p in ('NativeFallback','Python')}
    for p in peers:require(load(network/p/'server.json').get('validate_spawning'),'actual network spawning gate omitted')
    require(load(network/'NativeFallback/server.json')['result']['native_messages']==load(network/'Python/server.json')['result']['native_messages'],'affected damage/reward payload order differs')
    current=SCRIPTS/'uep_lyra_native/spawning.py'
    for directory in (runtime,network):require(sha(current)==sha(directory/'Inputs/Overlay/Content/Scripts/uep_lyra_native/spawning.py'),'production spawning policy changed after native execution')
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    result=dict(schema_version=1,status='accepted',batch='CPP04',candidates=['CPP-007','CPP-008'],target='UE5.8.1 / CPython3.11 / Win64 Development',
        policy_events=2,native_specific_query_occupancy_and_claim_helpers=4,asset_family_count=2,
        native_python_geometry_claim_and_restart_differential=rules,actual_dedicated_server_and_two_clients=peers,
        native_cached_starts_and_pie_preference_preserved=True,private_cache_not_written=True,
        actual_native_occupancy_states=dict(empty=0,partial=1,full=2),actual_native_restart_entered_python=True,
        native_claim_and_expiration_timer_preserved=True,native_rng_retained=True,exact_rng_sequence_claim=False,
        affected_cpp01_cpp02_cpp03_damage_notifications_team_and_bot_gates_passed=True,
        compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'],
        reusable_native_objects=[dict(path=str(inter/('Module.LyraGame.'+str(i)+'.cpp.obj')),sha256=sha(inter/('Module.LyraGame.'+str(i)+'.cpp.obj'))) for i in (1,2,3)],
        official_reference_unchanged=True,engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,full_cpp_migration_acceptance=False,
        retained_attempts=['Build01','Runtime01'],retained_notes=['Build01 lacked the MinimalAPI base event export; Build02 exports the implementation for the derived module.',
            'Runtime01 returned the native const-array output tuple as an actor; Runtime02 explicitly extracts ReturnValue using the existing output ABI helper.'],
        evidence=[evidence(root/'Build02/summary.json'),evidence(root/'Assets01/summary.json'),evidence(runtime/'summary.json'),evidence(network/'summary.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='accepted',batch='CPP04',candidates=2,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.runtime,a.network,a.output),indent=2))
