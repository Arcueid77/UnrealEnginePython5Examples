"""Native bot spawn/destruction remain; naming and removal choice gain policy events."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha

BASE='Source/LyraGame/GameModes/LyraBotCreationComponent'


def sources():
    inventory=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text())
    expected={r['path']:r['sha256'] for field in ('runtime_cpp_files','supporting_declarations') for r in inventory[field]};rows=[]
    for suffix in ('.h','.cpp'):
        relative=BASE+suffix;original=REFERENCE/relative
        if sha(original)!=expected[relative]:raise ValueError('Original bot source differs from census')
        before=original.read_text(encoding='utf-8-sig');after=before
        if suffix=='.h':
            anchor='#if WITH_SERVER_CODE\npublic:'
            extra='''protected:
	UFUNCTION(BlueprintNativeEvent, BlueprintAuthorityOnly, Category="UEP|NativeGameplay")
	FString UEPCreateBotName(int32 PlayerIndex);

	UFUNCTION(BlueprintNativeEvent, BlueprintAuthorityOnly, Category="UEP|NativeGameplay")
	int32 UEPSelectBotToRemove(int32 BotCount);

	UFUNCTION(BlueprintPure, Category="UEP|NativeGameplay")
	bool UEPIsEditorBotContext() const;

'''
            if after.count(anchor)!=1:raise ValueError('Bot declaration anchor changed')
            after=after.replace(anchor,extra+anchor)
        else:
            start=after.index('FString ULyraBotCreationComponent::CreateBotName(int32 PlayerIndex)\n{')
            end=after.index('\nvoid ULyraBotCreationComponent::SpawnOneBot()',start)
            body=after[start:end].rstrip().replace('::CreateBotName(', '::UEPCreateBotName_Implementation(',1)
            body=body.replace('\n{\n','\n{\n#if WITH_SERVER_CODE\n',1)
            body=body[:-1]+'#else\n\treturn FString();\n#endif\n}\n'
            after=after[:start]+'''FString ULyraBotCreationComponent::CreateBotName(int32 PlayerIndex)
{
	return UEPCreateBotName(PlayerIndex);
}
'''+after[end:]
            select='''
int32 ULyraBotCreationComponent::UEPSelectBotToRemove_Implementation(int32 BotCount)
{
	return FMath::RandRange(0, BotCount - 1);
}

bool ULyraBotCreationComponent::UEPIsEditorBotContext() const
{
	return GIsEditor;
}

'''
            anchor='#if WITH_SERVER_CODE\n\nvoid ULyraBotCreationComponent::ServerCreateBots_Implementation()'
            if after.count(anchor)!=1:raise ValueError('Bot implementation anchor changed')
            after=after.replace(anchor,body+select+anchor)
            old='const int32 BotToRemoveIndex = FMath::RandRange(0, SpawnedBotList.Num() - 1);'
            if after.count(old)!=1:raise ValueError('Native removal selection changed')
            after=after.replace(old,'const int32 BotToRemoveIndex = UEPSelectBotToRemove(SpawnedBotList.Num());')
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(original)))
    return rows


def patch_text():return ''.join(''.join(difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'],tofile='b/'+r['relative'])) for r in sources())


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve();owned=REPO/'.build'
    if not stage.is_relative_to(owned) or not output.is_relative_to(owned) or output.exists():raise ValueError('Owned stage and fresh bot patch output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if marker.get('purpose')!='approved-native-gameplay-migration' or not marker.get('independent_file_copies'):raise ValueError('Independent native migration stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP03-bot-rules.patch'
    if artifact.read_text(encoding='utf-8')!=patch_text():raise ValueError('Versioned bot patch differs')
    rows=sources()
    for row in rows:
        if (stage/row['relative']).read_text(encoding='utf-8-sig') not in (row['before'],row['after']):raise ValueError('Unrelated bot edit')
    output.mkdir(parents=True);records=[]
    for row in rows:
        target=stage/row['relative'];archive=output/'PreviousSources'/row['relative'];archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(target.read_bytes());target.write_text(row['after'],encoding='utf-8',newline='\n')
        records.append(dict(path=str(target),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],previous_source=str(archive),previous_sha256=sha(archive),patched_sha256=sha(target)))
    report=dict(schema_version=1,status='patched_requires_native_build',batch='CPP03',new_policy_events=2,existing_native_event='ServerCreateBots',sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP03-bot-rules.patch'
        if target.exists():raise ValueError('Bot patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output),indent=2))
