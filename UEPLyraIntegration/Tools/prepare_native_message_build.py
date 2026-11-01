"""Derive an owned ShooterCore-only header/code compile plan from the accepted baseline."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

REPO=Path(__file__).resolve().parents[3]
MODULE=Path('Plugins/GameFeatures/ShooterCore')


def digest(path):return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper())


def prepare(stage,baseline,output):
    stage,baseline,output=(Path(p).resolve() for p in (stage,baseline,output))
    owned=(REPO/'.build').resolve()
    if any(not p.is_relative_to(owned) for p in (stage,baseline,output)) or output.exists():
        raise ValueError('Owned stages and a fresh build plan directory required')
    if not (stage/'.uep-lyra-full-stage.json').is_file() or not (baseline/'.uep-lyra-full-stage.json').is_file():
        raise ValueError('Both stage markers are required')
    output.mkdir(parents=True)
    old_root,new_root=baseline/MODULE,stage/MODULE
    old_intermediate=old_root/'Intermediate/Build/Win64/x64/UnrealEditor/Development/ShooterCoreRuntime'
    new_intermediate=new_root/'Intermediate/Build/Win64/x64/UnrealEditor/Development/ShooterCoreRuntime'
    new_intermediate.mkdir(parents=True,exist_ok=True)
    old_manifest=baseline/'Intermediate/Build/Win64/LyraEditor/LyraEditor.uhtmanifest'
    old_gen=old_root/'Intermediate/Build/Win64/UnrealEditor/Inc/ShooterCoreRuntime/UHT'
    new_gen=new_root/'Intermediate/Build/Win64/UnrealEditor/Inc/ShooterCoreRuntime/UHT'
    new_gen.mkdir(parents=True,exist_ok=True)

    def text_replace(text):
        for old,new in ((str(old_root),str(new_root)),(old_root.as_posix(),new_root.as_posix())):
            text=text.replace(old,new)
        return text

    def rewrite(value):
        if isinstance(value,str):return text_replace(value)
        if isinstance(value,list):return [rewrite(v) for v in value]
        if isinstance(value,dict):return {k:rewrite(v) for k,v in value.items()}
        return value

    manifest=json.loads(old_manifest.read_text(encoding='utf-8-sig'))
    for i,module in enumerate(manifest['Modules']):
        module['SaveExportedHeaders']=module['Name']=='ShooterCoreRuntime'
        if module['Name']=='ShooterCoreRuntime':manifest['Modules'][i]=rewrite(module)
    manifest['ExternalDependenciesFile']=str(output/'ShooterCoreOnly.deps')
    uht_manifest=output/'LyraEditor.ShooterCoreOnly.uhtmanifest'
    uht_manifest.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    sources=[digest(old_manifest)]
    derived=[digest(uht_manifest)]
    for file in old_gen.rglob('*'):
        if file.is_file():
            target=new_gen/file.relative_to(old_gen);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(text_replace(file.read_text(encoding='utf-8-sig')),encoding='utf-8',newline='\n')
    names=['Module.ShooterCoreRuntime.cpp','PerModuleInline.gen.cpp','Definitions.ShooterCoreRuntime.h',
           'ShooterCoreRuntime.Shared.rsp','Module.ShooterCoreRuntime.cpp.obj.rsp',
           'UnrealEditor-ShooterCoreRuntime.lib.rsp','UnrealEditor-ShooterCoreRuntime.dll.rsp']
    for name in names:
        original=old_intermediate/name;target=new_intermediate/name
        sources.append(digest(original))
        target.write_text(text_replace(original.read_text(encoding='utf-8-sig')),encoding='utf-8',newline='\n')
        derived.append(digest(target))
    old_binary=old_root/'Binaries/Win64/UnrealEditor-ShooterCoreRuntime.dll'
    new_binary=new_root/'Binaries/Win64/UnrealEditor-ShooterCoreRuntime.dll'
    previous=output/'PreviousBinaries';previous.mkdir()
    shutil.copy2(new_binary,previous/new_binary.name)
    protected=[digest(old_binary),digest(previous/new_binary.name)]
    for file in (old_root/'Source').rglob('*'):
        if file.is_file():protected.append(digest(file))
    for file in (new_root/'Source').rglob('*'):
        if file.is_file():derived.append(digest(file))
    engine=Path('F:/UnrealEngine')
    for relative in ['Engine/Build/Build.version','Engine/Binaries/Win64/UnrealEditor.exe',
        'Engine/Binaries/Win64/UnrealEditor.modules','Engine/Binaries/Win64/UnrealEditor-Core.dll',
        'Engine/Binaries/Win64/UnrealEditor-Engine.dll']:
        protected.append(digest(engine/relative))
    for plugin in ('UnrealEnginePython','UEPLyraBridge'):
        for project in (baseline,stage):
            protected.append(digest(project/f'Plugins/{plugin}/Binaries/Win64/UnrealEditor-{plugin}.dll'))
    steps=[dict(name='compile',tool='cl.exe',rsp=str(new_intermediate/'Module.ShooterCoreRuntime.cpp.obj.rsp')),
           dict(name='import-library',tool='link.exe',rsp=str(new_intermediate/'UnrealEditor-ShooterCoreRuntime.lib.rsp')),
           dict(name='link-dll',tool='link.exe',rsp=str(new_intermediate/'UnrealEditor-ShooterCoreRuntime.dll.rsp'))]
    report=dict(schema_version=1,status='planned',module='ShooterCoreRuntime',stage=str(stage),baseline=str(baseline),
        uht_manifest=str(uht_manifest),uht_export_modules=[m['Name'] for m in manifest['Modules'] if m['SaveExportedHeaders']],
        generated_directory=str(new_gen),binary=str(new_binary),steps=steps,sources=sources,derived=derived,protected=protected,
        native_pch_and_dependency_objects_reused=True,engine_compile_planned=False,runtime_acceptance=False)
    (output/'plan.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(status='planned',plan=str(output/'plan.json'),steps=len(steps),uht_export_modules=report['uht_export_modules'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',required=True);parser.add_argument('--baseline',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.stage,args.baseline,args.output)))
