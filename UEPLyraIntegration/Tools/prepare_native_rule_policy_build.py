"""Compile only changed LyraGame units and the single TopDownArena unity unit."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest

TA=Path('Plugins/GameFeatures/TopDownArena')


def prepare(previous,baseline,output):
    previous,baseline,output=(Path(p).resolve() for p in (previous,baseline,output))
    if any(not p.is_relative_to(REPO/'.build') for p in (previous,baseline,output)) or output.exists():raise ValueError('Owned baselines and fresh rule build output required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));old=json.loads((previous/'Plan/plan.json').read_text());stage=Path(old['stage']);changed={Path(r['path']) for r in json.loads((output.parent/'SourcePatch/summary.json').read_text())['sources']}
    if summary['status']!='built_requires_native_acceptance':raise ValueError('Accepted world-policy binary required')
    for row in summary['products']+summary['generated']+old['sources']+old['derived']+old['protected']:
        if Path(row['path']) not in changed and digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Rule baseline changed: '+row['path'])
    output.mkdir(parents=True);backup=output/'PreviousBinaries';backup.mkdir();shutil.copy2(old['binary'],backup/Path(old['binary']).name)
    inputs=[digest(REPO/'Demos/UEPLyraIntegration/NativePolicyAdapters'/('UEPNativeRulePolicies'+suffix)) for suffix in ('.h','.cpp')]
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame';unity=inter/'Module.LyraGame.3.cpp';shutil.copy2(unity,output/'PreviousUnity3.cpp')
    unity.write_text(unity.read_text(encoding='utf-8-sig')+'\n#include "'+(stage/'Source/LyraGame/UEPPolicy/UEPNativeRulePolicies.cpp').as_posix()+'"\n',encoding='utf-8',newline='\n')
    manifest=json.loads(Path(old['uht_manifest']).read_text());module=next(m for m in manifest['Modules'] if m['Name']=='LyraGame');module['PublicHeaders'].append(str(stage/'Source/LyraGame/UEPPolicy/UEPNativeRulePolicies.h'));manifest['ExternalDependenciesFile']=str(output/'LyraGameOnly.deps');manifest_path=output/'LyraEditor.LyraGameOnly.uhtmanifest';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    selected={inter/f'Module.LyraGame.{i}.cpp.obj' for i in (1,2,3)}
    protected=[row for row in old['protected'] if Path(row['path']) not in selected and not Path(row['path']).is_relative_to(Path(old['generated_directory'])) and not Path(row['path']).is_relative_to(stage/TA/'Binaries')]
    protected.append(digest(backup/Path(old['binary']).name))
    for i in (1,2,3):
        obj=inter/f'Module.LyraGame.{i}.cpp.obj';copy=backup/obj.name;shutil.copy2(obj,copy);protected.append(digest(copy))
    # Reuse the validated module's compiler settings and generated headers,
    # rebasing every project path to the advancing private stage.
    old_inter=baseline/TA/'Intermediate/Build/Win64/x64/UnrealEditor/Development/TopDownArenaRuntime';ta_inter=stage/TA/'Intermediate/Build/Win64/x64/UnrealEditor/Development/TopDownArenaRuntime';ta_inter.mkdir(parents=True,exist_ok=True)
    old_gen=baseline/TA/'Intermediate/Build/Win64/UnrealEditor/Inc/TopDownArenaRuntime/UHT';ta_gen=stage/TA/'Intermediate/Build/Win64/UnrealEditor/Inc/TopDownArenaRuntime/UHT';ta_gen.mkdir(parents=True,exist_ok=True)
    def rebase(text):
        for a,b in ((str(baseline),str(stage)),(baseline.as_posix(),stage.as_posix())):text=text.replace(a,b)
        return text
    ta_derived=[]
    for p in old_gen.rglob('*'):
        if p.is_file():
            target=ta_gen/p.relative_to(old_gen);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(rebase(p.read_text(encoding='utf-8-sig')),encoding='utf-8',newline='\n');inputs.append(digest(p));ta_derived.append(digest(target))
    for name in ('Module.TopDownArenaRuntime.cpp','PerModuleInline.gen.cpp','Definitions.TopDownArenaRuntime.h','TopDownArenaRuntime.Shared.rsp','Module.TopDownArenaRuntime.cpp.obj.rsp','UnrealEditor-TopDownArenaRuntime.lib.rsp','UnrealEditor-TopDownArenaRuntime.dll.rsp'):
        p=old_inter/name;target=ta_inter/name;target.write_text(rebase(p.read_text(encoding='utf-8-sig')),encoding='utf-8',newline='\n');inputs.append(digest(p));ta_derived.append(digest(target))
        if str(baseline).casefold() in target.read_text().casefold() or baseline.as_posix().casefold() in target.read_text().casefold():raise ValueError('TopDown response still writes the old stage')
    ta_binary=stage/TA/'Binaries/Win64/UnrealEditor-TopDownArenaRuntime.dll';shutil.copy2(ta_binary,backup/ta_binary.name);protected.append(digest(backup/ta_binary.name))
    for p in (baseline/TA/'Source').rglob('*'):
        if p.is_file():inputs.append(digest(p))
    for p in (stage/TA/'Source').rglob('*'):
        if p.is_file():ta_derived.append(digest(p))
    plan=dict(old);plan['sources']+=inputs
    plan['derived']=[digest(Path(row['path'])) if Path(row['path']) in changed|{unity} else row for row in old['derived']]+[digest(manifest_path)]+[digest(p) for p in changed if not any(Path(row['path'])==p for row in old['derived'])]+ta_derived
    plan['protected']=protected
    plan['steps']=[dict(name='compile-'+str(i),tool='cl.exe',rsp=str(inter/f'Module.LyraGame.{i}.cpp.obj.rsp')) for i in (1,2,3)]+[s for s in old['steps'] if s['tool']!='cl.exe']+[
        dict(name='compile-topdown',tool='cl.exe',rsp=str(ta_inter/'Module.TopDownArenaRuntime.cpp.obj.rsp')),
        dict(name='import-library-topdown',tool='link.exe',rsp=str(ta_inter/'UnrealEditor-TopDownArenaRuntime.lib.rsp')),
        dict(name='link-dll-topdown',tool='link.exe',rsp=str(ta_inter/'UnrealEditor-TopDownArenaRuntime.dll.rsp'))]
    plan.update(previous_build=str(previous),topdown_compiler_baseline=str(baseline),topdown_binary=str(ta_binary),uht_manifest=str(manifest_path),uht_export_modules=['LyraGame'],header_generation_executed=True,compiled_unity_units=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp','Module.LyraGame.3.cpp','Module.TopDownArenaRuntime.cpp'],reused_unity_units=[])
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],engine_compile_planned=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--baseline',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.baseline,a.output),indent=2))
