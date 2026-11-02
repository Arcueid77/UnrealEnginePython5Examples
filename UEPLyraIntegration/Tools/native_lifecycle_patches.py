"""CPP-019/020/021: policy seams with native GAS context and primitive execution."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha


def replace_function(text,signature,body):
    start=text.index(signature);opening=text.index('{',start);depth=1;end=opening+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[:opening+1]+'\n'+body+'\n'+text[end-1:]


def original_function_body(text,signature):
    start=text.index(signature);opening=text.index('{',start);depth=1;end=opening+1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[opening+1:end-1]


def sources():
    census=json.loads((REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json').read_text());expected={r['path']:r['sha256'] for k in ('runtime_cpp_files','supporting_declarations') for r in census[k]};rows=[]
    declarations={
      'Jump':'''    UFUNCTION(BlueprintNativeEvent, BlueprintPure) bool UEPUsesPythonJumpPolicy() const;
    UFUNCTION(BlueprintNativeEvent, BlueprintPure) bool UEPShouldCheckJumpSuper(bool bHasAvatar, bool bHasCharacter, bool bCanJump) const;
    UFUNCTION(BlueprintNativeEvent) void UEPRunJumpStart(ALyraCharacter* Character, bool bLocal, bool bPressed);
    UFUNCTION(BlueprintNativeEvent) void UEPRunJumpStop(ALyraCharacter* Character, bool bLocal, bool bPressed);
''',
      'Death':'''    UFUNCTION(BlueprintNativeEvent, BlueprintPure) bool UEPUsesPythonDeathPolicy() const;
    UFUNCTION(BlueprintNativeEvent) TArray<FName> UEPDeathActivationPlan(bool bAutoStart) const;
    UFUNCTION(BlueprintNativeEvent) TArray<FName> UEPDeathEndPlan() const;
    UFUNCTION(BlueprintNativeEvent, BlueprintPure) bool UEPShouldStartDeath(bool bHasHealth, int32 State) const;
    UFUNCTION(BlueprintNativeEvent, BlueprintPure) bool UEPShouldFinishDeath(bool bHasHealth, int32 State) const;
''',
      'Reset':'''    UFUNCTION(BlueprintNativeEvent, BlueprintPure) UE_API bool UEPUsesPythonResetPolicy() const;
    UFUNCTION(BlueprintNativeEvent) UE_API TArray<FName> UEPResetActivationPlan() const;
'''}
    for kind in ('Jump','Death','Reset'):
        cls='ULyraGameplayAbility_'+kind
        for suffix in ('.h','.cpp'):
            rel='Source/LyraGame/AbilitySystem/Abilities/LyraGameplayAbility_'+kind+suffix;p=REFERENCE/rel
            if sha(p)!=expected[rel]:raise ValueError('Original lifecycle source differs: '+rel)
            before=p.read_text(encoding='utf-8-sig');after=before
            if suffix=='.h':
                if kind=='Jump':after=after.replace('class UObject;','class UObject;\nclass ALyraCharacter;')
                after=after.replace('protected:\n','protected:\n'+declarations[kind]+'\n',1)
            elif kind=='Jump':
                signature='bool '+cls+'::CanActivateAbility('
                body=original_function_body(after,signature)
                branch='''    if (UEPUsesPythonJumpPolicy())
    {
        const bool bHasAvatar = ActorInfo && ActorInfo->AvatarActor.IsValid();
        const ALyraCharacter* Character = bHasAvatar ? Cast<ALyraCharacter>(ActorInfo->AvatarActor.Get()) : nullptr;
        const bool bContinue = UEPShouldCheckJumpSuper(bHasAvatar, Character != nullptr, Character && Character->CanJump());
        if (!bContinue || !ActorInfo || !Character) { return false; }
        return Super::CanActivateAbility(Handle, ActorInfo, SourceTags, TargetTags, OptionalRelevantTags);
    }
''';after=replace_function(after,signature,branch+body)
                for action in ('Start','Stop'):
                    signature='void '+cls+'::CharacterJump'+action+'(';body=original_function_body(after,signature)
                    branch='''    if (UEPUsesPythonJumpPolicy())
    {
        ALyraCharacter* Character = GetLyraCharacterFromActorInfo();
        UEPRunJump'''+action+'''(Character, Character && Character->IsLocallyControlled(), Character && Character->bPressedJump);
        return;
    }
''';after=replace_function(after,signature,branch+body)
                after+='''
bool ULyraGameplayAbility_Jump::UEPUsesPythonJumpPolicy_Implementation() const { return false; }
bool ULyraGameplayAbility_Jump::UEPShouldCheckJumpSuper_Implementation(bool bHasAvatar, bool bHasCharacter, bool bCanJump) const { return false; }
void ULyraGameplayAbility_Jump::UEPRunJumpStart_Implementation(ALyraCharacter* Character, bool bLocal, bool bPressed) {}
void ULyraGameplayAbility_Jump::UEPRunJumpStop_Implementation(ALyraCharacter* Character, bool bLocal, bool bPressed) {}
'''
            elif kind=='Death':
                for method in ('ActivateAbility','EndAbility'):
                    signature='void '+cls+'::'+method+'(';body=original_function_body(after,signature)
                    if method=='ActivateAbility':
                        dispatch='''        ULyraAbilitySystemComponent* LyraASC = CastChecked<ULyraAbilitySystemComponent>(ActorInfo->AbilitySystemComponent.Get());
        for (FName Action : UEPDeathActivationPlan(bAutoStartDeath))
        {
            if (Action == TEXT("CancelOthers")) { FGameplayTagContainer Ignore; Ignore.AddTag(LyraGameplayTags::Ability_Behavior_SurvivesDeath); LyraASC->CancelAbilities(nullptr, &Ignore, this); }
            else if (Action == TEXT("MakeUncancelable")) { SetCanBeCanceled(false); }
            else if (Action == TEXT("BlockAbilities")) { if (!ChangeActivationGroup(ELyraAbilityActivationGroup::Exclusive_Blocking)) { UE_LOG(LogLyraAbilitySystem, Error, TEXT("UEP death activation group failed")); } }
            else if (Action == TEXT("StartDeath")) { StartDeath(); }
            else if (Action == TEXT("ActivateBlueprint")) { Super::ActivateAbility(Handle, ActorInfo, ActivationInfo, TriggerEventData); return; }
            else { ensureMsgf(false, TEXT("Unknown UEP death activation command")); return; }
        }
'''
                    else:
                        dispatch='''        for (FName Action : UEPDeathEndPlan())
        {
            if (Action == TEXT("FinishDeath")) { FinishDeath(); }
            else if (Action == TEXT("EndBlueprint")) { Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled); return; }
            else { ensureMsgf(false, TEXT("Unknown UEP death end command")); return; }
        }
'''
                    branch='''    check(ActorInfo);
    if (UEPUsesPythonDeathPolicy())
    {
'''+dispatch+'''        ensureMsgf(false, TEXT("UEP death plan did not execute its terminal action"));
        return; // A handled Python plan never replays the native body.
    }
''';after=replace_function(after,signature,branch+body)
                for action in ('Start','Finish'):
                    signature='void '+cls+'::'+action+'Death(';body=original_function_body(after,signature)
                    branch='''    if (UEPUsesPythonDeathPolicy())
    {
        ULyraHealthComponent* Health = ULyraHealthComponent::FindHealthComponent(GetAvatarActorFromActorInfo());
        const bool bApply = UEPShould'''+action+'''Death(Health != nullptr, Health ? static_cast<int32>(Health->GetDeathState()) : -1);
        if (Health && bApply) { Health->'''+action+'''Death(); }
        return;
    }
''';after=replace_function(after,signature,branch+body)
                after+='''
bool ULyraGameplayAbility_Death::UEPUsesPythonDeathPolicy_Implementation() const { return false; }
TArray<FName> ULyraGameplayAbility_Death::UEPDeathActivationPlan_Implementation(bool bAutoStart) const { return {}; }
TArray<FName> ULyraGameplayAbility_Death::UEPDeathEndPlan_Implementation() const { return {}; }
bool ULyraGameplayAbility_Death::UEPShouldStartDeath_Implementation(bool bHasHealth, int32 State) const { return false; }
bool ULyraGameplayAbility_Death::UEPShouldFinishDeath_Implementation(bool bHasHealth, int32 State) const { return false; }
'''
            else:
                signature='void '+cls+'::ActivateAbility(';body=original_function_body(after,signature)
                branch='''    check(ActorInfo);
    if (UEPUsesPythonResetPolicy())
    {
        ULyraAbilitySystemComponent* LyraASC = CastChecked<ULyraAbilitySystemComponent>(ActorInfo->AbilitySystemComponent.Get());
        for (FName Action : UEPResetActivationPlan())
        {
            if (Action == TEXT("CancelOthers")) { FGameplayTagContainer Ignore; Ignore.AddTag(LyraGameplayTags::Ability_Behavior_SurvivesDeath); LyraASC->CancelAbilities(nullptr, &Ignore, this); }
            else if (Action == TEXT("MakeUncancelable")) { SetCanBeCanceled(false); }
            else if (Action == TEXT("ResetCharacter")) { if (ALyraCharacter* Character = Cast<ALyraCharacter>(CurrentActorInfo->AvatarActor.Get())) { Character->Reset(); } }
            else if (Action == TEXT("BroadcastReset")) { FLyraPlayerResetMessage Message; Message.OwnerPlayerState = CurrentActorInfo->OwnerActor.Get(); UGameplayMessageSubsystem::Get(this).BroadcastMessage(LyraGameplayTags::GameplayEvent_Reset, Message); }
            else if (Action == TEXT("ActivateBlueprint")) { Super::ActivateAbility(Handle, ActorInfo, ActivationInfo, TriggerEventData); }
            else if (Action == TEXT("EndAbility")) { EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, false); return; }
            else { ensureMsgf(false, TEXT("Unknown UEP reset command")); return; }
        }
        ensureMsgf(false, TEXT("UEP reset plan did not execute its terminal action"));
        return;
    }
''';after=replace_function(after,signature,branch+body)
                after+='''
bool ULyraGameplayAbility_Reset::UEPUsesPythonResetPolicy_Implementation() const { return false; }
TArray<FName> ULyraGameplayAbility_Reset::UEPResetActivationPlan_Implementation() const { return {}; }
'''
            if suffix=='.cpp' and kind in ('Jump','Death'):
                after=after.replace('#include UE_INLINE_GENERATED_CPP_BY_NAME(', '#include "UObject/UnrealType.h"\n\n#include UE_INLINE_GENERATED_CPP_BY_NAME(',1)
                guard='UEP'+kind+'PolicyTearingDown';property_name='UEP'+kind+'TearingDown'
                token='ULyraGameplayAbility_'+kind+'::ULyraGameplayAbility_'+kind
                position=after.index(token)
                helper='static bool '+guard+'(const UObject* Ability)\n{\n    const FBoolProperty* Flag = FindFProperty<FBoolProperty>(Ability->GetClass(), TEXT("'+property_name+'"));\n    return Flag && Flag->GetPropertyValue_InContainer(Ability);\n}\n\n'
                after=after[:position]+helper+after[position:];after=after.replace('if (UEPUsesPython'+kind+'Policy())','if (!'+guard+'(this) && UEPUsesPython'+kind+'Policy())')
            rows.append(dict(relative=rel,before=before,after=after,original_sha256=sha(p)))
    return rows


def patch_text():
    return ''.join(line if line.endswith('\n') else line+'\n' for r in sources() for line in difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'],tofile='b/'+r['relative']))


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve()
    if not stage.is_relative_to(REPO/'.build/LyraValidation/CppGameplayExtended') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned stage and fresh lifecycle patch report required')
    if not json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['independent_file_copies']:raise ValueError('Independent stage required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP13-15-ability-lifecycle.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned lifecycle patch differs')
    rows=sources()
    for r in rows:
        if (stage/r['relative']).read_text(encoding='utf-8-sig') not in (r['before'],r['after']):raise ValueError('Unrelated lifecycle source edit')
    output.mkdir(parents=True);records=[]
    for r in rows:
        p=stage/r['relative'];backup=output/'PreviousSources'/r['relative'];backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(p.read_bytes());p.write_text(r['after'],encoding='utf-8',newline='\n');records.append(dict(path=str(p),original=str(REFERENCE/r['relative']),original_sha256=r['original_sha256'],patched_sha256=sha(p)))
    result=dict(status='patched_requires_native_build',candidates=['CPP-019','CPP-020','CPP-021'],sources=records,runtime_acceptance=False);(output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(apply(a.stage,a.output),indent=2))
