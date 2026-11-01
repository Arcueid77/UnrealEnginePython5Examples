"""Close the affected native inventory/pickup/RPC checks with explicit TODO."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.inventory_validation_contract import compare,require
from uep_lyra_native.inventory_network_contract import directory


def collect(root,runtime,network,output):
    root,output=root.resolve(),output.resolve();runtime=root/runtime;network=root/network
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed inventory evidence and fresh ledger required')
    build=load(root/'Build01/summary.json');assets=load(root/'Assets01/summary.json');plan=load(root/'Build01/Plan/plan.json');stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None and len(build['products'])==1,'native inventory build failed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==5,'inventory resource family failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'native inventory module changed')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'inventory asset changed')
    for row in load(root/'Build01/SourcePatch/summary.json')['sources']:
        require(sha(Path(row['original']))==row['original_sha256'],'official inventory reference changed')
        require(sha(Path(row['path']))==row['patched_sha256'],'staged inventory source changed')
    require(load(runtime/'summary.json')['status']==load(network/'summary.json')['status']=='passed','closed inventory runtime/network failed')
    rules=compare(load(runtime/'NativeFallback/runtime.json'),load(runtime/'Python/runtime.json'));peers={p:directory(network/p) for p in ('NativeFallback','Python')}
    for relative in ('inventory.py','inventory_validation_helpers.py'):
        for path in (runtime,network):require(sha(SCRIPTS/'uep_lyra_native'/relative)==sha(path/'Inputs/Overlay/Content/Scripts/uep_lyra_native'/relative),'inventory implementation changed after execution')
    baseline=Path('F:/LyraStarterGame/Source/LyraGame/Inventory/LyraInventoryManagerComponent.cpp')
    require('void FLyraInventoryList::AddEntry(ULyraInventoryItemInstance* Instance)\n{\n\tunimplemented();\n}' in baseline.read_text(),'native existing-instance limitation changed')
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    result=dict(schema_version=1,status='accepted',batch='CPP05',candidates=['CPP-009','CPP-010'],target='UE5.8.1 / CPython3.11 / Win64 Development',
        policy_events=4,asset_family_count=5,native_python_inventory_differential=rules,actual_dedicated_server_and_two_clients=peers,
        native_server_slot_rpc_equipment_onrep_fast_array_and_subobjects_preserved=True,retained_quickbar_graphs_defaults_and_game_feature_role_flags=True,
        native_instance_addentry_unimplemented_retained=True,existing_instance_forwarding_host_test_only=True,existing_instance_runtime_acceptance=False,
        interface_null_pickup_guard_unchanged_source_audited=True,interface_null_inventory_guard_runtime_tested=True,
        compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'],
        reusable_native_objects=[dict(path=str(inter/('Module.LyraGame.'+str(i)+'.cpp.obj')),sha256=sha(inter/('Module.LyraGame.'+str(i)+'.cpp.obj'))) for i in (1,2,3)],
        official_reference_unchanged=True,engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,full_cpp_migration_acceptance=False,
        evidence=[evidence(root/'Build01/summary.json'),evidence(root/'Assets01/summary.json'),evidence(runtime/'summary.json'),evidence(network/'summary.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='accepted',batch='CPP05',candidates=2,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.runtime,a.network,a.output),indent=2))
