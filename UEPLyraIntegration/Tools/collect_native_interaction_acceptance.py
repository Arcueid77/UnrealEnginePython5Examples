"""Close interaction policy, existing Explorer, and actual owner/authority evidence."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.interaction_validation_contract import require,validate
from uep_lyra_native.interaction_network_contract import validate_directory
from uep_lyra_abilities.explorer_interact_contract import validate as validate_legacy


def collect(root,runtime,legacy,network,output):
    root,output=root.resolve(),output.resolve();runtime=root/runtime;legacy=root/legacy;network=root/network
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed interaction evidence and fresh ledger required')
    build=load(root/'Build05Interface/summary.json');assets=load(root/'Assets01/summary.json');plan=load(Path(build['plan']['path']));stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'native interaction build failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'native interaction module changed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==2,'native interaction resources failed')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'interaction resource changed')
    for row in load(root/'Build05Interface/SourcePatch/summary.json')['sources']:
        require(sha(Path(row['original']))==row['original_sha256'] and sha(Path(row['path']))==row['patched_sha256'],'official/staged interaction source changed')
    for directory in (runtime,legacy,network):require(load(directory/'summary.json')['status']=='passed','interaction runtime/legacy/network lane failed')
    rules=validate(load(runtime/'runtime.json'));existing=validate_legacy(load(legacy/'runtime.json'));peers=[validate_directory(network/p) for p in ('NativeFallback','Python')]
    for directory in (runtime,legacy,network):require(sha(SCRIPTS/'uep_lyra_native/interactions.py')==sha(directory/'Inputs/Overlay/Content/Scripts/uep_lyra_native/interactions.py'),'interaction policy changed after execution')
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    result=dict(schema_version=1,status='accepted',batch='CPP08',candidates=['CPP-014'],target='UE5.8.1 / CPython3.11 / Win64 Development',policy_events=2,asset_family_count=2,
        native_python_interaction_differential=rules,existing_explorer_interact_regression=existing,actual_two_owner_prediction_authority_network=peers,
        native_interface_query_soft_class_assignment_payload_customization_actor_info_and_gas_retained=True,native_scan_grant_and_input_wait_tasks_retained=True,
        original_ga_interact_blueprint_graphs_defaults_and_inheritance_preserved=True,cpp_comparison_holds_accepted_six_blueprint_python_methods=True,
        original_blueprint_fallback_profile_retained_and_regressed=True,stage_only_native_fixture_sources_versioned=True,
        native_input_fixture_uses_lyra_virtual_spec_dispatch_once=True,physical_keyboard_acceptance=False,
        ue581_trigger_ability_uses_asc_actor_info=True,original_actor_info_argument_construction_preserved=True,effective_native_actor_info_owner_avatar='ASC owner PlayerState and avatar Pawn',
        compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'],
        reusable_native_objects=[dict(path=str(inter/('Module.LyraGame.'+str(i)+'.cpp.obj')),sha256=sha(inter/('Module.LyraGame.'+str(i)+'.cpp.obj'))) for i in (1,2,3)],
        official_reference_unchanged=True,engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,visible_rendering_acceptance=False,full_cpp_migration_acceptance=False,
        retained_attempts=['Build01','Build02','Build03Fixture','Build04Input','Runtime01','Runtime02','Runtime03','Runtime04'],
        retained_notes=['Build01 stopped before compilation because its selector placed the generated package unit in the wrong partition; actual compiler dependencies select LyraGame units 1/2 and reuse 3.',
            'Runtime01 exposed that UE5.8.1 TriggerAbilityFromGameplayEvent ignores the supplied ActorInfo argument and activates with ASC ActorInfo. The native witness now records the actual activation and payload; original argument construction remains unchanged.',
            'Runtime02 used PressInputID, whose base generic-event emission duplicates Lyra AbilitySpecInputPressed dispatch. A stage-only reflected fixture now performs the virtual native spec input dispatch once, preserving WaitInputPress replication.',
            'Runtime03 diagnostic read CurrentOptions from the readiness ability before assigning Interact. The per-case subject now starts empty.',
            'Runtime04 passed the native reference matrix and exposed unsupported InterfaceProperty reads in the Python route. The interface remains opaque in a typed native Option-to-Actor query; no SDK changes are required.'],
        evidence=[evidence(root/'Build05Interface/summary.json'),evidence(root/'Assets01/summary.json'),evidence(runtime/'summary.json'),evidence(legacy/'summary.json'),evidence(network/'summary.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='accepted',batch='CPP08',candidates=1,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--legacy',required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.runtime,a.legacy,a.network,a.output),indent=2))
