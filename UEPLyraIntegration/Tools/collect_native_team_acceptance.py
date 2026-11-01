"""Close CPP02 only after both retained team configurations and real peers pass."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.team_validation_contract import compare,require
from uep_lyra_native.message_network_contract import validate_directory


def collect(root,runtime,four_runtime,network,output):
    root,output=root.resolve(),output.resolve();runtime=root/runtime;four_runtime=root/four_runtime;network=root/network
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed team evidence and fresh ledger required')
    build=load(root/'Build03/summary.json');assets=load(root/'Assets04/summary.json')
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'native team build failed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==3,'team asset family failed')
    plan=load(root/'Build03/Plan/plan.json');stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    require(plan['compiled_unity_units']==['Module.LyraGame.1.cpp','Module.LyraGame.3.cpp'] and plan['reused_unity_units']==['Module.LyraGame.2.cpp'],'affected native compilation partition differs')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'built native team module changed')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'accepted team asset changed')
    for row in load(root/'Build03/SourcePatch/summary.json')['sources']:
        require(sha(Path(row['original']))==row['original_sha256'],'official team reference changed')
        require(sha(Path(row['path']))==row['patched_sha256'],'staged team source changed')
    two_summary=load(runtime/'summary.json')
    require(all(two_summary['processes']['Two-'+p]['exit_code']==0 for p in ('NativeFallback','Python')),'closed two-team process subset failed')
    require(load(runtime/'Two/comparison.json')['status']=='passed','two-team subset comparison failed')
    require(load(four_runtime/'summary.json')['status']==load(network/'summary.json')['status']=='passed','closed four-team runtime/network failed')
    family_roots={'Two':runtime,'Four':four_runtime}
    families={family:compare(load(directory/family/'NativeFallback/runtime.json'),load(directory/family/'Python/runtime.json')) for family,directory in family_roots.items()}
    peers={profile:validate_directory(network/profile) for profile in ('NativeFallback','Python')}
    native=load(network/'NativeFallback/server.json');python=load(network/'Python/server.json')
    require(native.get('validate_team') and python.get('validate_team'),'actual peer run omitted team policy gate')
    require(native['result']['native_messages']==python['result']['native_messages'],'affected CPP01 native damage/reward messages differ')
    current=SCRIPTS/'uep_lyra_native/team_creation.py'
    for directory in (runtime,four_runtime,network):require(sha(current)==sha(directory/'Inputs/Overlay/Content/Scripts/uep_lyra_native/team_creation.py'),'production team policy changed after native execution')
    result=dict(schema_version=1,status='accepted',batch='CPP02',candidates=['CPP-004'],target='UE5.8.1 / CPython3.11 / Win64 Development',
        native_policy_events=2,native_setter_adapters=1,persistent_configuration_classes=2,asset_family_count=3,
        native_team_creation_and_callbacks_preserved=True,native_setter_notifications_preserved=True,
        standalone_native_python_differentials=families,actual_dedicated_server_and_two_clients=peers,
        natural_eleven_player_assignments_balanced=True,affected_cpp01_damage_score_and_notifications_passed=True,
        compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'],
        reusable_native_objects=[dict(path=str(stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame/Module.LyraGame.3.cpp.obj'),sha256=sha(stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame/Module.LyraGame.3.cpp.obj'))],
        native_team_metrics={p:load(network/p/'server.json')['natural_team_metrics'] for p in peers},
        official_reference_unchanged=True,engine_full_compile_executed=False,cook_package_executed=False,
        full_cpp_migration_acceptance=False,new_platform_acceptance=False,
        reused_two_team_subset=True,retained_attempts=['Build01','Build02','Assets01','Assets02','Assets03','Runtime01','Runtime02','Runtime03/Four','Runtime04'],
        retained_notes=['Build01 compiled the affected units; Build02 fixed only the reused object link path.',
            'Runtime01 identified the non-reflected setter; Build03 added one thin native setter adapter.',
            'Runtime02 seeded invalid zero-based fixture IDs; native reference assertion retained; Runtime03 reads original IDs.',
            'Runtime03 Two passed both profiles and is reused; only Four was restarted.',
            'Runtime04 local split-screen players produced a native SlateUser ensure under NullRHI; Runtime05 uses three temporary native PlayerState actors with explicit fixture scope.'],
        evidence=[evidence(root/'Build03/summary.json'),evidence(root/'Assets04/summary.json'),evidence(runtime/'Two/comparison.json'),evidence(four_runtime/'summary.json'),evidence(network/'summary.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='accepted',batch='CPP02',candidates=1,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--four-runtime',required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(collect(a.root,a.runtime,a.four_runtime,a.network,a.output),indent=2))
