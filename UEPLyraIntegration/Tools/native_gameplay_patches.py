"""Source-bound native event entrypoints; business bodies remain the native baseline."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json

REPO=Path(__file__).resolve().parents[3]
REFERENCE=Path('F:/LyraStarterGame')
MODULE='Plugins/GameFeatures/ShooterCore/Source/ShooterCoreRuntime'
PROCESSORS={
    'ElimStreakProcessor':('UElimStreakProcessor',('Elimination',)),
    'ElimChainProcessor':('UElimChainProcessor',('Elimination',)),
    'AssistProcessor':('UAssistProcessor',('Damage','Elimination')),
}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def cpp01_sources():
    inventory=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text(encoding='utf-8'))
    expected={r['path']:r['sha256'] for r in inventory['runtime_cpp_files']+inventory['supporting_declarations']}
    rows=[]
    for name,(cls,events) in PROCESSORS.items():
        for folder,extension in (('Public','.h'),('Private','.cpp')):
            rel=f'{MODULE}/{folder}/MessageProcessors/{name}{extension}'
            original=REFERENCE/rel
            if sha(original)!=expected[rel]:raise ValueError('Reviewed reference source changed: '+rel)
            before=original.read_text(encoding='utf-8-sig')
            after=before
            if extension=='.h':
                anchor='private:\n\tvoid On'+events[0]+'Message(FGameplayTag Channel, const FLyraVerbMessage& Payload);'
                declarations='protected:\n'+''.join(
                    '\tUFUNCTION(BlueprintNativeEvent, Category="UEP|NativeGameplay")\n'
                    '\tvoid UEPHandle'+event+'(FGameplayTag Channel, const FLyraVerbMessage& Payload);\n\n'
                    for event in events)
                if after.count(anchor)!=1:raise ValueError('One private callback declaration required: '+rel)
                after=after.replace(anchor,declarations+anchor)
                generated='#include "'+name+'.generated.h"'
                after=after.replace(generated,'#include "Messages/LyraVerbMessage.h"\n\n'+generated)
            else:
                for event in events:
                    signature=f'void {cls}::On{event}Message(FGameplayTag Channel, const FLyraVerbMessage& Payload)\n'
                    if after.count(signature)!=1:raise ValueError('One original callback definition required: '+rel)
                    after=after.replace(signature,
                        signature+'{\n\tUEPHandle'+event+'(Channel, Payload);\n}\n\n'+
                        f'void {cls}::UEPHandle{event}_Implementation(FGameplayTag Channel, const FLyraVerbMessage& Payload)\n')
            rows.append(dict(relative=rel,before=before,after=after,original_sha256=sha(original)))
    return rows


def patch_text():
    return ''.join(''.join(difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),
        fromfile='a/'+r['relative'],tofile='b/'+r['relative'])) for r in cpp01_sources())


def apply(stage,output):
    stage,output=Path(stage).resolve(),Path(output).resolve()
    owned=(REPO/'.build').resolve()
    if not stage.is_relative_to(owned) or not output.is_relative_to(owned) or output.exists():
        raise ValueError('Marked owned stage and fresh output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if marker.get('purpose')!='approved-native-gameplay-migration' or not marker.get('independent_file_copies'):
        raise ValueError('An independent native-gameplay stage is required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP01-message-rules.patch'
    if artifact.read_text(encoding='utf-8')!=patch_text():raise ValueError('Versioned patch differs from reviewed transformation')
    rows=cpp01_sources()
    for row in rows:
        current=(stage/row['relative']).read_text(encoding='utf-8-sig')
        if current not in (row['before'],row['after']):raise ValueError('Unrelated stage edit: '+row['relative'])
    output.mkdir(parents=True)
    records=[]
    for row in rows:
        target=stage/row['relative'];archive=output/'PreviousSources'/row['relative']
        archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(target.read_bytes())
        target.write_text(row['after'],encoding='utf-8',newline='\n')
        records.append(dict(path=str(target),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],
            previous_source=str(archive),previous_sha256=sha(archive),patched_sha256=sha(target)))
    report=dict(schema_version=1,status='patched_requires_native_build',batch='CPP01',sources=records,
        patch=dict(path=str(artifact),sha256=sha(artifact)),business_bodies_preserved=True,
        event_entrypoints=4,runtime_acceptance=False,official_reference_unchanged=all(sha(r['original'])==r['original_sha256'] for r in records))
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage');parser.add_argument('--output');parser.add_argument('--write-patch',action='store_true')
    args=parser.parse_args()
    if args.write_patch:
        destination=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP01-message-rules.patch'
        if destination.exists():raise ValueError('Patch already exists; review changes explicitly')
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(patch_text(),encoding='utf-8',newline='\n')
        print(str(destination))
    else:
        result=apply(args.stage,args.output)
        print(json.dumps({k:result[k] for k in ('status','batch','event_entrypoints','official_reference_unchanged')}))
