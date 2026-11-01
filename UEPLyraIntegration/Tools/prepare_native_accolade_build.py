"""One ShooterCore unity rebuild, using the current accepted LyraGame ABI."""
import argparse
import json
from pathlib import Path
from prepare_native_message_build import REPO,digest,prepare as prepare_sc


def prepare(stage,baseline,output):
    stage,baseline,output=(Path(p).resolve() for p in (stage,baseline,output))
    prepare_sc(stage,baseline,output);plan_path=output/'plan.json';plan=json.loads(plan_path.read_text());manifest_path=Path(plan['uht_manifest']);manifest=json.loads(manifest_path.read_text())
    mapping=[(baseline/'Source/LyraGame',stage/'Source/LyraGame'),
        (baseline/'Intermediate/Build/Win64/UnrealEditor/Inc/LyraGame',stage/'Intermediate/Build/Win64/UnrealEditor/Inc/LyraGame'),
        (baseline/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame',stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame')]
    def replace(text):
        for old,new in mapping:
            for a,b in ((str(old),str(new)),(old.as_posix(),new.as_posix())):text=text.replace(a,b)
        return text
    def rewrite(value):
        if isinstance(value,str):return replace(value)
        if isinstance(value,list):return [rewrite(v) for v in value]
        if isinstance(value,dict):return {k:rewrite(v) for k,v in value.items()}
        return value
    manifest['Modules']=[rewrite(m) if m['Name']=='LyraGame' else m for m in manifest['Modules']]
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    inter=stage/'Plugins/GameFeatures/ShooterCore/Intermediate/Build/Win64/x64/UnrealEditor/Development/ShooterCoreRuntime'
    for rsp in inter.glob('*.rsp'):rsp.write_text(replace(rsp.read_text(encoding='utf-8-sig')),encoding='utf-8',newline='\n')
    plan['derived']=[digest(Path(r['path'])) for r in plan['derived']]
    lg=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    for path in [stage/'Binaries/Win64/UnrealEditor-LyraGame.dll',lg/'UnrealEditor-LyraGame.lib',*[lg/('Module.LyraGame.'+str(i)+'.cpp.obj') for i in (1,2,3)]]:plan['protected'].append(digest(path))
    plan.update(batch='CPP07',compiled_unity_units=['Module.ShooterCoreRuntime.cpp'],reused_lyra_game_units=[1,2,3],current_lyra_game_headers_and_import_library_used=True)
    plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],reused_lyra_game_units=plan['reused_lyra_game_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--baseline',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.stage,a.baseline,a.output)))
