"""Compile the new carrier/protection fixture and Reset body, retaining unit 3."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned lifecycle baseline and fresh carrier build required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));old=json.loads((previous/'Plan/plan.json').read_text());stage=Path(old['stage']);changed={Path(r['path']) for r in json.loads((output.parent/'SourcePatch/summary.json').read_text())['sources']}
    if summary['status']!='built_requires_native_acceptance':raise ValueError('Successful lifecycle binary required')
    for r in summary['products']+summary['generated']+old['sources']+old['derived']+old['protected']:
        if Path(r['path']) not in changed and digest(Path(r['path']))['sha256']!=r['sha256']:raise ValueError('Carrier baseline changed: '+r['path'])
    output.mkdir(parents=True);(output/'PreviousBinaries').mkdir();shutil.copy2(old['binary'],output/'PreviousBinaries'/Path(old['binary']).name);inputs=[];targets=[]
    for suffix in ('.h','.cpp'):
        p=REPO/'Demos/UEPLyraIntegration/NativeFixtures'/('UEPNativeProtectionFixture'+suffix);target=stage/'Source/LyraGame/UEPValidation'/p.name
        if target.exists():raise ValueError('Protection fixture already exists')
        shutil.copy2(p,target);inputs.append(digest(p));targets.append(digest(target))
        carrier=REPO/'Demos/UEPLyraIntegration/NativePolicyAdapters'/('UEPNativeGameplayPolicy'+suffix);inputs.append(digest(carrier))
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame';unity=inter/'Module.LyraGame.2.cpp';shutil.copy2(unity,output/'PreviousUnity2.cpp');unity.write_text(unity.read_text(encoding='utf-8-sig')+'\n#include "'+(stage/'Source/LyraGame/UEPPolicy/UEPNativeGameplayPolicy.cpp').as_posix()+'"\n#include "'+(stage/'Source/LyraGame/UEPValidation/UEPNativeProtectionFixture.cpp').as_posix()+'"\n',encoding='utf-8',newline='\n')
    manifest=json.loads(Path(old['uht_manifest']).read_text());module=next(m for m in manifest['Modules'] if m['Name']=='LyraGame');module['PublicHeaders']+=[str(stage/'Source/LyraGame/UEPPolicy/UEPNativeGameplayPolicy.h'),str(stage/'Source/LyraGame/UEPValidation/UEPNativeProtectionFixture.h')];manifest['ExternalDependenciesFile']=str(output/'LyraGameOnly.deps');manifest_path=output/'LyraEditor.LyraGameOnly.uhtmanifest';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    selected={inter/f'Module.LyraGame.{i}.cpp.obj' for i in (1,2)};protected=[r for r in old['protected'] if Path(r['path']) not in selected and not Path(r['path']).is_relative_to(Path(old['generated_directory']))]+[digest(inter/'Module.LyraGame.3.cpp.obj'),digest(output/'PreviousBinaries'/Path(old['binary']).name)]
    for i in (1,2,3):
        obj=inter/f'Module.LyraGame.{i}.cpp.obj';backup=output/'PreviousBinaries'/obj.name;shutil.copy2(obj,backup);protected.append(digest(backup))
    plan=dict(old);plan['sources']+=inputs;plan['derived']=[digest(Path(r['path'])) if Path(r['path']) in changed|{unity} else r for r in old['derived']]+targets+[digest(manifest_path)]+[digest(p) for p in changed if not any(Path(r['path'])==p for r in old['derived'])];plan['protected']=protected
    plan['steps']=[dict(name='compile-'+str(i),tool='cl.exe',rsp=str(inter/f'Module.LyraGame.{i}.cpp.obj.rsp')) for i in (1,2)]+[s for s in old['steps'] if s['tool']!='cl.exe'];plan.update(previous_build=str(previous),uht_manifest=str(manifest_path),uht_export_modules=['LyraGame'],header_generation_executed=True,compiled_unity_units=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp'],reused_unity_units=['Module.LyraGame.3.cpp'])
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output),indent=2))
