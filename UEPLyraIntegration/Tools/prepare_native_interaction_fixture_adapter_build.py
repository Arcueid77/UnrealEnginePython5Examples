"""Add a reflected stage-only input adapter; regenerate/rebuild its affected units."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned successful build and fresh adapter output required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));old=json.loads((previous/'Plan/plan.json').read_text());stage=Path(old['stage'])
    if summary['status']!='built_requires_native_acceptance' or summary['error'] is not None:raise ValueError('Successful native interaction witness build required')
    sources=[REPO/'Demos/UEPLyraIntegration/NativeFixtures'/('UEPNativeInteractionFixture'+suffix) for suffix in ('.h','.cpp')]
    for row in summary['products']+summary['generated']+old['sources']+old['derived']+old['protected']:
        if Path(row['path']) in sources:continue
        if digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Previous frozen input/product changed: '+row['path'])
    original=Path(old['previous_build']);plan=json.loads((original/'Plan/plan.json').read_text());output.mkdir(parents=True)
    (output/'PreviousBinaries').mkdir();shutil.copy2(plan['binary'],output/'PreviousBinaries'/Path(plan['binary']).name);shutil.copytree(previous/'SourcePatch',output/'SourcePatch')
    targets=[stage/'Source/LyraGame/UEPValidation'/s.name for s in sources]
    for source,target in zip(sources,targets):shutil.copy2(target,output/('Previous'+source.suffix));shutil.copy2(source,target)
    for key in ('sources','derived'):plan[key]=[digest(Path(r['path'])) if Path(r['path']) in sources+targets else r for r in plan[key]]
    plan.update(previous_build=str(previous),fixture_native_input_adapter_added=True,header_generation_executed=True)
    (output/'Plan').mkdir();(output/'Plan/plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output)))
