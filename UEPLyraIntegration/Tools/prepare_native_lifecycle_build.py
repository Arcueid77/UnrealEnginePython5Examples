"""Advance the accepted cost stage, archiving its binary and only compiling dependencies."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned accepted baseline and fresh output required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));old=json.loads((previous/'Plan/plan.json').read_text());stage=Path(old['stage']);changed={Path(r['path']) for r in json.loads((output.parent/'SourcePatch/summary.json').read_text())['sources']}
    if summary['status']!='built_requires_native_acceptance' or summary['error'] is not None:raise ValueError('Successful native baseline required')
    for row in summary['products']+summary['generated']+old['sources']+old['derived']+old['protected']:
        if Path(row['path']) not in changed and digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Native lifecycle baseline changed: '+row['path'])
    output.mkdir(parents=True);backup=output/'PreviousBinaries';backup.mkdir();shutil.copy2(old['binary'],backup/Path(old['binary']).name)
    sources=[];targets=[]
    for suffix in ('.h','.cpp'):
        p=REPO/'Demos/UEPLyraIntegration/NativeFixtures'/('UEPNativeLifecycleFixture'+suffix);target=stage/'Source/LyraGame/UEPValidation'/p.name
        if target.exists():raise ValueError('Lifecycle fixture exists')
        shutil.copy2(p,target);sources.append(digest(p));targets.append(digest(target))
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame';unity=inter/'Module.LyraGame.2.cpp';shutil.copy2(unity,output/'PreviousUnity2.cpp');unity.write_text(unity.read_text(encoding='utf-8-sig')+'\n#include "'+(stage/'Source/LyraGame/UEPValidation/UEPNativeLifecycleFixture.cpp').as_posix()+'"\n',encoding='utf-8',newline='\n')
    manifest=json.loads(Path(old['uht_manifest']).read_text());module=next(m for m in manifest['Modules'] if m['Name']=='LyraGame');module['PublicHeaders'].append(str(stage/'Source/LyraGame/UEPValidation/UEPNativeLifecycleFixture.h'));manifest['ExternalDependenciesFile']=str(output/'LyraGameOnly.deps');manifest_path=output/'LyraEditor.LyraGameOnly.uhtmanifest';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    changed_headers={str(p).replace('\\','/').lower() for p in changed if p.suffix=='.h'};selected=[];dependencies=[];(output/'DependencyInputs').mkdir()
    for i in (1,2,3):
        dep=inter/f'Module.LyraGame.{i}.cpp.dep.json';archive=output/'DependencyInputs'/dep.name;shutil.copy2(dep,archive);dependencies.append(digest(archive));includes={p.replace('\\','/').lower() for p in json.loads(dep.read_text())['Data']['Includes']}
        if i==2 or changed_headers&includes:selected.append(i)
    if 1 not in selected or 2 not in selected:raise ValueError('Lifecycle dependency partition incomplete')
    objects={inter/f'Module.LyraGame.{i}.cpp.obj' for i in selected};protected=[r for r in old['protected'] if Path(r['path']) not in objects and not Path(r['path']).is_relative_to(Path(old['generated_directory']))]+[digest(backup/Path(old['binary']).name)]
    for i in (1,2,3):
        obj=inter/f'Module.LyraGame.{i}.cpp.obj';shutil.copy2(obj,backup/obj.name);protected.append(digest(backup/obj.name))
        if i not in selected:protected.append(digest(obj))
    plan=dict(old);plan['sources']+=sources+dependencies;plan['derived']=[digest(Path(r['path'])) if Path(r['path']) in changed|{unity} else r for r in old['derived']]+targets+[digest(manifest_path)]+[digest(p) for p in changed if not any(Path(r['path'])==p for r in old['derived'])]
    plan['protected']=protected;plan['steps']=[dict(name='compile-'+str(i),tool='cl.exe',rsp=str(inter/f'Module.LyraGame.{i}.cpp.obj.rsp')) for i in selected]+[s for s in old['steps'] if s['tool']!='cl.exe']
    plan.update(previous_build=str(previous),uht_manifest=str(manifest_path),uht_export_modules=['LyraGame'],header_generation_executed=True,compiled_unity_units=[f'Module.LyraGame.{i}.cpp' for i in selected],reused_unity_units=[f'Module.LyraGame.{i}.cpp' for i in (1,2,3) if i not in selected])
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output),indent=2))
