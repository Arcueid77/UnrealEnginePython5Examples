"""Policy seams retain native start caching, PIE preference, occupancy and claims."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha

LG='Source/LyraGame/Player/LyraPlayerSpawningManagerComponent'
SC='Plugins/GameFeatures/ShooterCore/Source/ShooterCoreRuntime/Private/TDM_PlayerSpawningManagmentComponent'


def sources():
    inventory=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text())
    expected={r['path']:r['sha256'] for field in ('runtime_cpp_files','supporting_declarations') for r in inventory[field]};rows=[]
    for base in (LG,SC):
        for suffix in ('.h','.cpp'):
            relative=base+suffix;original=REFERENCE/relative
            if sha(original)!=expected[relative]:raise ValueError('Original spawning source differs from census')
            before=original.read_text(encoding='utf-8-sig');after=before
            if base==LG and suffix=='.h':
                anchor='protected:\n\t// Utility'
                declarations='''protected:
	UFUNCTION(BlueprintNativeEvent, Category="UEP|NativeGameplay")
	UE_API AActor* UEPChooseFromStarts(AController* Player, const TArray<ALyraPlayerStart*>& StarterPoints);

	UFUNCTION(BlueprintCallable, Category="UEP|NativeGameplay")
	AActor* UEPChooseSpecificStart(AController* Player, const TArray<ALyraPlayerStart*>& StarterPoints);

	UFUNCTION(BlueprintPure, Category="UEP|NativeGameplay")
	int32 UEPGetStartOccupancy(ALyraPlayerStart* Start, AController* Player) const;

	UFUNCTION(BlueprintPure, Category="UEP|NativeGameplay")
	bool UEPIsStartClaimed(ALyraPlayerStart* Start) const;

	UFUNCTION(BlueprintCallable, Category="UEP|NativeGameplay")
	bool UEPTryClaimStart(ALyraPlayerStart* Start, AController* Player);

'''
                if after.count(anchor)!=1:raise ValueError('Spawn declaration anchor changed')
                after=after.replace(anchor,declarations+anchor)
            elif base==LG:
                start=after.index('\t\tif (APlayerState* PlayerState = Player->GetPlayerState<APlayerState>())')
                end=after.index('\t\treturn PlayerStart;',start)+len('\t\treturn PlayerStart;')
                body=after[start:end];body='\n'.join(line[1:] if line.startswith('\t') else line for line in body.splitlines())
                after=after[:start]+'\t\treturn UEPChooseFromStarts(Player, StarterPoints);'+after[end:]
                methods='''AActor* ULyraPlayerSpawningManagerComponent::UEPChooseFromStarts_Implementation(AController* Player, const TArray<ALyraPlayerStart*>& CandidatePoints)
{
	TArray<ALyraPlayerStart*> StarterPoints = CandidatePoints;
'''+body+'''
}

AActor* ULyraPlayerSpawningManagerComponent::UEPChooseSpecificStart(AController* Player, const TArray<ALyraPlayerStart*>& StarterPoints)
{
	TArray<ALyraPlayerStart*> MutableStarts = StarterPoints;
	return OnChoosePlayerStart(Player, MutableStarts);
}

int32 ULyraPlayerSpawningManagerComponent::UEPGetStartOccupancy(ALyraPlayerStart* Start, AController* Player) const
{
	return Start ? static_cast<int32>(Start->GetLocationOccupancy(Player)) : static_cast<int32>(ELyraPlayerStartLocationOccupancy::Full);
}

bool ULyraPlayerSpawningManagerComponent::UEPIsStartClaimed(ALyraPlayerStart* Start) const
{
	return Start && Start->IsClaimed();
}

bool ULyraPlayerSpawningManagerComponent::UEPTryClaimStart(ALyraPlayerStart* Start, AController* Player)
{
	return Start && Start->TryClaim(Player);
}

'''
                anchor='#if WITH_EDITOR\nAPlayerStart* ULyraPlayerSpawningManagerComponent::FindPlayFromHereStart'
                if after.count(anchor)!=1:raise ValueError('Spawn definition anchor changed')
                after=after.replace(anchor,methods+anchor)
            elif suffix=='.h':
                anchor='protected:\n\n};'
                extra='''protected:
	UFUNCTION(BlueprintNativeEvent, Category="UEP|NativeGameplay")
	AActor* UEPChooseTDMStart(AController* Player, const TArray<ALyraPlayerStart*>& PlayerStarts);

};'''
                if after.count(anchor)!=1:raise ValueError('TDM declaration anchor changed')
                after=after.replace(anchor,extra)
            else:
                declaration='AActor* UTDM_PlayerSpawningManagmentComponent::OnChoosePlayerStart(AController* Player, TArray<ALyraPlayerStart*>& PlayerStarts)\n'
                if after.count(declaration)!=1:raise ValueError('TDM definition anchor changed')
                replacement=declaration+'''{
	return UEPChooseTDMStart(Player, PlayerStarts);
}

AActor* UTDM_PlayerSpawningManagmentComponent::UEPChooseTDMStart_Implementation(AController* Player, const TArray<ALyraPlayerStart*>& PlayerStarts)
'''
                after=after.replace(declaration,replacement)
            rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(original)))
    return rows


def patch_text():return ''.join(''.join(difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'],tofile='b/'+r['relative'])) for r in sources())


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve();owned=REPO/'.build'
    if not stage.is_relative_to(owned) or not output.is_relative_to(owned) or output.exists():raise ValueError('Owned stage and fresh spawning patch output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if marker.get('purpose')!='approved-native-gameplay-migration' or not marker.get('independent_file_copies'):raise ValueError('Independent native migration stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP04-spawn-rules.patch'
    if artifact.read_text(encoding='utf-8')!=patch_text():raise ValueError('Versioned spawning patch differs')
    rows=sources()
    for row in rows:
        target=stage/row['relative']
        initial_header=(row['relative']==LG+'.h' and sha(target)=='8918D88A6A2297B262F8DDC7D176E50C99A5B92E00B5EEDDBB5CF3BD15BD38A9')
        if target.read_text(encoding='utf-8-sig') not in (row['before'],row['after']) and not initial_header:raise ValueError('Unrelated spawning edit')
    output.mkdir(parents=True);records=[]
    for row in rows:
        target=stage/row['relative'];archive=output/'PreviousSources'/row['relative'];archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(target.read_bytes());target.write_text(row['after'],encoding='utf-8',newline='\n')
        records.append(dict(path=str(target),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],previous_source=str(archive),previous_sha256=sha(archive),patched_sha256=sha(target)))
    report=dict(schema_version=1,status='patched_requires_native_build',batch='CPP04',policy_events=2,native_occupancy_and_claim_helpers=4,sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP04-spawn-rules.patch'
        if target.exists():raise ValueError('Spawning patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output),indent=2))
