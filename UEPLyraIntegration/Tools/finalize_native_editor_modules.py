"""Write stage-local loader manifests for freshly compiled project modules."""
import argparse
import hashlib
import json
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def require(value,message):
    if not value:raise ValueError(message)

def finalize(stage,engine,result):
    stage,engine,result=stage.resolve(),engine.resolve(),result.resolve()
    require(stage.is_relative_to(REPO/'.build') and result.is_relative_to(REPO/'.build') and not result.exists(),'owned stage and fresh manifest report required')
    engine_manifest=engine/'Engine/Binaries/Win64/UnrealEditor.modules';engine_hash=sha(engine_manifest)
    build_id=json.loads(engine_manifest.read_text(encoding='utf-8-sig'))['BuildId']
    descriptors=[stage/'LyraStarterGame.uproject']+sorted((stage/'Plugins').rglob('*.uplugin'));groups={};products=[]
    project=json.loads(descriptors[0].read_text(encoding='utf-8-sig'));disabled={row['Name'] for row in project['Plugins'] if not row.get('Enabled',True)}
    for descriptor in descriptors:
        if descriptor.suffix=='.uplugin' and descriptor.stem in disabled:continue
        data=json.loads(descriptor.read_text(encoding='utf-8-sig'))
        for module in data.get('Modules',[]):
            name=module['Name'];binary=descriptor.parent/'Binaries/Win64'/('UnrealEditor-'+name+'.dll')
            require(binary.is_file(),'fresh project module missing: '+name)
            groups.setdefault(binary.parent,{})[name]=binary.name
            products.append(dict(path=str(binary),sha256=sha(binary)))
    manifests=[]
    for directory,modules in groups.items():
        path=directory/'UnrealEditor.modules'
        if path.exists():
            previous=json.loads(path.read_text(encoding='utf-8-sig'))
            require(previous['BuildId']==build_id and set(previous['Modules'])<=set(modules),'unexpected private module manifest contents')
        path.write_text(json.dumps(dict(BuildId=build_id,Modules=modules),indent=2)+'\n',encoding='utf-8',newline='\n')
        manifests.append(dict(path=str(path),sha256=sha(path)))
    require(sha(engine_manifest)==engine_hash,'protected Engine manifest changed')
    report=dict(status='passed',scope='fresh-project-module-loader-manifests-only',engine_build_id=build_id,
        engine_manifest_unchanged=True,old_project_binaries_reused=False,project_modules=len(products),products=products,manifests=manifests)
    result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    return {k:v for k,v in report.items() if k not in ('products','manifests')}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('stage','engine','result'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(finalize(a.stage,a.engine,a.result)))
