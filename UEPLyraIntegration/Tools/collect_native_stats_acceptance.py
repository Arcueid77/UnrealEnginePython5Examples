"""Accept CPP10 from native creation, typed-map boundaries and real replication."""
import argparse
import json
from pathlib import Path
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence,require
import sys
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.item_stats_contract import validate
from uep_lyra_native.item_stats_network_contract import directory


def collect(root,runtime,network,output):
    root,output=root.resolve(),output.resolve();runtime=root/runtime;network=root/network
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed initial-stat evidence and fresh ledger required')
    build=load(root/'Build03FixtureBody/summary.json');plan=load(root/'Build03FixtureBody/Plan/plan.json');assets=load(root/'Assets01/summary.json');stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'initial-stat fixture build failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'compiled initial-stat module changed')
    for row in load(root/'Build01/SourcePatch/summary.json')['sources']:require(sha(Path(row['original']))==row['original_sha256'] and sha(Path(row['path']))==row['patched_sha256'],'initial-stat original/staged source changed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==6,'complete constant-profile definition family required')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'initial-stat declaration changed')
    require(load(runtime/'summary.json')['status']=='passed','native initial-stat matrix failed');rules=validate(load(runtime/'runtime.json'))
    require(load(network/'summary.json')['status']=='passed','initial-stat replicated-owner matrix failed');peers={p:directory(network/p) for p in ('NativeFallback','Python')}
    for run in (runtime,network):
        require(sha(SCRIPTS/'uep_lyra_native/item_stats.py')==sha(run/'Inputs/Overlay/Content/Scripts/uep_lyra_native/item_stats.py'),'initial-stat policy changed after execution')
        for row in load(run/'summary.json')['hashes']:
            p=Path(row['path'])
            if p.is_relative_to(run/'Inputs'):require(sha(p)==row['sha256'],'archived runtime input changed')
    for row in load(network/'summary.json')['hashes']:require(sha(Path(row['path']))==row['sha256'],'frozen network input changed')
    stage_copy=load(root/'stage-copy.json');require(stage_copy['status']=='passed' and not stage_copy['hardlinks_used'] and not stage_copy['junctions_used'],'independent initial-stat stage not established')
    result=dict(schema_version=1,status='accepted',batch='CPP10',candidates=['CPP-016'],target='UE5.8.1 / CPython3.11 / Win64 Development',policy_events=2,asset_family_count=6,
        native_python_initial_stat_matrix=rules,native_replicated_owners=peers,previous_inventory_and_quickbar_policies_fixed_to_python=True,
        constant_item_definition_profile_selector_verified=True,native_instanced_fragments_order_defaults_graphs_and_inheritance_preserved=True,typed_snapshot_replaces_unhashable_map_key_reads=True,native_map_iteration_order_preserved=True,
        production_examples=['Pistol','Rifle','Shotgun'],retained_configuration_examples=['HealthPickup_Unused','NetShooter_PROTO'],retained_examples_natural_gameplay_acceptance=False,
        native_inventory_creation_and_tag_stack_replication_preserved=True,no_native_replay_after_handled_python_callback=True,python_exception_injection_tested=False,
        independent_stage=True,preserved_cpp09_actual_input_stage=True,official_reference_unchanged=True,sdk_or_bridge_rebuild_executed=False,engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,
        initial_build_compiled_units=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp','Module.LyraGame.3.cpp'],fixture_build_compiled_units=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp'],fixture_body_repair_compiled_units=['Module.LyraGame.2.cpp'],fixture_body_repair_reused_units=['Module.LyraGame.1.cpp','Module.LyraGame.3.cpp'],
        retained_attempts=['Build02Fixtures: fixture-only FindFPropertyChecked spelling failed; repaired its body using FindFProperty plus check, retaining UHT and units 1/3.','Runtime01: creation matrix passed, editor-world K2_DestroyActor did not remove the fixture; Runtime02 uses the actual EditorActorSubsystem destroy and verifies removal.','Network01: definition getter was an inline native function; Network02 reads the reflected ItemDef property.'],
        evidence=[evidence(root/'stage-copy.json'),evidence(root/'Build01/summary.json'),evidence(root/'Build03FixtureBody/summary.json'),evidence(root/'Assets01/summary.json'),evidence(runtime/'summary.json'),evidence(runtime/'comparison.json'),evidence(network/'summary.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='accepted',batch='CPP10',ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.runtime,a.network,a.output),indent=2))
