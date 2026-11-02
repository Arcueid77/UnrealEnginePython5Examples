"""Repair two private lifecycle bodies, reusing successful UHT and units 2/3."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest
import native_lifecycle_patches as native


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned prior lifecycle build and fresh output required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));plan=json.loads((previous/'Plan/plan.json').read_text());stage=Path(plan['stage'])
    if summary['status']!='built_requires_native_acceptance':raise ValueError('Successful previous build required')
    for r in summary['products']+summary['generated']+plan['sources']+plan['derived']+plan['protected']:
        if digest(Path(r['path']))['sha256']!=r['sha256']:raise ValueError('Frozen lifecycle input changed: '+r['path'])
    changed=[r for r in native.sources() if (stage/r['relative']).read_text(encoding='utf-8-sig')!=r['after']]
    if {Path(r['relative']).name for r in changed}!={'LyraGameplayAbility_Jump.cpp','LyraGameplayAbility_Death.cpp'}:raise ValueError('Only Jump/Death private teardown guards may change')
    output.mkdir(parents=True);(output/'PreviousSources').mkdir();(output/'PreviousBinaries').mkdir();shutil.copy2(plan['binary'],output/'PreviousBinaries'/Path(plan['binary']).name)
    for r in changed:
        p=stage/r['relative'];shutil.copy2(p,output/'PreviousSources'/p.name);p.write_text(r['after'],encoding='utf-8',newline='\n')
    native.apply(stage,output/'SourcePatch');paths={stage/r['relative'] for r in changed};plan['derived']=[digest(Path(r['path'])) if Path(r['path']) in paths else r for r in plan['derived']]
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame';plan['protected']=[r for r in plan['protected'] if Path(r['path'])!=inter/'Module.LyraGame.1.cpp.obj']+summary['generated']+[digest(inter/'Module.LyraGame.2.cpp.obj'),digest(output/'PreviousBinaries'/Path(plan['binary']).name)]
    plan['steps']=[dict(name='compile-1',tool='cl.exe',rsp=str(inter/'Module.LyraGame.1.cpp.obj.rsp'))]+[s for s in plan['steps'] if s['tool']!='cl.exe'];plan.update(previous_build=str(previous),compiled_unity_units=['Module.LyraGame.1.cpp'],reused_unity_units=['Module.LyraGame.2.cpp','Module.LyraGame.3.cpp'],uht_export_modules=[],header_generation_executed=False,explicit_teardown_guard=True)
    (output/'Plan').mkdir();(output/'Plan/plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output),indent=2))
