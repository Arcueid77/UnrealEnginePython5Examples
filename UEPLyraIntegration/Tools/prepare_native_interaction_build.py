"""Compile only the LyraGame unity units affected by CPP08 and package registration."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest


def prepare(stage,baseline,output,previous_build=None):
    stage,baseline,output=(Path(p).resolve() for p in (stage,baseline,output));owned=REPO/'.build'
    if any(not p.is_relative_to(owned) for p in (stage,baseline,output)) or output.exists():raise ValueError('Owned stages and fresh interaction build plan required')
    for root in (stage,baseline):
        if not (root/'.uep-lyra-full-stage.json').is_file():raise ValueError('Both marked stages required')
    accepted=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP06-acceptance.json').read_text())
    if previous_build is not None:
        previous_build=Path(previous_build).resolve()
        if not previous_build.is_relative_to(owned):raise ValueError('Owned previous interaction build required')
        old=json.loads((previous_build/'summary.json').read_text(encoding='utf-8-sig'));old_plan=json.loads(Path(old['plan']['path']).read_text())
        if old['status']!='built_requires_native_acceptance' or old['error'] is not None:raise ValueError('Successful previous interaction build required')
        replaced={stage/'Source/LyraGame/Interaction/Abilities'/('LyraGameplayAbility_Interact'+s) for s in ('.h','.cpp')}
        for row in old['products']+old['generated']+old_plan['sources']+old_plan['derived']+old_plan['protected']:
            if Path(row['path']) not in replaced and digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Previous frozen interaction input changed: '+row['path'])
    for row in accepted['reusable_native_objects']:
        if previous_build is not None and Path(row['path']).name!='Module.LyraGame.3.cpp.obj':continue
        if digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Accepted spawner object changed')
    output.mkdir(parents=True)
    relative=Path('Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame')
    old_inter,new_inter=baseline/relative,stage/relative;new_inter.mkdir(parents=True,exist_ok=True)
    gen_relative=Path('Intermediate/Build/Win64/UnrealEditor/Inc/LyraGame/UHT')
    old_gen,new_gen=baseline/gen_relative,stage/gen_relative;new_gen.mkdir(parents=True,exist_ok=True)
    pairs=[(baseline/'Source/LyraGame',stage/'Source/LyraGame'),(old_inter,new_inter),(old_gen,new_gen),
        (baseline/'Binaries/Win64/UnrealEditor-LyraGame',stage/'Binaries/Win64/UnrealEditor-LyraGame')]
    def replace(text):
        for old,new in pairs:
            for a,b in ((str(old),str(new)),(old.as_posix(),new.as_posix())):text=text.replace(a,b)
        return text
    def rewrite(value):
        if isinstance(value,str):return replace(value)
        if isinstance(value,list):return [rewrite(v) for v in value]
        if isinstance(value,dict):return {k:rewrite(v) for k,v in value.items()}
        return value
    fixture_root=REPO/'Demos/UEPLyraIntegration/NativeFixtures'
    fixture_source=stage/'Source/LyraGame/UEPValidation';fixture_source.mkdir(parents=True,exist_ok=True)
    fixture_files=[fixture_root/('UEPNativeInteractionFixture'+suffix) for suffix in ('.h','.cpp')]
    for file in fixture_files:shutil.copy2(file,fixture_source/file.name)
    original_manifest=baseline/'Intermediate/Build/Win64/LyraEditor/LyraEditor.uhtmanifest'
    manifest=json.loads(original_manifest.read_text(encoding='utf-8-sig'))
    for i,module in enumerate(manifest['Modules']):
        module['SaveExportedHeaders']=module['Name']=='LyraGame'
        if module['Name']=='LyraGame':
            manifest['Modules'][i]=rewrite(module)
            manifest['Modules'][i]['PublicHeaders'].append(str(fixture_source/'UEPNativeInteractionFixture.h'))
    manifest['ExternalDependenciesFile']=str(output/'LyraGameOnly.deps')
    manifest_path=output/'LyraEditor.LyraGameOnly.uhtmanifest';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    for file in old_gen.rglob('*'):
        if file.is_file():
            target=new_gen/file.relative_to(old_gen);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(replace(file.read_text(encoding='utf-8-sig')),encoding='utf-8',newline='\n')
    selected=[];dependencies=[]
    for unity in sorted(old_inter.glob('Module.LyraGame.*.cpp')):
        dep=unity.with_suffix('.cpp.dep.json');data=json.loads(dep.read_text())['Data'];dependencies.append(digest(dep))
        # The generated package checksum unit must be rebuilt alongside the
        # compiler-reported units that include the changed interaction declaration.
        if any('lyragameplayability_interact.' in x.lower() for x in data['Includes']) or 'LyraGame.init.gen.cpp' in unity.read_text():selected.append(unity.name)
    if selected!=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp']:raise ValueError('Baseline interaction dependency partition changed')
    names=['PerModuleInline.gen.cpp','Definitions.LyraGame.h','LyraGame.Shared.rsp','UnrealEditor-LyraGame.lib.rsp','UnrealEditor-LyraGame.dll.rsp',*selected,*[n+'.obj.rsp' for n in selected]]
    sources=[digest(original_manifest),*dependencies,*[digest(f) for f in fixture_files]];derived=[digest(manifest_path)]
    for name in names:
        original=old_inter/name;target=new_inter/name;sources.append(digest(original));text=replace(original.read_text(encoding='utf-8-sig'))
        if name in ('UnrealEditor-LyraGame.lib.rsp','UnrealEditor-LyraGame.dll.rsp'):
            for unit in (1,2,3):text=text.replace(str(baseline/relative/f'Module.LyraGame.{unit}.cpp.obj'),str(stage/relative/f'Module.LyraGame.{unit}.cpp.obj'))
        if name=='Module.LyraGame.2.cpp':text+='\n#include "'+(fixture_source/'UEPNativeInteractionFixture.cpp').as_posix()+'"\n'
        target.write_text(text,encoding='utf-8',newline='\n');derived.append(digest(target))
    binary=stage/'Binaries/Win64/UnrealEditor-LyraGame.dll';previous=output/'PreviousBinaries';previous.mkdir();shutil.copy2(binary,previous/binary.name)
    protected=[digest(stage/relative/'Module.LyraGame.3.cpp.obj'),digest(baseline/'Binaries/Win64/UnrealEditor-LyraGame.dll'),digest(previous/binary.name)]
    for path in (baseline/'Source/LyraGame').rglob('*'):
        if path.is_file():protected.append(digest(path))
    for path in (stage/'Source/LyraGame').rglob('*'):
        if path.is_file():derived.append(digest(path))
    for root in (baseline,stage):
        for plugin in ('UnrealEnginePython','UEPLyraBridge'):
            protected.append(digest(root/f'Plugins/{plugin}/Binaries/Win64/UnrealEditor-{plugin}.dll'))
    protected.append(digest(stage/'Plugins/GameFeatures/ShooterCore/Binaries/Win64/UnrealEditor-ShooterCoreRuntime.dll'))
    for relative in ('Engine/Binaries/Win64/UnrealEditor.exe','Engine/Binaries/Win64/UnrealEditor-Core.dll','Engine/Binaries/Win64/UnrealEditor-Engine.dll','Engine/Build/Build.version'):
        protected.append(digest(Path('F:/UnrealEngine')/relative))
    steps=[dict(name='compile-'+str(i+1),tool='cl.exe',rsp=str(new_inter/(name+'.obj.rsp'))) for i,name in enumerate(selected)]
    steps.extend([dict(name='import-library',tool='link.exe',rsp=str(new_inter/'UnrealEditor-LyraGame.lib.rsp')),dict(name='link-dll',tool='link.exe',rsp=str(new_inter/'UnrealEditor-LyraGame.dll.rsp'))])
    report=dict(schema_version=1,status='planned',module='LyraGame',stage=str(stage),baseline=str(baseline),uht_manifest=str(manifest_path),uht_export_modules=['LyraGame'],
        generated_directory=str(new_gen),binary=str(binary),steps=steps,sources=sources,derived=derived,protected=protected,
        compiled_unity_units=selected,reused_unity_units=['Module.LyraGame.3.cpp'],compiler_dependency_partition_verified=True,stage_only_native_interface_and_gas_fixtures=True,engine_compile_planned=False,runtime_acceptance=False)
    (output/'plan.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='planned',compiled_unity_units=selected,reused_unity_units=report['reused_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--baseline',required=True);p.add_argument('--output',required=True);p.add_argument('--previous-build');a=p.parse_args();print(json.dumps(prepare(a.stage,a.baseline,a.output,a.previous_build)))
