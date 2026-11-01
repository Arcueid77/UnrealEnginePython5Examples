"""Close native accolade policy, lifetime, and real-owner network evidence."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.accolade_validation_contract import require,validate
from uep_lyra_native.message_network_contract import validate_directory


def collect(root,runtime,network,output):
    root,output=root.resolve(),output.resolve();runtime=root/runtime;network=root/network
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed accolade evidence and fresh ledger required')
    build=load(root/'Build01/summary.json');assets=load(root/'Assets03/summary.json');plan=load(root/'Build01/Plan/plan.json');stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'native accolade build failed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==2,'native accolade resources failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'native accolade module changed')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'native accolade asset changed')
    for row in load(root/'Build01/SourcePatch/summary.json')['sources']:
        require(sha(Path(row['original']))==row['original_sha256'],'official accolade reference changed')
        require(sha(Path(row['path']))==row['patched_sha256'],'staged accolade source changed')
    require(load(runtime/'summary.json')['status']==load(network/'summary.json')['status']=='passed','closed accolade runtime/network failed')
    report=load(runtime/'runtime.json');rules=validate(report);peers=[]
    for profile in ('NativeFallback','Python'):
        peers.append(validate_directory(network/profile))
        for peer in ('server','A','B0'):require(load(network/profile/(peer+'.json'))['validate_accolades'],'ordinary owner accolade queue gate was disabled')
    for peer in ('A','B0'):
        pair=[]
        for profile,prefix in (('NativeFallback','native_'),('Python','python_')):
            value=load(network/profile/(peer+'.json'))['accolade_result']
            pair.append(dict(metrics={k:value['metrics'][prefix+k] for k in ('notify','row','consider','process','display','pop','clear')},creates=value['presentation_creates'],destroys=value['presentation_destroys']))
        require(pair[0]==pair[1],'real-owner native/Python queue or presentation counts differ')
    for path in (runtime,network):require(sha(SCRIPTS/'uep_lyra_native/accolades.py')==sha(path/'Inputs/Overlay/Content/Scripts/uep_lyra_native/accolades.py'),'accolade policy changed after execution')
    result=dict(schema_version=1,status='accepted',batch='CPP07',candidates=['CPP-012','CPP-013'],target='UE5.8.1 / CPython3.11 / Win64 Development',
        policy_events=7,asset_family_count=2,native_python_registry_async_timer_lifetime_differential=rules,actual_native_damage_two_owner_network=peers,
        cpp_reference_keeps_accepted_three_blueprint_presentation_methods=True,native_ftext_and_icon_payloads_preserved=True,network_host_fixture_per_real_owner=True,natural_hud_creation_or_rendering_acceptance=False,
        cold_native_asset=report['cold_native_asset'],actual_pending_asset_and_registry_callbacks_cancelled=True,
        native_lifetime_fix=['cancel reconsideration timer and clear queues on destruct','reject callbacks from a previous widget construction generation'],
        compiled_unity_units=plan['compiled_unity_units'],reused_lyra_game_units=plan['reused_lyra_game_units'],
        native_registry_asset_streaming_timer_and_listener_ownership_preserved=True,official_reference_unchanged=True,
        engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,visible_rendering_acceptance=False,full_cpp_migration_acceptance=False,
        retained_attempts=['Assets01','Assets02','Runtime01','Runtime02','Runtime03','Runtime04','Runtime05','Runtime06','Network01','Network02','Network03'],
        retained_notes=['Runtime01 showed SetOwningPlayer(None) does not create an ownerless widget; the fixture now constructs a new widget without a player context.',
            'Runtime02 exposed use of the tag asset interface query instead of the tag container query; HasAnyTags with hierarchical matching preserves the native HasAny rule.',
            'Runtime03 passed all eleven behavior cases but correctly rejected a teardown fixture whose assets were already cached and completed inline.',
            'Runtime04-05 found the first chosen texture already resident. Runtime06 attempted the editor table import from game mode and hit a null editor subsystem in CSVImportFactory. Assets02 exposed missing RowStruct initialization before import. Assets03 prepares the stage-only table in the editor; the game selects an existing unloaded texture without loading it and requires both asset and registry requests pending before teardown.',
            'Network01 encountered widget default objects without a UWorld. Network02 found no natural HUD hosts in the NullRHI clients and could not pass its host gate; a client later exited through an engine error handler. Network03 was stopped before fixture setup to correct an undefined constructor helper and root the fixture class through the startup GC. The accepted network harness creates one original host widget per actual client owner, retains production native message/registry/timer paths, and claims no natural HUD or rendering acceptance.'],
        evidence=[evidence(root/'Build01/summary.json'),evidence(root/'Assets03/summary.json'),evidence(runtime/'summary.json'),evidence(network/'summary.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='accepted',batch='CPP07',candidates=2,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.runtime,a.network,a.output),indent=2))
