"""CPP10: route initial-stat policy through the existing Const item definition."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha


def sources():
    paths=['Inventory/InventoryFragment_SetStats.h','Inventory/InventoryFragment_SetStats.cpp','Inventory/LyraInventoryItemDefinition.h','Inventory/LyraInventoryItemDefinition.cpp']
    census=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text());expected={r['path']:r['sha256'] for k in ('runtime_cpp_files','supporting_declarations') for r in census[k]};rows=[]
    for suffix in paths:
        relative='Source/LyraGame/'+suffix;p=REFERENCE/relative
        if sha(p)!=expected[relative]:raise ValueError('Original initial-stat source changed')
        before=p.read_text(encoding='utf-8-sig');after=before
        if suffix=='Inventory/InventoryFragment_SetStats.h':
            after=after.replace('UCLASS()','''USTRUCT(BlueprintType)
struct LYRAGAME_API FUEPInitialItemStat
{
\tGENERATED_BODY()
\tUPROPERTY(BlueprintReadOnly) FGameplayTag Tag;
\tUPROPERTY(BlueprintReadOnly) int32 Count = 0;
};

UCLASS()''',1)
            after=after.replace('\tint32 GetItemStatByTag(FGameplayTag Tag) const;','\tint32 GetItemStatByTag(FGameplayTag Tag) const;\n\n\tUFUNCTION(BlueprintCallable)\n\tTArray<FUEPInitialItemStat> UEPGetInitialStats() const;')
        elif suffix=='Inventory/InventoryFragment_SetStats.cpp':
            token='''void UInventoryFragment_SetStats::OnInstanceCreated(ULyraInventoryItemInstance* Instance) const
{'''
            after=after.replace(token,token+'''
\tif (Instance && Instance->GetItemDef())
\t{
\t\tconst ULyraInventoryItemDefinition* Definition = GetDefault<ULyraInventoryItemDefinition>(Instance->GetItemDef());
\t\tif (Definition->UEPUsesPythonInitialStats())
\t\t{
\t\t\tDefinition->UEPInitializeItemStats(this, Instance);
\t\t\treturn; // A failed Python policy must never run the native loop again.
\t\t}
\t}
''')
            after+='''
TArray<FUEPInitialItemStat> UInventoryFragment_SetStats::UEPGetInitialStats() const
{
\tTArray<FUEPInitialItemStat> Result;
\tResult.Reserve(InitialItemStats.Num());
\tfor (const auto& Entry : InitialItemStats)
\t{
\t\tFUEPInitialItemStat& Row = Result.AddDefaulted_GetRef();
\t\tRow.Tag = Entry.Key;
\t\tRow.Count = Entry.Value;
\t}
\treturn Result;
}
'''
        elif suffix=='Inventory/LyraInventoryItemDefinition.h':
            after=after.replace('class ULyraInventoryItemInstance;','class ULyraInventoryItemInstance;\nclass UInventoryFragment_SetStats;')
            after=after.replace('\tULyraInventoryItemDefinition(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());','''\tULyraInventoryItemDefinition(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());

\tUFUNCTION(BlueprintNativeEvent, BlueprintPure)
\tbool UEPUsesPythonInitialStats() const;

\tUFUNCTION(BlueprintNativeEvent)
\tvoid UEPInitializeItemStats(const UInventoryFragment_SetStats* Fragment, ULyraInventoryItemInstance* Instance) const;''')
        else:
            after+='''
bool ULyraInventoryItemDefinition::UEPUsesPythonInitialStats_Implementation() const
{
\treturn false;
}

void ULyraInventoryItemDefinition::UEPInitializeItemStats_Implementation(const UInventoryFragment_SetStats* Fragment, ULyraInventoryItemInstance* Instance) const
{
\tensureMsgf(false, TEXT("Initial-stat Python route selected without its handler"));
}
'''
        if after==before:raise ValueError('Initial-stat patch did not apply')
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(p)))
    return rows


def patch_text():
    result=[]
    for row in sources():
        for line in difflib.unified_diff(row['before'].splitlines(True),row['after'].splitlines(True),fromfile='a/'+row['relative'],tofile='b/'+row['relative']):result.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
    return ''.join(result)


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve()
    if not stage.is_relative_to(REPO/'.build/LyraValidation/CppGameplayExtended') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Fresh extended-stage patch output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if not marker.get('independent_file_copies') or marker.get('purpose')!='approved-native-gameplay-migration':raise ValueError('Independent stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP10-initial-stats.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned initial-stat patch differs')
    rows=sources()
    for row in rows:
        if (stage/row['relative']).read_text(encoding='utf-8-sig') not in (row['before'],row['after']):raise ValueError('Unrelated initial-stat edit')
    output.mkdir(parents=True);records=[]
    for row in rows:
        p=stage/row['relative'];archive=output/'PreviousSources'/row['relative'];archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(p.read_bytes());p.write_text(row['after'],encoding='utf-8',newline='\n');records.append(dict(path=str(p),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],patched_sha256=sha(p),previous_source=str(archive)))
    result=dict(status='patched_requires_native_build',batch='CPP10',sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP10-initial-stats.patch'
        if target.exists():raise ValueError('Initial-stat patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output),indent=2))
