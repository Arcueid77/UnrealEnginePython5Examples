"""Add the new standalone USTRUCT registration to its item-cost translation unit."""
import argparse
import json
from pathlib import Path
import shutil
from prepare_native_message_build import REPO,digest
import native_cost_patches as native


def prepare(previous,output):
    previous,output=(Path(p).resolve() for p in (previous,output))
    if not previous.is_relative_to(REPO/'.build') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned prior link failure and fresh output required')
    summary=json.loads((previous/'summary.json').read_text(encoding='utf-8-sig'));plan=json.loads((previous/'Plan/plan.json').read_text());stage=Path(plan['stage'])
    if any(summary['processes']['compile-'+str(i)]['exit_code']!=0 for i in (2,3)) or 'link-dll' not in summary['error']:raise ValueError('Successful dependent units and isolated link failure required')
    for row in summary['generated']+plan['sources']+plan['derived']+plan['protected']:
        if digest(Path(row['path']))['sha256']!=row['sha256']:raise ValueError('Prior cost input changed: '+row['path'])
    changes=[r for r in native.sources() if (stage/r['relative']).read_text(encoding='utf-8-sig')!=r['after']]
    if len(changes)!=1 or not changes[0]['relative'].endswith('LyraAbilityCost_ItemTagStack.cpp'):raise ValueError('Only standalone generated-registration include may change')
    row=changes[0];target=stage/row['relative'];before=target.read_text(encoding='utf-8-sig')
    if before.replace('#include UE_INLINE_GENERATED_CPP_BY_NAME(LyraAbilityCost_ItemTagStack)','#include UE_INLINE_GENERATED_CPP_BY_NAME(LyraAbilityCost_ItemTagStack)\n#include UE_INLINE_GENERATED_CPP_BY_NAME(LyraTagStackCostPolicy)')!=row['after']:raise ValueError('Cost semantics changed during registration repair')
    output.mkdir(parents=True);shutil.copy2(target,output/'PreviousItemCost.cpp');target.write_text(row['after'],encoding='utf-8',newline='\n');native.apply(stage,output/'SourcePatch')
    inter=stage/'Intermediate/Build/Win64/x64/UnrealEditor/Development/LyraGame'
    plan['derived']=[digest(target) if Path(r['path'])==target else r for r in plan['derived']]
    plan['protected']=[r for r in plan['protected'] if Path(r['path'])!=inter/'Module.LyraGame.1.cpp.obj']+summary['generated']+[digest(inter/f'Module.LyraGame.{i}.cpp.obj') for i in (2,3)]
    rsp=str(inter/'Module.LyraGame.1.cpp.obj.rsp');plan['steps']=[dict(name='compile-1',tool='cl.exe',rsp=rsp)]+[s for s in plan['steps'] if s['tool']!='cl.exe']
    plan.update(previous_build=str(previous),compiled_unity_units=['Module.LyraGame.1.cpp'],reused_unity_units=['Module.LyraGame.2.cpp','Module.LyraGame.3.cpp'],uht_export_modules=[],header_generation_executed=False,fixture_body_only_repair=False,standalone_struct_registration_include_repair=True)
    (output/'Plan').mkdir();(output/'Plan/plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='planned',compiled_unity_units=plan['compiled_unity_units'],uht_export_modules=[])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(prepare(a.previous,a.output),indent=2))
