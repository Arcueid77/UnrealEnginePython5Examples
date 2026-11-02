"""Repair a fixture body without rerunning successful UHT/other unity units."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned prior fixture build and fresh repair output required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));plan=json.loads((previous/'Plan/plan.json').read_text());stage=Path(plan['stage'])
    if summary['processes']['uht']['exit_code']!=0 or summary['processes']['compile-1']['exit_code']!=0:raise ValueError('Successful UHT and registration unit required')
    source=REPO/'Demos/UEPLyraIntegration/NativeFixtures/UEPNativeStatsFixture.cpp';target=stage/'Source/LyraGame/UEPValidation/UEPNativeStatsFixture.cpp'
    for row in summary['generated']+plan['sources']+plan['derived']+plan['protected']:
        if Path(row['path'])==source:continue
        if digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Prior frozen fixture input changed: '+row['path'])
    base=json.loads((Path(plan['previous_build'])/'summary.json').read_text(encoding='utf-8-sig'))
    for row in base['products']:
        if digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('DLL changed after compile-only failure')
    output.mkdir(parents=True);(output/'PreviousBinaries').mkdir();shutil.copy2(plan['binary'],output/'PreviousBinaries'/Path(plan['binary']).name);shutil.copytree(previous/'SourcePatch',output/'SourcePatch');shutil.copy2(target,output/'PreviousFixture.cpp');shutil.copy2(source,target)
    for key in ('sources','derived'):plan[key]=[digest(Path(r['path'])) if Path(r['path']) in (source,target) else r for r in plan[key]]
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    plan['protected']+=summary['generated']+[digest(inter/('Module.LyraGame.'+str(i)+'.cpp.obj')) for i in (1,3)]
    plan['steps']=[s for s in plan['steps'] if s['tool']!='cl.exe' or 'Module.LyraGame.2.cpp.obj.rsp' in s['rsp']]
    plan.update(previous_build=str(previous),compiled_unity_units=['Module.LyraGame.2.cpp'],reused_unity_units=['Module.LyraGame.1.cpp','Module.LyraGame.3.cpp'],uht_export_modules=[],header_generation_executed=False,fixture_body_only_repair=True)
    (output/'Plan').mkdir();(output/'Plan/plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],uht_export_modules=[])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output),indent=2))
