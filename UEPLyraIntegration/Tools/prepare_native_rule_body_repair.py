"""Resume a failed unit-3 compile without repeating successful UHT or units 1/2."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned failed build and fresh repair required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));plan=json.loads((previous/'Plan/plan.json').read_text());stage=Path(plan['stage'])
    if not all(summary['processes'][name]['exit_code']==0 for name in ('uht','compile-1','compile-2')):raise ValueError('Successful UHT and first two units required')
    source=REPO/'Demos/UEPLyraIntegration/NativePolicyAdapters/UEPNativeRulePolicies.cpp';target=stage/'Source/LyraGame/UEPPolicy/UEPNativeRulePolicies.cpp';changed={source,target}
    for row in summary['generated']+plan['sources']+plan['derived']+plan['protected']:
        if Path(row['path']) not in changed and digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Unrelated repair input changed: '+row['path'])
    recorded=next(row for row in plan['derived'] if Path(row['path'])==target)
    if digest(target)['sha256']!=recorded['sha256']:raise ValueError('Staged fixture changed before repair')
    output.mkdir(parents=True);(output/'PreviousSources').mkdir();shutil.copy2(target,output/'PreviousSources'/target.name);shutil.copy2(source,target)
    plan['sources']=[digest(Path(row['path'])) if Path(row['path']) in changed else row for row in plan['sources']]
    plan['derived']=[digest(Path(row['path'])) if Path(row['path']) in changed else row for row in plan['derived']]
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    plan['protected']+=summary['generated']+[digest(inter/f'Module.LyraGame.{i}.cpp.obj') for i in (1,2)]
    plan['steps']=[step for step in plan['steps'] if step['name'] not in ('compile-1','compile-2')]
    plan.update(previous_build=str(previous),compiled_unity_units=['Module.LyraGame.3.cpp','Module.TopDownArenaRuntime.cpp'],reused_unity_units=['Module.LyraGame.1.cpp','Module.LyraGame.2.cpp'],uht_export_modules=[],header_generation_executed=False)
    (output/'Plan').mkdir();(output/'Plan/plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n')
    (output/'reused-generated.json').write_text(json.dumps(summary['generated'],indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output),indent=2))
