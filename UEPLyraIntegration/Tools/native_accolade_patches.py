"""Typed accolade policy seams and native lifetime cancellation."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha
from native_inventory_patches import function_range

ROOT='Plugins/GameFeatures/ShooterCore/Source/ShooterCoreRuntime'
HEADER=ROOT+'/Public/Accolades/LyraAccoladeHostWidget.h'
CPP=ROOT+'/Private/Accolades/LyraAccoladeHostWidget.cpp'


def sources():
    census=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text())
    expected={r['path']:r['sha256'] for field in ('runtime_cpp_files','supporting_declarations') for r in census[field]};rows=[]
    for relative in (HEADER,CPP):
        original=REFERENCE/relative
        if sha(original)!=expected[relative]:raise ValueError('Original accolade source differs from census')
        before=original.read_text(encoding='utf-8-sig');after=before
        if relative==HEADER:
            after=after.replace('\tint32 SequenceID = 0;','\tUPROPERTY(Transient, BlueprintReadOnly)\n\tint32 SequenceID = 0;').replace('\tbool bFinishedLoading = false;','\tUPROPERTY(Transient, BlueprintReadOnly)\n\tbool bFinishedLoading = false;')
            after=after.replace('\tint32 NextDisplaySequenceID = 0;','\tUPROPERTY(Transient)\n\tint32 NextDisplaySequenceID = 0;').replace('\tint32 AllocatedSequenceID = 0;','\tUPROPERTY(Transient)\n\tint32 AllocatedSequenceID = 0;\n\n\tint32 UEPLifetimeGeneration = 0;\n\tbool bUEPAcceptingNotifications = false;')
            start=after.index('\tvoid OnNotificationMessage(')
            after=after[:start]+'''\tvoid OnRegistryLoadCompleted(const FDataRegistryAcquireResult& AccoladeHandle, int32 SequenceID, int32 LifetimeGeneration);

public:
\tUFUNCTION(BlueprintNativeEvent)
\tvoid OnNotificationMessage(FGameplayTag Channel, const FLyraNotificationMessage& Notification);

\tUFUNCTION(BlueprintNativeEvent)
\tvoid UEPQueueAccoladeRow(const FLyraAccoladeDefinitionRow& Row, int32 SequenceID);

\tUFUNCTION(BlueprintNativeEvent)
\tvoid ConsiderLoadedAccolades();

\tUFUNCTION(BlueprintNativeEvent)
\tvoid PopDisplayedAccolade();

\tUFUNCTION(BlueprintNativeEvent)
\tvoid ProcessLoadedAccolade(const FPendingAccoladeEntry& Entry);

\tUFUNCTION(BlueprintNativeEvent)
\tvoid DisplayNextAccolade();

\tUFUNCTION(BlueprintNativeEvent)
\tvoid UEPClearAccoladeState();

\t// Native registry/async/timer facilities retain their object ownership.
\tUFUNCTION(BlueprintCallable)
\tbool UEPRequestAccoladeRow(FGameplayTag PayloadTag, int32 SequenceID);

\tUFUNCTION(BlueprintCallable)
\tvoid UEPStartAccoladeAssetLoad(int32 SequenceID);

\tUFUNCTION(BlueprintCallable)
\tvoid UEPScheduleAccoladePop(float Duration);
};
'''
        else:
            after=after.replace('\tSuper::NativeConstruct();','\t++UEPLifetimeGeneration;\n\tbUEPAcceptingNotifications = true;\n\tSuper::NativeConstruct();',1)
            after=after.replace('void ULyraAccoladeHostWidget::NativeDestruct()\n{','void ULyraAccoladeHostWidget::NativeDestruct()\n{\n\tbUEPAcceptingNotifications = false;\n\t++UEPLifetimeGeneration;',1)
            after=after.replace('\tCancelAsyncLoading();','\tCancelAsyncLoading();\n\tif (UWorld* World = GetWorld())\n\t{\n\t\tWorld->GetTimerManager().ClearTimer(NextTimeToReconsiderHandle);\n\t}\n\tUEPClearAccoladeState();',1)
            start=after.index('\t\tFDataRegistryId ItemID(');end=after.index('\n\t}',start)
            after=after[:start]+'''\t\tif (!UEPRequestAccoladeRow(Notification.PayloadTag, NextID))
\t\t{
\t\t\t--AllocatedSequenceID;
\t\t}'''+after[end:]
            start,opening,end=function_range(after,'void ULyraAccoladeHostWidget::OnRegistryLoadCompleted(')
            after=after[:start]+'''void ULyraAccoladeHostWidget::OnRegistryLoadCompleted(const FDataRegistryAcquireResult& AccoladeHandle, int32 SequenceID, int32 LifetimeGeneration)
{
\tif (!bUEPAcceptingNotifications || LifetimeGeneration != UEPLifetimeGeneration)
\t{
\t\treturn;
\t}
\tif (const FLyraAccoladeDefinitionRow* AccoladeRow = AccoladeHandle.GetItem<FLyraAccoladeDefinitionRow>())
\t{
\t\tUEPQueueAccoladeRow(*AccoladeRow, SequenceID);
\t}
\telse
\t{
\t\tensure(false);
\t}
}'''+after[end:]
            for name in ('OnNotificationMessage','ConsiderLoadedAccolades','PopDisplayedAccolade','ProcessLoadedAccolade','DisplayNextAccolade'):
                after=after.replace('ULyraAccoladeHostWidget::'+name+'(','ULyraAccoladeHostWidget::'+name+'_Implementation(')
            after+='''
bool ULyraAccoladeHostWidget::UEPRequestAccoladeRow(FGameplayTag PayloadTag, int32 SequenceID)
{
\tFDataRegistryId ItemID(NAME_AccoladeRegistryID, PayloadTag.GetTagName());
\tif (!UDataRegistrySubsystem::Get()->AcquireItem(ItemID, FDataRegistryItemAcquiredCallback::CreateUObject(this, &ThisClass::OnRegistryLoadCompleted, SequenceID, UEPLifetimeGeneration)))
\t{
\t\tUE_LOG(LogLyra, Error, TEXT("Failed to find accolade registry for tag %s, accolades will not appear"), *PayloadTag.GetTagName().ToString());
\t\treturn false;
\t}
\treturn true;
}

void ULyraAccoladeHostWidget::UEPQueueAccoladeRow_Implementation(const FLyraAccoladeDefinitionRow& Row, int32 SequenceID)
{
\tFPendingAccoladeEntry& Entry = PendingAccoladeLoads.AddDefaulted_GetRef();
\tEntry.Row = Row;
\tEntry.SequenceID = SequenceID;
\tUEPStartAccoladeAssetLoad(SequenceID);
}

void ULyraAccoladeHostWidget::UEPStartAccoladeAssetLoad(int32 SequenceID)
{
\tconst FPendingAccoladeEntry* Entry = PendingAccoladeLoads.FindByPredicate([SequenceID](const FPendingAccoladeEntry& Candidate) { return Candidate.SequenceID == SequenceID; });
\tif (!ensure(Entry)) { return; }
\tTArray<FSoftObjectPath> AssetsToLoad;
\tAssetsToLoad.Add(Entry->Row.Sound.ToSoftObjectPath());
\tAssetsToLoad.Add(Entry->Row.Icon.ToSoftObjectPath());
\tconst int32 LifetimeGeneration = UEPLifetimeGeneration;
\tAsyncLoad(AssetsToLoad, [this, SequenceID, LifetimeGeneration]
\t{
\t\tif (!bUEPAcceptingNotifications || LifetimeGeneration != UEPLifetimeGeneration) { return; }
\t\tFPendingAccoladeEntry* Finished = PendingAccoladeLoads.FindByPredicate([SequenceID](const FPendingAccoladeEntry& Candidate) { return Candidate.SequenceID == SequenceID; });
\t\tif (ensure(Finished))
\t\t{
\t\t\tFinished->Sound = Finished->Row.Sound.Get();
\t\t\tFinished->Icon = Finished->Row.Icon.Get();
\t\t\tFinished->bFinishedLoading = true;
\t\t\tConsiderLoadedAccolades();
\t\t}
\t});
\tStartAsyncLoading();
}

void ULyraAccoladeHostWidget::UEPScheduleAccoladePop(float Duration)
{
\tGetWorld()->GetTimerManager().SetTimer(NextTimeToReconsiderHandle, this, &ThisClass::PopDisplayedAccolade, Duration);
}

void ULyraAccoladeHostWidget::UEPClearAccoladeState_Implementation()
{
\tfor (const FPendingAccoladeEntry& Entry : PendingAccoladeDisplays)
\t{
\t\tif (UUserWidget* Widget = Entry.AllocatedWidget) { DestroyAccoladeWidget(Widget); }
\t}
\tPendingAccoladeLoads.Reset();
\tPendingAccoladeDisplays.Reset();
\tNextDisplaySequenceID = 0;
\tAllocatedSequenceID = 0;
}
'''
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(original)))
    return rows


def patch_text():return ''.join(''.join(difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'],tofile='b/'+r['relative'])) for r in sources())


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve();owned=REPO/'.build'
    if not stage.is_relative_to(owned) or not output.is_relative_to(owned) or output.exists():raise ValueError('Owned stage and fresh accolade patch output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if marker.get('purpose')!='approved-native-gameplay-migration' or not marker.get('independent_file_copies'):raise ValueError('Independent native stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP07-accolade-rules.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned accolade patch differs')
    rows=sources()
    for row in rows:
        if (stage/row['relative']).read_text(encoding='utf-8-sig') not in (row['before'],row['after']):raise ValueError('Unrelated accolade source edit')
    output.mkdir(parents=True);records=[]
    for row in rows:
        target=stage/row['relative'];archive=output/'PreviousSources'/row['relative'];archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(target.read_bytes());target.write_text(row['after'],encoding='utf-8',newline='\n')
        records.append(dict(path=str(target),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],previous_source=str(archive),previous_sha256=sha(archive),patched_sha256=sha(target)))
    result=dict(schema_version=1,status='patched_requires_native_build',batch='CPP07',policy_events=7,sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP07-accolade-rules.patch'
        if target.exists():raise ValueError('Accolade patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output),indent=2))
