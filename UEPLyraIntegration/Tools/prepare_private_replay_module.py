"""Compile the optional current-engine memory streamer into the private stage."""
import argparse
import json
import shutil
from pathlib import Path
from prepare_native_message_build import REPO,digest


def prepare(stage,output,reuse=None):
    stage,output=(Path(p).resolve() for p in (stage,output))
    if not stage.is_relative_to(REPO/'.build/LyraValidation/CppGameplayExtended') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned private stage/fresh replay dependency output required')
    output.mkdir(parents=True);engine=Path('F:/UnrealEngine');module=engine/'Engine/Source/Runtime/NetworkReplayStreaming/InMemoryNetworkReplayStreaming';old=stage/'Plugins/GameFeatures/TopDownArena/Intermediate/Build/Win64/x64/UnrealEditor/Development/TopDownArenaRuntime';name='InMemoryNetworkReplayStreaming';inputs=[];derived=[]
    for suffix in ('.cpp','.h'):
        p=module/('Private' if suffix=='.cpp' else 'Public')/(name+suffix);inputs.append(digest(p))
    cpp=output/('Module.'+name+'.cpp');cpp.write_text('#include "'+(module/'Private'/(name+'.cpp')).as_posix()+'"\n',encoding='utf-8',newline='\n');derived.append(digest(cpp))
    names=('Definitions.TopDownArenaRuntime.h','TopDownArenaRuntime.Shared.rsp','Module.TopDownArenaRuntime.cpp.obj.rsp','UnrealEditor-TopDownArenaRuntime.lib.rsp','UnrealEditor-TopDownArenaRuntime.dll.rsp')
    binary=stage/'Binaries/Win64'/('UnrealEditor-'+name+'.dll')
    if binary.exists():raise ValueError('Private replay module already exists')
    for filename in names:
        p=old/filename;inputs.append(digest(p));text=p.read_text(encoding='utf-8-sig')
        for a,b in ((str(old),str(output)),(old.as_posix(),output.as_posix()),((stage/'Plugins/GameFeatures/TopDownArena/Binaries/Win64').as_posix(),binary.parent.as_posix())):text=text.replace(a,b)
        text=text.replace('TopDownArenaRuntime',name)
        if filename.endswith('.Shared.rsp'):
            text+='\n'+''.join('/I"'+p.as_posix()+'"\n' for p in (module/'Public',engine/'Engine/Source/Runtime/NetworkReplayStreaming/NetworkReplayStreaming/Public',engine/'Engine/Source/Runtime/Json/Public'))
        if filename.endswith('.dll.rsp'):
            text+='\n'+''.join('"'+(engine/('Engine/Intermediate/Build/Win64/x64/UnrealEditor/Development/'+dependency+'/UnrealEditor-'+dependency+'.lib')).as_posix()+'"\n' for dependency in ('NetworkReplayStreaming','Json'))
        target=output/filename.replace('TopDownArenaRuntime',name);target.write_text(text,encoding='utf-8',newline='\n');derived.append(digest(target))
    protected=[digest(engine/'Engine/Binaries/Win64/UnrealEditor.modules'),digest(engine/'Engine/Binaries/Win64/UnrealEditor-InMemoryNetworkReplayStreaming.dll'),digest(engine/'Engine/Build/Build.version')]
    steps=[dict(name='compile',tool='cl.exe',rsp=str(output/('Module.'+name+'.cpp.obj.rsp'))),dict(name='import-library',tool='link.exe',rsp=str(output/('UnrealEditor-'+name+'.lib.rsp'))),dict(name='link-dll',tool='link.exe',rsp=str(output/('UnrealEditor-'+name+'.dll.rsp')))]
    if reuse:
        reuse=Path(reuse).resolve()
        if not reuse.is_relative_to(REPO/'.build'):raise ValueError('Owned compile reuse required')
        prior=json.loads((reuse/'summary.json').read_text(encoding='utf-8-sig'))
        if prior['processes']['compile']['exit_code']!=0:raise ValueError('Successful replay compile required')
        original=reuse/'Plan'/('Module.'+name+'.cpp.obj');target=output/original.name;shutil.copy2(original,target);inputs.append(digest(original));derived.append(digest(target));steps=steps[1:]
    result=dict(status='planned',stage=str(stage),binary=str(binary),manifest=str(stage/'Binaries/Win64/UnrealEditor.modules'),sources=inputs,derived=derived,protected=protected,steps=steps,engine_files_modified=False,engine_full_compile_executed=False)
    (output/'plan.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',private_module=name,source_cpp_units=1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--output',required=True);p.add_argument('--reuse-from');a=p.parse_args();print(json.dumps(prepare(a.stage,a.output,a.reuse_from),indent=2))
