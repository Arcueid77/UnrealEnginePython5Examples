"""Recompile only changed policy bodies, retaining UHT and other modules."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest

def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned baseline and fresh body-repair plan required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));plan=json.loads((previous/'Plan/plan.json').read_text(encoding='utf-8-sig'));stage=Path(plan['stage'])
    if summary['status']!='built_requires_native_acceptance' or summary['error'] is not None:raise ValueError('Successful latest native binary required')
    from native_policy_carrier_patches import sources as carrier_sources
    source=REPO/'Demos/UEPLyraIntegration/NativePolicyAdapters/UEPNativeWorldPolicies.cpp';world_target=stage/'Source/LyraGame/UEPPolicy'/source.name
    carrier=REPO/'Demos/UEPLyraIntegration/Tools/native_policy_carrier_patches.py'
    changed={}
    if source.read_text(encoding='utf-8-sig')!=world_target.read_text(encoding='utf-8-sig'):changed[world_target]=source.read_text(encoding='utf-8-sig')
    reset=carrier_sources()[0];reset_target=stage/reset['relative']
    if reset_target.read_text(encoding='utf-8-sig')!=reset['after']:changed[reset_target]=reset['after']
    if not changed:raise ValueError('No policy body change to compile')
    for row in summary['products']+summary['generated']+plan['sources']+plan['derived']+plan['protected']:
        if Path(row['path']) not in (source,carrier) and digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Unrelated hardening input changed: '+row['path'])
    output.mkdir(parents=True);backup=output/'PreviousBinaries';backup.mkdir();shutil.copy2(plan['binary'],backup/Path(plan['binary']).name);(output/'PreviousSources').mkdir()
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    selected=[];dependencies=[]
    (output/'DependencyInputs').mkdir()
    for i in (1,2,3):
        dep=inter/f'Module.LyraGame.{i}.cpp.dep.json';copy=output/'DependencyInputs'/dep.name;shutil.copy2(dep,copy);dependencies.append(digest(copy))
        includes={str(p).replace('\\','/').casefold() for p in json.loads(copy.read_text())['Data']['Includes']}
        if includes & {p.as_posix().casefold() for p in changed}:selected.append(i)
    if not selected:raise ValueError('Changed policy body absent from compiler dependencies')
    for target,text in changed.items():
        shutil.copy2(target,output/'PreviousSources'/target.name);target.write_text(text,encoding='utf-8',newline='\n')
    plan['sources']=[digest(Path(r['path'])) if Path(r['path']) in (source,carrier) else r for r in plan['sources']]+dependencies+[digest(carrier)]
    plan['derived']=[digest(Path(r['path'])) if Path(r['path']) in changed else r for r in plan['derived']]
    selected_objects={inter/f'Module.LyraGame.{i}.cpp.obj' for i in selected}
    plan['protected']=[r for r in plan['protected'] if Path(r['path']) not in selected_objects]+[digest(backup/Path(plan['binary']).name)]
    reused=[i for i in (1,2,3) if i not in selected]
    plan['protected']+=[digest(inter/f'Module.LyraGame.{i}.cpp.obj') for i in reused]
    plan['steps']=[dict(name='compile-'+str(i),tool='cl.exe',rsp=str(inter/f'Module.LyraGame.{i}.cpp.obj.rsp')) for i in selected]+[step for step in plan['steps'] if step['name'] in ('import-library','link-dll')]
    plan.update(previous_build=str(previous),compiled_unity_units=[f'Module.LyraGame.{i}.cpp' for i in selected],reused_unity_units=[f'Module.LyraGame.{i}.cpp' for i in reused]+['Module.TopDownArenaRuntime.cpp'],uht_export_modules=[],header_generation_executed=False,compiler_dependency_partition_verified=True)
    (output/'Plan').mkdir();(output/'Plan/plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n')
    (output/'reused-generated.json').write_text(json.dumps(summary['generated'],indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output)))
