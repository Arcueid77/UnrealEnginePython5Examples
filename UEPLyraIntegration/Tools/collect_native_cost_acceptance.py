"""Close CPP11 production and CPP12 capability evidence without broad regression."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence,require
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.tag_stack_cost_contract import validate as boundaries
from uep_lyra_native.tag_stack_cost_production_contract import validate as configured
from uep_lyra_native.tag_stack_cost_network_contract import validate as network_gate


def collect(root,network,output):
    root,output=root.resolve(),output.resolve();player_root=root.parent/'20261102-CPP12';network=root/network
    require(root.is_relative_to(REPO/'.build'),'owned closed cost evidence required')
    destinations=[output/(b+'-acceptance.json') for b in ('CPP11','CPP12')]
    require(all(not p.exists() for p in destinations),'fresh cost acceptance ledgers required')
    build=load(root/'Build05Registration/summary.json');plan=load(root/'Build05Registration/Plan/plan.json');assets=load(root/'Assets01/summary.json');stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'shared native cost build failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'compiled cost module changed')
    for row in load(root/'Build05Registration/SourcePatch/summary.json')['sources']:
        require(sha(Path(row['path']))==row['patched_sha256'],'native cost source changed')
        if row['original']:require(sha(Path(row['original']))==row['original_sha256'],'official original cost source changed')
    require(plan['compiled_unity_units']==['Module.LyraGame.1.cpp'] and not plan['header_generation_executed'],'registration repair recompiled unrelated native units')
    require(load(root/'Build01/summary.json')['processes']['uht']['exit_code']==0,'initial UHT failed')
    repaired=load(root/'Build04FixtureBody/summary.json');require(all(repaired['processes']['compile-'+str(i)]['exit_code']==0 for i in (2,3)),'cost dependent units failed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==3,'complete cost declaration family required')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'cost declaration changed')
    for row in assets['retained_abilities']:require(sha(stage/row['relative'])==row['sha256'],'original ability Blueprint changed')
    lifecycle=player_root/'Lifecycle03';runs=[root/'Runtime03',player_root/'Runtime01',root/'Production01',network,root/'Diagnostics03',lifecycle]
    item=boundaries(load(runs[0]/'runtime.json'));player=boundaries(load(runs[1]/'runtime.json'));production=configured(load(runs[2]/'runtime.json'))
    peers={}
    require(load(network/'summary.json')['status']=='passed','cost network lane failed')
    for weapon in ('pistol','rifle','shotgun'):
        peers[weapon]=network_gate(load(network/weapon/'server.json'),{p:load(network/weapon/(p+'.json')) for p in ('A','B0')})
        processes=load(network/'summary.json')['weapons'][weapon]['processes'];require(set(processes)=={'server','A','B0'} and all(p['exit_code']==0 for p in processes.values()),'cost network process exit evidence failed')
    for run in runs:
        require(load(run/'summary.json')['status']=='passed','closed cost lane failed')
        current=(SCRIPTS/'uep_lyra_native/tag_stack_costs.py').read_bytes();archived=(run/'Inputs/Overlay/Content/Scripts/uep_lyra_native/tag_stack_costs.py').read_bytes()
        diagnostic_bound=b"    if len(metrics(ability)['contexts'])>128:del metrics(ability)['contexts'][:-128]\n"
        require(current==archived or current.replace(diagnostic_bound,b'')==archived,'cost policy changed beyond the bounded diagnostic history')
        for row in load(run/'summary.json')['hashes']:
            p=Path(row['path'])
            if p.is_relative_to(run/'Inputs'):require(sha(p)==row['sha256'],'archived cost runtime input changed')
    life_result=network_gate(load(lifecycle/'pistol/server.json'),{p:load(lifecycle/'pistol'/(p+'.json')) for p in ('A','B0')})
    require(life_result['player_respawn_and_avatar_lifecycle'],'player cost native respawn/avatar replacement not established')
    for row in load(lifecycle/'summary.json')['hashes']:
        p=Path(row['path'])
        if p.name=='tag_stack_costs.py':continue # Exact archived/current one-line diagnostic-only comparison above.
        require(sha(p)==row['sha256'],'frozen final network input changed')
    require(load(root/'Diagnostics03/comparison.json')['native_checks']==320,'final bounded-history native callback proof missing')
    old_stage=REPO/'.build/LyraValidation/CppGameplay/Stage/Lyra'
    require(sha(old_stage/'Binaries/Win64/UnrealEditor-LyraGame.dll')=='0C7BC68D7C8B71E9C7BEE8E0403AB3A5111A61C1C1C708A1CD773602A045E5BE','CPP09 actual-input binary changed')
    common=dict(schema_version=1,target='UE5.8.1 / CPython3.11 / Win64 Development',policy_events=3,asset_family_count=3,network_weapons=peers,previous_weapon_blueprint_policy_fixed_to_python=True,
        native_instanced_cost_subobjects_preserved=True,native_quantity_curve_level_and_truncation_preserved=True,native_additional_cost_order_fail_fast_and_hit_only_filter_preserved=True,native_authority_only_tag_stack_writes_and_replication_preserved=True,
        no_raw_actor_info_or_spec_pointer_exposed=True,no_native_replay_after_handled_python_apply=True,python_exception_injection_tested=False,
        shared_native_binary_for_both_batches=True,diagnostic_history_limit=128,final_native_diagnostic_checks=320,prior_matrices_reused_after_exact_one_line_diagnostic_history_bound=True,native_player_lifecycle=life_result,preserved_cpp09_actual_input_stage=True,official_reference_unchanged=True,sdk_or_bridge_rebuild_executed=False,engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,
        native_compile_partition=dict(initial=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp','Module.LyraGame.3.cpp'],fixture_body_repair=['Module.LyraGame.2.cpp','Module.LyraGame.3.cpp'],registration_include_repair=['Module.LyraGame.1.cpp'],uht_runs=1),
        retained_attempts=['Build01: test fixture called protected Lyra overrides; public base virtual call repaired fixture body only.','Build02/03: planner rejected mutable compiler dependency output and old UHT generated headers; guards now archive dependency inputs and retain the successful new UHT hashes.','Build04: standalone policy USTRUCT generated registration was missing; added its inline generated include in the item-cost unit, reused units 2/3 and UHT.','Runtime01: unsaved post-compilation fixture CDO cost edits were absent from new instance; test script explicitly initializes the fixture instance.','Runtime02: destroying a controller also destroys its player state; reverse actor cleanup skips already removed actors.','Diagnostics01/02: editor fixture setup could not increment player stacks outside the authority probe; bounded-history lane now checks unchanged native balances without setup mutations.','Lifecycle01/02: actual death/endplay/stack preservation and firing passed, but pre-transition or already half-magazine inventory expectations blocked cleanup; Lifecycle03 compares each native post-lifecycle baseline without applying any values from files.'],
        evidence=[evidence(root/'Build01/summary.json'),evidence(root/'Build04FixtureBody/summary.json'),evidence(root/'Build05Registration/summary.json'),evidence(root/'Assets01/summary.json')]+[evidence(run/'summary.json') for run in runs])
    results=[dict(common,status='accepted',batch='CPP11',candidates=['CPP-017'],production_replacement_accepted=True,native_cost_boundaries=item,configured_original_consumers=production,production_examples=['Pistol','Rifle','Shotgun'],retained_configuration_examples=['HealthPickup_Unused','NetShooter_PROTO'],retained_examples_natural_gameplay_acceptance=False),
        dict(common,status='capability_accepted',batch='CPP12',candidates=['CPP-018'],production_replacement_accepted=False,configured_original_consumers=0,native_cost_boundaries=player,temporary_player_cost_consumers_only=True)]
    for path,result in zip(destinations,results):path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='accepted',production=['CPP-017'],capability_only=['CPP-018'],ledgers=[str(p) for p in destinations])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.network,a.output),indent=2))
