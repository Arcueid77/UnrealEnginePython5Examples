"""Add disposable map-value fixtures; recompile registration and its unity unit."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned successful build and fresh fixture output required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));old=json.loads((previous/'Plan/plan.json').read_text());stage=Path(old['stage'])
    if summary['status']!='built_requires_native_acceptance' or summary['error'] is not None:raise ValueError('Successful initial-stat build required')
    for row in summary['products']+summary['generated']+old['sources']+old['derived']+old['protected']:
        if digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Prior initial-stat build input/product changed: '+row['path'])
    output.mkdir(parents=True);(output/'PreviousBinaries').mkdir();shutil.copy2(old['binary'],output/'PreviousBinaries'/Path(old['binary']).name);shutil.copytree(previous/'SourcePatch',output/'SourcePatch')
    sources=[];targets=[]
    for suffix in ('.h','.cpp'):
        source=REPO/'Demos/UEPLyraIntegration/NativeFixtures'/('UEPNativeStatsFixture'+suffix);target=stage/'Source/LyraGame/UEPValidation'/source.name
        if target.exists():raise ValueError('Stats fixture already exists')
        shutil.copy2(source,target);sources.append(digest(source));targets.append(digest(target))
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame';unity=inter/'Module.LyraGame.2.cpp';shutil.copy2(unity,output/'PreviousUnity2.cpp')
    text=unity.read_text(encoding='utf-8-sig')+'\n#include "'+(stage/'Source/LyraGame/UEPValidation/UEPNativeStatsFixture.cpp').as_posix()+'"\n';unity.write_text(text,encoding='utf-8',newline='\n')
    manifest=json.loads(Path(old['uht_manifest']).read_text());module=next(m for m in manifest['Modules'] if m['Name']=='LyraGame');module['PublicHeaders'].append(str(stage/'Source/LyraGame/UEPValidation/UEPNativeStatsFixture.h'));manifest['ExternalDependenciesFile']=str(output/'LyraGameOnly.deps')
    plan_dir=output/'Plan';plan_dir.mkdir();manifest_path=plan_dir/'LyraEditor.LyraGameOnly.uhtmanifest';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    plan=dict(old);plan['sources']+=sources;plan['derived']=[digest(Path(r['path'])) if Path(r['path'])==unity else r for r in old['derived']]+targets+[digest(manifest_path)]
    plan['protected']+= [digest(inter/'Module.LyraGame.3.cpp.obj'),digest(output/'PreviousBinaries'/Path(old['binary']).name)]
    plan['steps']=[s for s in old['steps'] if s['tool']!='cl.exe' or any('Module.LyraGame.'+str(i)+'.cpp.obj.rsp' in s['rsp'] for i in (1,2))]
    plan.update(uht_manifest=str(manifest_path),previous_build=str(previous),compiled_unity_units=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp'],reused_unity_units=['Module.LyraGame.3.cpp'],stage_only_boundary_fixture=True,production_source_unchanged_from_previous_build=True)
    (plan_dir/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output),indent=2))
