"""Route native item/player cost rules through their existing ability owner."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha

TYPES='''#pragma once
#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "LyraTagStackCostPolicy.generated.h"

USTRUCT(BlueprintType)
struct LYRAGAME_API FUEPTagStackCostContext
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) bool bHasTarget = false;
    UPROPERTY(BlueprintReadOnly) bool bPlayerStack = false;
    UPROPERTY(BlueprintReadOnly) bool bAuthority = false;
    UPROPERTY(BlueprintReadOnly) bool bHasFailureTagOutput = false;
    UPROPERTY(BlueprintReadOnly) int32 Available = 0;
    UPROPERTY(BlueprintReadOnly) int32 Quantity = 0;
    UPROPERTY(BlueprintReadOnly) FGameplayTag Tag;
    UPROPERTY(BlueprintReadOnly) FGameplayTag FailureTag;
};

USTRUCT(BlueprintType)
struct LYRAGAME_API FUEPTagStackCostCheckResult
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadWrite) bool bCanPay = false;
    UPROPERTY(BlueprintReadWrite) bool bAddFailureTag = false;
};
'''


def sources():
    paths=['LyraGameplayAbility.h','LyraGameplayAbility.cpp','LyraAbilityCost_ItemTagStack.h','LyraAbilityCost_ItemTagStack.cpp','LyraAbilityCost_PlayerTagStack.h','LyraAbilityCost_PlayerTagStack.cpp']
    census=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text());expected={r['path']:r['sha256'] for k in ('runtime_cpp_files','supporting_declarations') for r in census[k]};rows=[]
    for name in paths:
        relative='Source/LyraGame/AbilitySystem/Abilities/'+name;p=REFERENCE/relative
        if sha(p)!=expected[relative]:raise ValueError('Original cost source changed')
        before=p.read_text(encoding='utf-8-sig');after=before
        if name=='LyraGameplayAbility.h':
            after=after.replace('#include "LyraGameplayAbility.generated.h"','#include "LyraTagStackCostPolicy.h"\n#include "LyraGameplayAbility.generated.h"')
            token='\tUE_API ULyraGameplayAbility(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());'
            after=after.replace(token,token+'''

\tUFUNCTION(BlueprintNativeEvent, BlueprintPure)
\tUE_API bool UEPUsesPythonTagStackCosts(bool bPlayerStack) const;
\tUFUNCTION(BlueprintNativeEvent)
\tUE_API FUEPTagStackCostCheckResult UEPCheckTagStackCost(const FUEPTagStackCostContext& Context) const;
\tUFUNCTION(BlueprintNativeEvent)
\tUE_API int32 UEPApplyTagStackCost(const FUEPTagStackCostContext& Context) const;
''')
        elif name=='LyraGameplayAbility.cpp':
            after+='''
bool ULyraGameplayAbility::UEPUsesPythonTagStackCosts_Implementation(bool bPlayerStack) const
{
    return false;
}
FUEPTagStackCostCheckResult ULyraGameplayAbility::UEPCheckTagStackCost_Implementation(const FUEPTagStackCostContext& Context) const
{
    return FUEPTagStackCostCheckResult();
}
int32 ULyraGameplayAbility::UEPApplyTagStackCost_Implementation(const FUEPTagStackCostContext& Context) const
{
    return 0;
}
'''
        else:
            player='PlayerTagStack' in name;kind='true' if player else 'false';target_type='ALyraPlayerState' if player else 'ULyraInventoryItemInstance';cls='ULyraAbilityCost_'+('PlayerTagStack' if player else 'ItemTagStack')
            if name.endswith('.h'):
                generated='#include "'+name[:-2]+'.generated.h"';after=after.replace(generated,'#include "LyraTagStackCostPolicy.h"\n'+generated)
                after=after.replace('class ULyraGameplayAbility;','class ULyraGameplayAbility;\nclass '+target_type+';')
                after=after.replace('protected:\n','protected:\n\tFUEPTagStackCostContext UEPBuildCostContext(const ULyraGameplayAbility* Ability, FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const '+target_type+'* Target, bool bCollectFailure) const;\n\n',1)
            else:
                if not player:
                    token='#include UE_INLINE_GENERATED_CPP_BY_NAME(LyraAbilityCost_ItemTagStack)'
                    if token not in after:raise ValueError('Original item cost generated registration include differs')
                    after=after.replace(token,token+'\n#include UE_INLINE_GENERATED_CPP_BY_NAME(LyraTagStackCostPolicy)')
                target_setup=('''ALyraPlayerState* Target = nullptr;
        if (AController* Controller = Ability->GetControllerFromActorInfo()) { Target = Cast<ALyraPlayerState>(Controller->PlayerState); }''' if player else '''ULyraInventoryItemInstance* Target = nullptr;
        if (const ULyraGameplayAbility_FromEquipment* EquipmentAbility = Cast<const ULyraGameplayAbility_FromEquipment>(Ability)) { Target = EquipmentAbility->GetAssociatedItem(); }''')
                token='bool '+cls+'::CheckCost('
                start=after.index('{',after.index(token))+1
                failure='' if player else '\n        if (!Decision.bCanPay && Decision.bAddFailureTag && Target && OptionalRelevantTags && FailureTag.IsValid()) { OptionalRelevantTags->AddTag(FailureTag); }'
                body='''
    if (Ability->UEPUsesPythonTagStackCosts('''+kind+'''))
    {
        '''+target_setup+'''
        const FUEPTagStackCostContext Context = UEPBuildCostContext(Ability, Handle, ActorInfo, Target, OptionalRelevantTags != nullptr);
        const FUEPTagStackCostCheckResult Decision = Ability->UEPCheckTagStackCost(Context);'''+failure+'''
        return Decision.bCanPay;
    }
'''
                after=after[:start]+body+after[start:]
                token='void '+cls+'::ApplyCost(';start=after.index('{',after.index(token))+1
                body='''
    if (ActorInfo->IsNetAuthority() && Ability->UEPUsesPythonTagStackCosts('''+kind+'''))
    {
        '''+target_setup+'''
        if (Target)
        {
            const FUEPTagStackCostContext Context = UEPBuildCostContext(Ability, Handle, ActorInfo, Target, false);
            const int32 Amount = Ability->UEPApplyTagStackCost(Context);
            Target->RemoveStatTagStack(Tag, Amount);
        }
        return; // Never replay a failed/handled Python operation through native cost code.
    }
'''
                after=after[:start]+body+after[start:]
                after+='''
FUEPTagStackCostContext '''+cls+'''::UEPBuildCostContext(const ULyraGameplayAbility* Ability, FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const '''+target_type+'''* Target, bool bCollectFailure) const
{
    FUEPTagStackCostContext Context;
    Context.bPlayerStack = '''+kind+''';
    Context.bAuthority = ActorInfo->IsNetAuthority();
    Context.bHasFailureTagOutput = bCollectFailure;
    Context.Tag = Tag;
'''+('    Context.FailureTag = FailureTag;\n' if not player else '')+'''
    if (Target)
    {
        Context.bHasTarget = true;
        Context.Quantity = FMath::TruncToInt(Quantity.GetValueAtLevel(Ability->GetAbilityLevel(Handle, ActorInfo)));
        Context.Available = Target->GetStatTagStackCount(Tag);
    }
    return Context;
}
'''
        if after==before:raise ValueError('Cost patch did not apply: '+name)
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(p)))
    rows.append(dict(relative='Source/LyraGame/AbilitySystem/Abilities/LyraTagStackCostPolicy.h',before='',after=TYPES,original_sha256=None));return rows


def patch_text():
    output=[]
    for r in sources():
        for line in difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'] if r['before'] else '/dev/null',tofile='b/'+r['relative']):output.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
    return ''.join(output)


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve()
    if not stage.is_relative_to(REPO/'.build/LyraValidation/CppGameplayExtended') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Fresh extended cost output required')
    marker=json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))
    if not marker.get('independent_file_copies'):raise ValueError('Independent cost stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP11-12-tag-stack-costs.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned cost patch differs')
    rows=sources()
    for r in rows:
        p=stage/r['relative']
        if (p.read_text(encoding='utf-8-sig') if p.exists() else '') not in (r['before'],r['after']):raise ValueError('Unrelated cost edit')
    output.mkdir(parents=True);records=[]
    for r in rows:
        p=stage/r['relative'];archive=output/'PreviousSources'/r['relative'];archive.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():archive.write_bytes(p.read_bytes())
        p.write_text(r['after'],encoding='utf-8',newline='\n');records.append(dict(path=str(p),original=str(REFERENCE/r['relative']) if r['original_sha256'] else None,original_sha256=r['original_sha256'],patched_sha256=sha(p)))
    report=dict(status='patched_requires_native_build',batches=['CPP11','CPP12'],sources=records,patch=dict(path=str(artifact),sha256=sha(artifact)),runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path);p.add_argument('--output',type=Path);p.add_argument('--write-patch',action='store_true');a=p.parse_args()
    if a.write_patch:
        target=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP11-12-tag-stack-costs.patch'
        if target.exists():raise ValueError('Cost patch already exists')
        target.write_text(patch_text(),encoding='utf-8',newline='\n');print(target)
    else:print(json.dumps(apply(a.stage,a.output),indent=2))
