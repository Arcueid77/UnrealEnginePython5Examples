"""Interaction policy seams, with native interfaces/soft references/GAS retained."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha
from native_inventory_patches import function_range

BASE='Source/LyraGame/Interaction/Abilities/LyraGameplayAbility_Interact'


def sources():
    inventory=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text())
    expected={r['path']:r['sha256'] for field in ('runtime_cpp_files','supporting_declarations') for r in inventory[field]};rows=[]
    for relative in (BASE+'.h',BASE+'.cpp'):
        original=REFERENCE/relative
        if sha(original)!=expected[relative]:raise ValueError('Original interaction source differs from census')
        before=original.read_text(encoding='utf-8-sig');after=before
        if relative.endswith('.h'):
            after=after.replace('class UIndicatorDescriptor;','class UIndicatorDescriptor;\nclass ULyraIndicatorManagerComponent;')
            after=after.replace('UFUNCTION(BlueprintCallable)','UFUNCTION(BlueprintCallable, BlueprintNativeEvent)',2)
            after=after.replace('\nprotected:\n\tUPROPERTY(BlueprintReadWrite)', '''
\t// Narrow native facilities for interfaces, soft class paths, and GAS actor info.
\tUFUNCTION(BlueprintCallable)
\tULyraIndicatorManagerComponent* UEPGetInteractionIndicatorManager() const;

\tUFUNCTION(BlueprintCallable)
\tAActor* UEPGetInteractionTargetActor(const FInteractionOption& Option) const;

\tUFUNCTION(BlueprintCallable)
\tbool UEPHasInteractionWidget(const FInteractionOption& Option) const;

\tUFUNCTION(BlueprintCallable)
\tvoid UEPSetInteractionIndicatorClass(UIndicatorDescriptor* Indicator, const FInteractionOption& Option, bool bUseOption);

\tUFUNCTION(BlueprintPure)
\tFString UEPInteractionIndicatorPath(UIndicatorDescriptor* Indicator) const;

\tUFUNCTION(BlueprintPure)
\tFString UEPDefaultInteractionWidgetPath() const;

\tUFUNCTION(BlueprintCallable)
\tvoid UEPTriggerInteractionOption(const FInteractionOption& Option);

protected:
\tUPROPERTY(BlueprintReadWrite)''',1)
        else:
            start,opening,end=function_range(after,'void ULyraGameplayAbility_Interact::TriggerInteraction()')
            body=after[opening+1:end-1];payload=body[body.index('\n\t\tAActor* Instigator'):body.rfind('\n\t}')]
            payload=payload.replace('\n\t\t','\n\t')
            after=after[:opening+1]+'''
\tif (CurrentOptions.Num() == 0) { return; }
\tif (GetAbilitySystemComponentFromActorInfo())
\t{
\t\tUEPTriggerInteractionOption(CurrentOptions[0]);
\t}
'''+after[end-1:]
            after=after.replace('::UpdateInteractions(','::UpdateInteractions_Implementation(').replace('::TriggerInteraction()','::TriggerInteraction_Implementation()')
            after+='''
ULyraIndicatorManagerComponent* ULyraGameplayAbility_Interact::UEPGetInteractionIndicatorManager() const
{
\treturn ULyraIndicatorManagerComponent::GetComponent(GetLyraPlayerControllerFromActorInfo());
}

AActor* ULyraGameplayAbility_Interact::UEPGetInteractionTargetActor(const FInteractionOption& Option) const
{
\treturn UInteractionStatics::GetActorFromInteractableTarget(Option.InteractableTarget);
}

bool ULyraGameplayAbility_Interact::UEPHasInteractionWidget(const FInteractionOption& Option) const
{
\treturn !Option.InteractionWidgetClass.IsNull();
}

void ULyraGameplayAbility_Interact::UEPSetInteractionIndicatorClass(UIndicatorDescriptor* Indicator, const FInteractionOption& Option, bool bUseOption)
{
\tIndicator->SetIndicatorClass(bUseOption ? Option.InteractionWidgetClass : DefaultInteractionWidgetClass);
}

FString ULyraGameplayAbility_Interact::UEPInteractionIndicatorPath(UIndicatorDescriptor* Indicator) const
{
\treturn Indicator->GetIndicatorClass().ToSoftObjectPath().ToString();
}

FString ULyraGameplayAbility_Interact::UEPDefaultInteractionWidgetPath() const
{
\treturn DefaultInteractionWidgetClass.ToSoftObjectPath().ToString();
}

void ULyraGameplayAbility_Interact::UEPTriggerInteractionOption(const FInteractionOption& InteractionOption)
{'''+payload+'\n}\n'
        if after==before:raise ValueError('Interaction policy patch did not apply')
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(original)))
    return rows


def patch_text():return ''.join(''.join(difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'],tofile='b/'+r['relative'])) for r in sources())


def apply(stage,output,previous_build=None):
    stage,output=stage.resolve(),output.resolve();owned=REPO/'.build'
    if not stage.is_relative_to(owned) or not output.is_relative_to(owned) or output.exists():raise ValueError('Owned stage and fresh interaction patch output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if marker.get('purpose')!='approved-native-gameplay-migration' or not marker.get('independent_file_copies'):raise ValueError('Independent native stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP08-interaction-rules.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned interaction patch differs')
    rows=sources()
    previous_sources={}
    if previous_build is not None:
        previous_build=previous_build.resolve()
        if not previous_build.is_relative_to(owned):raise ValueError('Owned previous interaction build required')
        previous=json.loads((previous_build/'summary.json').read_text(encoding='utf-8-sig'))
        if previous['status']!='built_requires_native_acceptance' or previous['error'] is not None:raise ValueError('Successful previous interaction build required')
        if any(sha(Path(r['path']))!=r['sha256'] for r in previous['products']):raise ValueError('Previous native interaction product changed')
        previous_sources={r['path']:r['patched_sha256'] for r in json.loads((previous_build/'SourcePatch/summary.json').read_text(encoding='utf-8-sig'))['sources']}
    for row in rows:
        target=stage/row['relative']
        if target.read_text(encoding='utf-8-sig') not in (row['before'],row['after']) and previous_sources.get(str(target))!=sha(target):raise ValueError('Unrelated interaction edit')
    output.mkdir(parents=True);records=[]
    for row in rows:
        target=stage/row['relative'];archive=output/'PreviousSources'/row['relative'];archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(target.read_bytes());target.write_text(row['after'],encoding='utf-8',newline='\n')
        records.append(dict(path=str(target),original=str(REFERENCE/row['relative']),original_sha256=row['original_sha256'],previous_source=str(archive),previous_sha256=sha(archive),patched_sha256=sha(target)))
    result=dict(schema_version=1,status='patched_requires_native_build',batch='CPP08',policy_events=2,sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--previous-build',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP08-interaction-rules.patch'
        if target.exists():raise ValueError('Interaction patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output,a.previous_build),indent=2))
