"""Close the production bot rule batch with source-bound native evidence."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.bot_validation_contract import compare,require
from uep_lyra_native.message_network_contract import validate_directory


def collect(root,runtime,network,output):
    root,output=root.resolve(),output.resolve();runtime=root/runtime;network=root/network
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed bot evidence and fresh ledger required')
    build=load(root/'Build01/summary.json');assets=load(root/'Assets01/summary.json')
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'native bot build failed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==3,'production bot asset family failed')
    plan=load(root/'Build01/Plan/plan.json');stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    require(plan['compiled_unity_units']==['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp'],'affected bot compilation differs')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'native bot module changed')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'production bot asset changed')
    author=load(root/'Assets01/assets.json');excluded=author['retained_performance_test'];require(sha(Path(excluded['path']))==excluded['sha256'],'excluded performance test class changed')
    for row in load(root/'Build01/SourcePatch/summary.json')['sources']:
        require(sha(Path(row['original']))==row['original_sha256'],'official bot reference changed')
        require(sha(Path(row['path']))==row['patched_sha256'],'staged bot source changed')
    require(load(runtime/'summary.json')['status']==load(network/'summary.json')['status']=='passed','closed bot runtime/network failed')
    families={f:compare(load(runtime/f/'NativeFallback/runtime.json'),load(runtime/f/'Python/runtime.json')) for f in ('TDM','CP')}
    peers={p:validate_directory(network/p) for p in ('NativeFallback','Python')}
    for profile in peers:
        report=load(network/profile/'server.json');require(report.get('validate_bots') and report.get('validate_team'),'affected bot/team/network gate omitted')
    require(load(network/'NativeFallback/server.json')['result']['native_messages']==load(network/'Python/server.json')['result']['native_messages'],'affected native/Python damage/reward payload order differs')
    current=SCRIPTS/'uep_lyra_native/bot_creation.py'
    for directory in (runtime,network):require(sha(current)==sha(directory/'Inputs/Overlay/Content/Scripts/uep_lyra_native/bot_creation.py'),'production bot policy changed after native execution')
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    result=dict(schema_version=1,status='accepted',batch='CPP03',candidates=['CPP-005','CPP-006'],target='UE5.8.1 / CPython3.11 / Win64 Development',
        new_policy_events=2,existing_native_event='ServerCreateBots',native_editor_context_accessors=1,production_classes=2,asset_family_count=3,
        standalone_native_python_differentials=families,actual_dedicated_server_and_two_clients=peers,
        native_controller_spawn_initialization_and_destruction_preserved=True,native_rng_retained=True,exact_rng_sequence_claim=False,
        editor_pie_override_acceptance=False,editor_override_ported_with_native_context_reader=True,
        native_self_destruct_deaths_per_profile_and_family=9,nonempty_python_name_state_teardown_verified=True,
        performance_test_class=excluded,affected_cpp01_cpp02_damage_score_notifications_and_team_assignments_passed=True,
        compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'],
        reusable_native_objects=[dict(path=str(inter/('Module.LyraGame.'+str(i)+'.cpp.obj')),sha256=sha(inter/('Module.LyraGame.'+str(i)+'.cpp.obj'))) for i in (1,2,3)],
        official_reference_unchanged=True,engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,full_cpp_migration_acceptance=False,
        retained_attempts=['Inspect01','Runtime01'],retained_notes=['Runtime01 completed native spawn/name/removal checks but queried a destroyed component during cleanup; Runtime02 retains the Python list before native destruction.'],
        evidence=[evidence(root/'Build01/summary.json'),evidence(root/'Assets01/summary.json'),evidence(runtime/'summary.json'),evidence(network/'summary.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='accepted',batch='CPP03',candidates=2,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.runtime,a.network,a.output),indent=2))
