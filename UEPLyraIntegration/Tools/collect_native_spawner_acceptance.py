"""Close native spawner orchestration and its existing two-owner regression."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.spawner_validation_contract import compare,require


def collect(root,runtime,network,output):
    root,output=root.resolve(),output.resolve();runtime=root/runtime;network=root/network
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned closed spawner evidence and fresh ledger required')
    build=load(root/'Build02/summary.json');assets=load(root/'Assets06/summary.json');plan=load(root/'Build02/Plan/plan.json');stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'spawner native build failed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==3,'spawner resource family failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'native spawner module changed')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'spawner asset changed')
    for row in load(root/'Build02/SourcePatch/summary.json')['sources']:
        require(sha(Path(row['original']))==row['original_sha256'],'official spawner reference changed')
        require(sha(Path(row['path']))==row['patched_sha256'],'staged spawner source changed')
    require(load(runtime/'summary.json')['status']==load(network/'summary.json')['status']=='passed','closed spawner runtime/network failed')
    rules=compare(load(runtime/'NativeFallback/runtime.json'),load(runtime/'Python/runtime.json'))
    validation=subprocess.run([sys.executable,'-B','-X','utf8',str(REPO/'Demos/UEPLyraIntegration/Tools/validate_native_spawner_network_reports.py'),str(network)],check=True,capture_output=True,text=True,encoding='utf-8')
    peers=json.loads(validation.stdout)
    require(peers['status']=='passed' and peers['cases']==36 and peers['clients']==2,'existing two-owner spawner regression incomplete')
    for path in (runtime,network):require(sha(SCRIPTS/'uep_lyra_native/spawner.py')==sha(path/'Inputs/Overlay/Content/Scripts/uep_lyra_native/spawner.py'),'spawner policy changed after execution')
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    result=dict(schema_version=1,status='accepted',batch='CPP06',candidates=['CPP-011'],target='UE5.8.1 / CPython3.11 / Win64 Development',
        policy_events=3,new_policy_events=2,asset_family_count=3,native_python_timer_and_overlap_differential=rules,native_cpp_python_two_owner_same_accepted_blueprint_layer_regression=peers,
        native_timer_handles_scheduling_replication_onrep_collision_and_mesh_ticks_preserved=True,existing_spawner_eight_blueprint_entrypoints_preserved=True,
        cpp_reference_keeps_accepted_blueprint_python_layer=True,cpp_profiles=['Python','NativeFallback'],legacy_full_blueprint_fallback_mixed_stage_acceptance=False,
        network_authored_ten_second_cooldowns_preserved=True,fixture_only_shortened_cooldown=True,native_endplay_clears_both_handles_unchanged=True,
        compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'],
        reusable_native_objects=[dict(path=str(inter/('Module.LyraGame.'+str(i)+'.cpp.obj')),sha256=sha(inter/('Module.LyraGame.'+str(i)+'.cpp.obj'))) for i in (1,2,3)],
        official_reference_unchanged=True,engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,visible_rendering_acceptance=False,full_cpp_migration_acceptance=False,
        retained_attempts=['Build01','Assets01','Assets02','Assets03','Assets04','Assets05','Runtime01','Runtime02','Runtime03','Runtime04','Runtime05','Network01'],
        retained_notes=['Build01 stopped before C++ compilation because its dependency selector still named inventory headers.',
            'Assets01 found unregistered inherited Python methods; explicit aliases preserve all eight accepted Blueprint entrypoints.',
            'Assets02 differed only in sibling component export order; the existing canonical CDO parser preserves object payloads.',
            'Assets03 rejected direct registration of the inherited-only child interface; only the declaring parent is registered.',
            'Runtime01-05 attempted to combine original Blueprint fallback bodies with the new C++ stage; a grant could return success without an inventory change and Runtime03 hit an engine object-handle assertion. This full-Blueprint combination is not accepted or offered by the C++ Set.',
            'Runtime06 compares the original C++ bodies and Python rules with the accepted Blueprint Python layer held constant. Assets06 removes the unused legacy full-Blueprint profile; both selected eleven-function mappings are unchanged and exercised again by Network02.',
            'Network01 exposed inherited test modules auto-starting extra drivers; the new native lane is excluded from both base auto-start guards, and transient absent JSON is handled. Network02 passed all 36 scenarios.'],
        preserved_recompiled_blueprint_stash='Examples:36819836544ea97c7eca1d3fd0c173c27751562a',
        evidence=[evidence(root/'Build02/summary.json'),evidence(root/'Assets06/summary.json'),evidence(runtime/'summary.json'),evidence(network/'summary.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='accepted',batch='CPP06',candidates=1,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--network',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.runtime,a.network,a.output),indent=2))
