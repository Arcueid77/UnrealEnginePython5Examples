"""Compile shared cost hooks and staged GAS fixtures once for CPP11/CPP12."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned initial-stat baseline and fresh cost plan required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));old=json.loads((previous/'Plan/plan.json').read_text());stage=Path(old['stage'])
    if summary['status']!='built_requires_native_acceptance' or summary['error'] is not None:raise ValueError('Successful initial-stat build required')
    patched=json.loads((output.parent/'SourcePatch/summary.json').read_text());changed={Path(r['path']) for r in patched['sources']}
    for row in summary['products']+summary['generated']+old['sources']+old['derived']+old['protected']:
        if Path(row['path']) in changed:continue
        if digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Initial-stat baseline changed: '+row['path'])
    output.mkdir(parents=True);backup=output/'PreviousBinaries';backup.mkdir();shutil.copy2(old['binary'],backup/Path(old['binary']).name)
    sources=[];targets=[]
    for suffix in ('.h','.cpp'):
        source=REPO/'Demos/UEPLyraIntegration/NativeFixtures'/('UEPNativeCostFixture'+suffix);target=stage/'Source/LyraGame/UEPValidation'/source.name
        if target.exists():raise ValueError('Cost fixture already exists')
        shutil.copy2(source,target);sources.append(digest(source));targets.append(digest(target))
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame';unity=inter/'Module.LyraGame.2.cpp';shutil.copy2(unity,output/'PreviousUnity2.cpp')
    unity.write_text(unity.read_text(encoding='utf-8-sig')+'\n#include "'+(stage/'Source/LyraGame/UEPValidation/UEPNativeCostFixture.cpp').as_posix()+'"\n',encoding='utf-8',newline='\n')
    manifest=json.loads(Path(old['uht_manifest']).read_text());module=next(m for m in manifest['Modules'] if m['Name']=='LyraGame')
    module['PublicHeaders'] += [str(stage/'Source/LyraGame/UEPValidation/UEPNativeCostFixture.h'),str(stage/'Source/LyraGame/AbilitySystem/Abilities/LyraTagStackCostPolicy.h')]
    manifest['ExternalDependenciesFile']=str(output/'LyraGameOnly.deps');manifest_path=output/'LyraEditor.LyraGameOnly.uhtmanifest';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    dependencies=[];selected=[];dependency_inputs=output/'DependencyInputs';dependency_inputs.mkdir()
    for i in (1,2,3):
        dep=inter/f'Module.LyraGame.{i}.cpp.dep.json';archive=dependency_inputs/dep.name;shutil.copy2(dep,archive);dependencies.append(digest(archive))
        if any(p.lower().endswith('lyragameplayability.h') for p in json.loads(dep.read_text())['Data']['Includes']):selected.append(i)
    if selected!=[1,2,3]:raise ValueError('Cost declaration dependency partition changed')
    objpaths={inter/f'Module.LyraGame.{i}.cpp.obj' for i in (1,2,3)}
    protected=[r for r in old['protected'] if Path(r['path']) not in objpaths and not Path(r['path']).is_relative_to(Path(old['generated_directory']))]+[digest(backup/Path(old['binary']).name)]
    for p in objpaths:shutil.copy2(p,backup/p.name);protected.append(digest(backup/p.name))
    plan=dict(old);plan['sources']+=sources+dependencies
    plan['derived']=[digest(Path(r['path'])) if Path(r['path']) in changed|{unity} else r for r in old['derived']]+targets+[digest(manifest_path)]+[digest(p) for p in changed if not any(Path(r['path'])==p for r in old['derived'])]
    plan['protected']=protected;plan['steps']=[dict(name='compile-'+str(i),tool='cl.exe',rsp=str(inter/f'Module.LyraGame.{i}.cpp.obj.rsp')) for i in (1,2,3)]+[s for s in old['steps'] if s['tool']!='cl.exe']
    plan.update(uht_manifest=str(manifest_path),uht_export_modules=['LyraGame'],header_generation_executed=True,previous_build=str(previous),compiled_unity_units=['Module.LyraGame.'+str(i)+'.cpp' for i in (1,2,3)],reused_unity_units=[],shared_cost_hooks_for_cpp11_and_cpp12=True)
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output),indent=2))
