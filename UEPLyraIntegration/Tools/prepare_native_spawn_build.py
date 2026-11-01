"""Two-module policy build: affected LyraGame units then ShooterCoreRuntime."""
import argparse
import json
from pathlib import Path
from prepare_native_message_build import REPO,digest,prepare as prepare_sc
from prepare_native_spawn_lg_build import prepare as prepare_lg


def prepare(stage,baseline,output):
    stage,baseline,output=(Path(p).resolve() for p in (stage,baseline,output));owned=REPO/'.build'
    if any(not p.is_relative_to(owned) for p in (stage,baseline,output)) or output.exists():raise ValueError('Owned stages and fresh combined spawning plan required')
    output.mkdir(parents=True);prepare_lg(stage,baseline,output/'LyraGame');prepare_sc(stage,baseline,output/'ShooterCoreRuntime')
    lg=json.loads((output/'LyraGame/plan.json').read_text());sc=json.loads((output/'ShooterCoreRuntime/plan.json').read_text())
    lg_manifest=json.loads(Path(lg['uht_manifest']).read_text());sc_manifest=json.loads(Path(sc['uht_manifest']).read_text())
    lg_module=next(m for m in lg_manifest['Modules'] if m['Name']=='LyraGame')
    sc_module=next(m for m in sc_manifest['Modules'] if m['Name']=='ShooterCoreRuntime')
    manifest=lg_manifest
    manifest['Modules']=[lg_module if m['Name']=='LyraGame' else sc_module if m['Name']=='ShooterCoreRuntime' else m for m in manifest['Modules']]
    for module in manifest['Modules']:module['SaveExportedHeaders']=module['Name'] in ('LyraGame','ShooterCoreRuntime')
    manifest['ExternalDependenciesFile']=str(output/'SpawningModules.deps')
    manifest_path=output/'LyraEditor.SpawningOnly.uhtmanifest';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    # The derived ShooterCore module must compile against the new base header
    # and import library, rather than the accepted old dependency locations.
    mapping=[(baseline/'Source/LyraGame',stage/'Source/LyraGame'),
        (baseline/'Intermediate/Build/Win64/UnrealEditor/Inc/LyraGame',stage/'Intermediate/Build/Win64/UnrealEditor/Inc/LyraGame'),
        (baseline/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame',stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame')]
    inter=stage/'Plugins/GameFeatures/ShooterCore/Intermediate/Build/Win64/x64/UnrealEditor/Development/ShooterCoreRuntime'
    for rsp in inter.glob('*.rsp'):
        text=rsp.read_text(encoding='utf-8-sig')
        for old,new in mapping:
            for a,b in ((str(old),str(new)),(old.as_posix(),new.as_posix())):text=text.replace(a,b)
        rsp.write_text(text,encoding='utf-8',newline='\n')
    derived=[digest(Path(r['path'])) for p in (lg,sc) for r in p['derived']];derived.append(digest(manifest_path))
    steps=[]
    for prefix,plan in (('LG',lg),('SC',sc)):
        for step in plan['steps']:steps.append(dict(step,name=prefix+'-'+step['name']))
    report=dict(schema_version=1,status='planned',stage=str(stage),baseline=str(baseline),modules=['LyraGame','ShooterCoreRuntime'],
        uht_manifest=str(manifest_path),uht_export_modules=['LyraGame','ShooterCoreRuntime'],
        generated_directories=[lg['generated_directory'],sc['generated_directory']],binaries=[lg['binary'],sc['binary']],steps=steps,
        sources=lg['sources']+sc['sources'],derived=derived,protected=lg['protected']+sc['protected'],
        compiled_unity_units={'LyraGame':lg['compiled_unity_units'],'ShooterCoreRuntime':['Module.ShooterCoreRuntime.cpp']},
        reused_unity_units=lg['reused_unity_units'],new_base_header_and_import_library_used=True,engine_compile_planned=False,runtime_acceptance=False)
    # ShooterCore is rebuilt intentionally in this batch.
    report['protected']=[r for r in report['protected'] if Path(r['path'])!=Path(sc['binary'])]
    (output/'plan.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='planned',uht_export_modules=report['uht_export_modules'],compiled_unity_units=report['compiled_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--baseline',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.stage,a.baseline,a.output)))
