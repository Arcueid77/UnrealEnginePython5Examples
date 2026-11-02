"""Collect closed frontend, replicated cosmetics and native camera lifecycles."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence,require
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.world_validation_contract import validate as runtime_gate
from uep_lyra_native.parts_network_contract import validate as network_gate


def closed(path):
    summary=load(path/'summary.json');require(summary['status']=='passed' and summary.get('error') is None,'closed world run failed: '+str(path))
    for row in summary.get('hashes',[]):
        p=Path(row['path'])
        if p.is_relative_to(path/'Inputs'):require(sha(p)==row['sha256'],'archived world input changed')
    archived=path/'Inputs/Overlay/Content/Scripts/uep_lyra_native/world_policies.py'
    require(sha(archived)==sha(SCRIPTS/'uep_lyra_native/world_policies.py'),'accepted world policy changed')
    return summary


def collect(root,output):
    root,output=root.resolve(),output.resolve();require(root.is_relative_to(REPO/'.build') and output.is_relative_to(REPO/'Demos'),'owned world evidence and output required')
    world=root/'20261102-CPP16';network=root/'20261102-CPP17/Network04'
    build=load(world/'Build01/summary.json');require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'world-policy native build failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'current world-policy binary changed')
    boundary=closed(world/'Boundaries01');b=load(world/'Boundaries01/runtime.json')
    require(b['status']=='passed' and b['frontend_cases']==70 and b['part_cases']==28 and b['camera_cases']==8,'world boundary matrix incomplete')
    runs={}
    for name in ('FrontendNative01','FrontendPython01','PartsNative03','PartsPython01','CameraNative02','CameraPython01','Defaultfrontend01','Defaultcamera01'):
        closed(world/name);runs[name]=runtime_gate(load(world/name/'runtime.json'))
    closed(network);reports={p:load(network/'parts'/(p+'.json')) for p in ('server','A','B0')};actual=network_gate(reports)
    for peer in ('server','A','B0'):require(load(network/'summary.json')['lanes']['parts']['processes'][peer]['exit_code']==0,'parts peer did not exit cleanly')
    promotion=load(world/'Assets03Promote/assets.json');require(promotion['status']=='passed' and promotion['new_defaults_enabled'],'accepted world policies not promoted to default')
    common=dict(schema_version=1,status='accepted',accepted=True,target='UE5.8.1 / CPython3.11 / Win64 Development',previous_reset_python_fixed=True,engine_full_compile_executed=False,sdk_or_bridge_rebuild_executed=False,cook_package_executed=False,physical_input_tested=False,default_profile_promoted=True,cpp09_actual_window_stage_preserved=True,compile_partition=dict(uht_modules=['LyraGame'],compiled_units=[1,3],reused_units=[2]),shared_adapter_candidates=['CPP-022','CPP-023','CPP-024'])
    ledgers={
        'CPP16':dict(common,batch='CPP16',candidates=['CPP-022'],typed_boundary_cases=70,actual_offline_frontend=[runs[n] for n in ('FrontendNative01','FrontendPython01','Defaultfrontend01')],native_user_initialization_success_failure_callbacks_supplied_by_fixture=True,join_success_failure_and_widget_cancel_policy_checked_by_typed_context=True,actual_online_service_results_tested=False,native_flow_handles_weak_widget_callbacks_and_delegate_removal_retained=True,evidence=[evidence(world/p) for p in ('Build01/summary.json','Boundaries01/summary.json','FrontendNative01/summary.json','FrontendPython01/summary.json','Defaultfrontend01/summary.json','Assets03Promote/summary.json')]),
        'CPP17':dict(common,batch='CPP17',candidates=['CPP-023'],typed_boundary_cases=28,native_and_python_possession=[runs[n] for n in ('PartsNative03','PartsPython01')],actual_network_actor_mesh_and_reset=actual,natural_suppression_developer_and_cheat_sources_distinguished=True,original_part_templates_restored_before_client_release=True,native_actor_creation_fast_array_replication_and_handles_retained=True,retained_failed_fixture_attempts=['Owned temporary PlayerState was destroyed while a spawn-effect spec remained active. The test now uses the original native Reset/respawn route and restores original parts.','Network01 used a non-reflected component query; corrected to native LyraSystemStatics.FindComponentsByClass.','Network02/03 exposed observer/restoration scheduling races. Hooks now run inside the existing owner/foreign acknowledgement barriers.'],evidence=[evidence(world/p) for p in ('Build01/summary.json','Boundaries01/summary.json','PartsNative03/summary.json','PartsPython01/summary.json')]+[evidence(network/'summary.json')]),
        'CPP18':dict(common,batch='CPP18',candidates=['CPP-024'],typed_boundary_cases=8,actual_native_ability_camera_lifecycle=[runs[n] for n in ('CameraNative02','CameraPython01','Defaultcamera01')],default_pawndata_camera_and_actual_ability_end_restore=True,wrong_owner_handle_preserves_override=True,missing_pawn_and_data_return_null=True,native_camera_blending_collision_and_owning_spec_handles_retained=True,pixels_tested=False,evidence=[evidence(world/p) for p in ('Build01/summary.json','Boundaries01/summary.json','CameraNative02/summary.json','CameraPython01/summary.json','Defaultcamera01/summary.json','Assets03Promote/summary.json')])}
    for batch,ledger in ledgers.items():
        path=output/(batch+'-acceptance.json');require(not path.exists(),'fresh world acceptance ledger required')
        path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='accepted',batches=list(ledgers),boundary_cases=106,replicated_part_trials=4,client_views=8)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.output),indent=2))
