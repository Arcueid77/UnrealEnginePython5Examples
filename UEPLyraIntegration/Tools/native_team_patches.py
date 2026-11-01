"""Expose two team-policy events while retaining native assignment and fallback."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]
REFERENCE=Path('F:/LyraStarterGame')
BASE='Source/LyraGame/Teams/LyraTeamCreationComponent'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def sources():
    inventory=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text())
    expected={r['path']:r['sha256'] for field in ('runtime_cpp_files','supporting_declarations') for r in inventory[field]}
    rows=[]
    for suffix in ('.h','.cpp'):
        relative=BASE+suffix;original=REFERENCE/relative
        if sha(original)!=expected[relative]:raise ValueError('Original team source differs from census: '+relative)
        before=original.read_text(encoding='utf-8-sig');after=before
        if suffix=='.h':
            anchor='#if WITH_SERVER_CODE\nprotected:\n'
            declaration='''protected:
	// Policy seams; native initialization, authority and team notifications remain native.
	UFUNCTION(BlueprintNativeEvent, Category="UEP|NativeGameplay")
	void UEPChooseTeamForPlayer(ALyraPlayerState* PS);

	UFUNCTION(BlueprintNativeEvent, Category="UEP|NativeGameplay")
	int32 UEPGetLeastPopulatedTeamID() const;

	// Keep the original native setter and its notifications behind reflection.
	UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="UEP|NativeGameplay")
	void UEPSetPlayerTeam(ALyraPlayerState* PS, int32 TeamId);

'''
            if after.count(anchor)!=1:raise ValueError('Team header anchor changed')
            after=after.replace(anchor,declaration+anchor)
        else:
            start=after.index('void ULyraTeamCreationComponent::ServerChooseTeamForPlayer(ALyraPlayerState* PS)\n{')
            end=after.index('\nvoid ULyraTeamCreationComponent::OnPlayerInitialized',start)
            original_body=after[start:end]
            native_body=original_body.replace('ServerChooseTeamForPlayer(', 'UEPChooseTeamForPlayer_Implementation(',1)
            native_body=native_body.replace('IntegerToGenericTeamId(GetLeastPopulatedTeamID())','IntegerToGenericTeamId(UEPGetLeastPopulatedTeamID())')
            native_body=native_body.replace('\n{\n','\n{\n#if WITH_SERVER_CODE\n',1)
            native_body=native_body.rstrip();native_body=native_body[:-1]+'#endif\n}\n'
            population='''
int32 ULyraTeamCreationComponent::UEPGetLeastPopulatedTeamID_Implementation() const
{
#if WITH_SERVER_CODE
	return GetLeastPopulatedTeamID();
#else
	return INDEX_NONE;
#endif
}

void ULyraTeamCreationComponent::UEPSetPlayerTeam(ALyraPlayerState* PS, int32 TeamId)
{
	PS->SetGenericTeamId(IntegerToGenericTeamId(TeamId));
}

'''
            after=after[:start]+'''void ULyraTeamCreationComponent::ServerChooseTeamForPlayer(ALyraPlayerState* PS)
{
	UEPChooseTeamForPlayer(PS);
}
'''+after[end:]
            anchor='#if WITH_SERVER_CODE\n\nvoid ULyraTeamCreationComponent::ServerCreateTeams()'
            if after.count(anchor)!=1:raise ValueError('Team native definition anchor changed')
            after=after.replace(anchor,native_body+population+anchor)
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(original)))
    return rows


def patch_text():
    return ''.join(''.join(difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'],tofile='b/'+r['relative'])) for r in sources())


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve();owned=REPO/'.build'
    if not stage.is_relative_to(owned) or not output.is_relative_to(owned) or output.exists():raise ValueError('Owned stage and fresh patch evidence required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if marker.get('purpose')!='approved-native-gameplay-migration' or not marker.get('independent_file_copies'):raise ValueError('Independent native migration stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP02-team-rules.patch'
    if artifact.read_text(encoding='utf-8')!=patch_text():raise ValueError('Versioned team patch differs')
    rows=sources()
    for row in rows:
        previous_cpp02={BASE+'.h':'FE919D374446A7F42AC979E577517D265ABC291C7287EEBD7A624C7ACB653A7E',
                        BASE+'.cpp':'18C03414F5F73EF1DB05509F601F27E430C3DEAB0B586E128F2BF852D45FB3CB'}
        target=stage/row['relative']
        if target.read_text(encoding='utf-8-sig') not in (row['before'],row['after']) and sha(target)!=previous_cpp02[row['relative']]:raise ValueError('Unrelated team source edit')
    output.mkdir(parents=True);records=[]
    for row in rows:
        target=stage/row['relative'];archive=output/'PreviousSources'/row['relative'];archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(target.read_bytes())
        target.write_text(row['after'],encoding='utf-8',newline='\n')
        records.append(dict(path=str(target),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],previous_source=str(archive),previous_sha256=sha(archive),patched_sha256=sha(target)))
    report=dict(schema_version=1,status='patched_requires_native_build',batch='CPP02',event_entrypoints=2,sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP02-team-rules.patch'
        if target.exists():raise ValueError('Team patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output),indent=2))
