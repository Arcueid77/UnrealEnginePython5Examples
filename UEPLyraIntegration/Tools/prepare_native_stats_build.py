"""Rebase CPP09's exact native inputs into the independent CPP10 stage."""
import argparse
import json
from pathlib import Path
import re
import shutil
from prepare_native_message_build import REPO,digest


def prepare(stage,baseline,output):
    stage,baseline,output=(Path(p).resolve() for p in (stage,baseline,output))
    if not stage.is_relative_to(REPO/'.build/LyraValidation/CppGameplayExtended') or not baseline.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Independent extended stage and fresh plan required')
    output.mkdir(parents=True)
    relative=Path('Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame');gen_relative=Path('Intermediate/Build/Win64/UnrealEditor/Inc/LyraGame/UHT')
    old_inter,new_inter=baseline/relative,stage/relative;old_gen,new_gen=baseline/gen_relative,stage/gen_relative
    new_inter.mkdir(parents=True,exist_ok=True);new_gen.mkdir(parents=True,exist_ok=True)
    pairs=[(baseline/'Source/LyraGame',stage/'Source/LyraGame'),(old_inter,new_inter),(old_gen,new_gen),(baseline/'Binaries/Win64/UnrealEditor-LyraGame',stage/'Binaries/Win64/UnrealEditor-LyraGame')]
    def replace(text):
        for old,new in pairs:
            for a,b in ((str(old),str(new)),(old.as_posix(),new.as_posix())):text=re.sub(re.escape(a),lambda m:b,text,flags=re.IGNORECASE)
        return text
    def rewrite(value):
        if isinstance(value,str):return replace(value)
        if isinstance(value,list):return [rewrite(v) for v in value]
        if isinstance(value,dict):return {k:rewrite(v) for k,v in value.items()}
        return value
    previous=REPO/'.build/LyraValidation/CppGameplay/20261101-CPP09/Build01/summary.json';accepted=json.loads(previous.read_text(encoding='utf-8-sig'))
    for row in accepted['products']:
        if digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Preserved CPP09 binary changed')
    original_manifest=REPO/'.build/LyraValidation/CppGameplay/20261101-CPP09/Build01/Plan/LyraEditor.LyraGameOnly.uhtmanifest'
    manifest=json.loads(original_manifest.read_text(encoding='utf-8-sig'))
    for i,module in enumerate(manifest['Modules']):
        module['SaveExportedHeaders']=module['Name']=='LyraGame'
        if module['Name']=='LyraGame':manifest['Modules'][i]=rewrite(module)
    manifest['ExternalDependenciesFile']=str(output/'LyraGameOnly.deps');manifest_path=output/'LyraEditor.LyraGameOnly.uhtmanifest';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    for file in old_gen.rglob('*'):
        if file.is_file():
            target=new_gen/file.relative_to(old_gen);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(replace(file.read_text(encoding='utf-8-sig')),encoding='utf-8',newline='\n')
    selected=[];dependencies=[]
    for unity in sorted(old_inter.glob('Module.LyraGame.*.cpp')):
        dep=unity.with_suffix('.cpp.dep.json');dependencies.append(digest(dep));includes=json.loads(dep.read_text())['Data']['Includes']
        if any(p.lower().endswith(('inventoryfragment_setstats.h','lyrainventoryitemdefinition.h')) for p in includes) or 'LyraGame.init.gen.cpp' in unity.read_text():selected.append(unity.name)
    if selected!=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp','Module.LyraGame.3.cpp']:raise ValueError('Initial-stat compiler dependency partition changed')
    names=['PerModuleInline.gen.cpp','Definitions.LyraGame.h','LyraGame.Shared.rsp','UnrealEditor-LyraGame.lib.rsp','UnrealEditor-LyraGame.dll.rsp',*selected,*[n+'.obj.rsp' for n in selected]]
    sources=[digest(original_manifest),*dependencies];derived=[digest(manifest_path)];protected=[digest(baseline/'Binaries/Win64/UnrealEditor-LyraGame.dll')]
    for name in names:
        original=old_inter/name;target=new_inter/name;sources.append(digest(original));target.write_text(replace(original.read_text(encoding='utf-8-sig')),encoding='utf-8',newline='\n');derived.append(digest(target))
    for root in (baseline,stage):
        for plugin in ('UnrealEnginePython','UEPLyraBridge'):protected.append(digest(root/f'Plugins/{plugin}/Binaries/Win64/UnrealEditor-{plugin}.dll'))
        protected.append(digest(root/'Plugins/GameFeatures/ShooterCore/Binaries/Win64/UnrealEditor-ShooterCoreRuntime.dll'))
    for file in (baseline/'Source/LyraGame').rglob('*'):
        if file.is_file():protected.append(digest(file))
    for file in (stage/'Source/LyraGame').rglob('*'):
        if file.is_file():derived.append(digest(file))
    for unit in (1,2,3):protected.append(digest(old_inter/f'Module.LyraGame.{unit}.cpp.obj'))
    binary=stage/'Binaries/Win64/UnrealEditor-LyraGame.dll';previous_dir=output/'PreviousBinaries';previous_dir.mkdir();shutil.copy2(binary,previous_dir/binary.name);protected.append(digest(previous_dir/binary.name))
    for relative in ('Engine/Binaries/Win64/UnrealEditor.exe','Engine/Binaries/Win64/UnrealEditor-Core.dll','Engine/Binaries/Win64/UnrealEditor-Engine.dll','Engine/Build/Build.version'):protected.append(digest(Path('F:/UnrealEngine')/relative))
    steps=[dict(name='compile-'+str(i+1),tool='cl.exe',rsp=str(new_inter/(name+'.obj.rsp'))) for i,name in enumerate(selected)]
    steps.extend([dict(name='import-library',tool='link.exe',rsp=str(new_inter/'UnrealEditor-LyraGame.lib.rsp')),dict(name='link-dll',tool='link.exe',rsp=str(new_inter/'UnrealEditor-LyraGame.dll.rsp'))])
    plan=dict(status='planned',module='LyraGame',stage=str(stage),baseline=str(baseline),uht_manifest=str(manifest_path),uht_export_modules=['LyraGame'],generated_directory=str(new_gen),binary=str(binary),steps=steps,sources=sources,derived=derived,protected=protected,compiled_unity_units=selected,reused_unity_units=[],compiler_dependency_partition_verified=True,preserved_cpp09_stage=True,engine_compile_planned=False,runtime_acceptance=False)
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=selected)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--baseline',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.stage,a.baseline,a.output),indent=2))
