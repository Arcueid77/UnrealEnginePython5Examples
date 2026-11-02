"""Compile LyraGame units 1/3 for the world policies, retaining unit 2."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned previous build and fresh output required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));old=json.loads((previous/'Plan/plan.json').read_text());stage=Path(old['stage']);changed={Path(r['path']) for r in json.loads((output.parent/'SourcePatch/summary.json').read_text())['sources']}
    if summary['status']!='built_requires_native_acceptance':raise ValueError('Successful carrier binary required')
    for row in summary['products']+summary['generated']+old['sources']+old['derived']+old['protected']:
        if Path(row['path']) not in changed and digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('World-policy baseline changed: '+row['path'])
    output.mkdir(parents=True);(output/'PreviousBinaries').mkdir();shutil.copy2(old['binary'],output/'PreviousBinaries'/Path(old['binary']).name)
    inputs=[digest(REPO/'Demos/UEPLyraIntegration/NativePolicyAdapters'/('UEPNativeWorldPolicies'+suffix)) for suffix in ('.h','.cpp')]
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame';unity=inter/'Module.LyraGame.3.cpp';shutil.copy2(unity,output/'PreviousUnity3.cpp')
    unity.write_text(unity.read_text(encoding='utf-8-sig')+'\n#include "'+(stage/'Source/LyraGame/UEPPolicy/UEPNativeWorldPolicies.cpp').as_posix()+'"\n',encoding='utf-8',newline='\n')
    manifest=json.loads(Path(old['uht_manifest']).read_text());module=next(m for m in manifest['Modules'] if m['Name']=='LyraGame');module['PublicHeaders'].append(str(stage/'Source/LyraGame/UEPPolicy/UEPNativeWorldPolicies.h'));manifest['ExternalDependenciesFile']=str(output/'LyraGameOnly.deps');manifest_path=output/'LyraEditor.LyraGameOnly.uhtmanifest';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    selected={inter/f'Module.LyraGame.{i}.cpp.obj' for i in (1,3)};protected=[row for row in old['protected'] if Path(row['path']) not in selected and not Path(row['path']).is_relative_to(Path(old['generated_directory']))]+[digest(inter/'Module.LyraGame.2.cpp.obj'),digest(output/'PreviousBinaries'/Path(old['binary']).name)]
    for i in (1,2,3):
        obj=inter/f'Module.LyraGame.{i}.cpp.obj';backup=output/'PreviousBinaries'/obj.name;shutil.copy2(obj,backup);protected.append(digest(backup))
    plan=dict(old);plan['sources']+=inputs;plan['derived']=[digest(Path(row['path'])) if Path(row['path']) in changed|{unity} else row for row in old['derived']]+[digest(manifest_path)]+[digest(p) for p in changed if not any(Path(row['path'])==p for row in old['derived'])];plan['protected']=protected
    plan['steps']=[dict(name='compile-'+str(i),tool='cl.exe',rsp=str(inter/f'Module.LyraGame.{i}.cpp.obj.rsp')) for i in (1,3)]+[s for s in old['steps'] if s['tool']!='cl.exe'];plan.update(previous_build=str(previous),uht_manifest=str(manifest_path),uht_export_modules=['LyraGame'],header_generation_executed=True,compiled_unity_units=['Module.LyraGame.1.cpp','Module.LyraGame.3.cpp'],reused_unity_units=['Module.LyraGame.2.cpp'])
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output),indent=2))
