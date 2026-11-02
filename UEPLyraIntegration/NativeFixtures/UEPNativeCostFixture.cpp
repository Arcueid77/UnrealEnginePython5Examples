#include "UEPNativeCostFixture.h"
#include "AbilitySystem/Abilities/LyraAbilityCost.h"
#include "AbilitySystem/Abilities/LyraAbilityCost_ItemTagStack.h"
#include "AbilitySystem/Abilities/LyraAbilityCost_PlayerTagStack.h"
#include "AbilitySystem/LyraAbilitySystemComponent.h"
#include "Inventory/LyraInventoryItemInstance.h"
#include "Equipment/LyraEquipmentInstance.h"
#include "Player/LyraPlayerState.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Abilities/GameplayAbilityTargetTypes.h"
#include "UObject/UnrealType.h"
#include "Engine/CurveTable.h"
#include UE_INLINE_GENERATED_CPP_BY_NAME(UEPNativeCostFixture)

namespace
{
    TArray<TObjectPtr<ULyraAbilityCost>>& CostArray(ULyraGameplayAbility* Ability)
    {
        FArrayProperty* Property = FindFProperty<FArrayProperty>(ULyraGameplayAbility::StaticClass(), TEXT("AdditionalCosts"));
        check(Property);
        return *Property->ContainerPtrToValuePtr<TArray<TObjectPtr<ULyraAbilityCost>>>(Ability);
    }
    template<typename T> T& Field(UObject* Object, const TCHAR* Name)
    {
        FProperty* Property = FindFProperty<FProperty>(Object->GetClass(), Name);
        check(Property);
        return *Property->ContainerPtrToValuePtr<T>(Object);
    }
}

UUEPNativeCostWitness::UUEPNativeCostWitness()
{
    InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::LocalPredicted;
    NetSecurityPolicy = EGameplayAbilityNetSecurityPolicy::ClientOrServer;
    ActivationPolicy = ELyraAbilityActivationPolicy::OnInputTriggered;
}
void UUEPNativeCostWitness::ActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, const FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* Event)
{
    ++NativeActivations;
    if (CommitAbility(Handle, Info, ActivationInfo)) { ++NativeCommits; }
    EndAbility(Handle, Info, ActivationInfo, true, false);
}

void UUEPNativeCostFixture::Configure(UClass* AbilityClass, const TArray<FUEPCostFixtureSpec>& Costs)
{
    ULyraGameplayAbility* Default = CastChecked<ULyraGameplayAbility>(AbilityClass->GetDefaultObject());
    auto& Entries = CostArray(Default);
    Entries.Reset();
    for (const FUEPCostFixtureSpec& Spec : Costs)
    {
        ULyraAbilityCost* Cost = Spec.bPlayerStack ? static_cast<ULyraAbilityCost*>(NewObject<ULyraAbilityCost_PlayerTagStack>(Default)) : NewObject<ULyraAbilityCost_ItemTagStack>(Default);
        FScalableFloat& Quantity = Field<FScalableFloat>(Cost, TEXT("Quantity"));
        Quantity.SetValue(Spec.Quantity);
        Quantity.Curve.CurveTable = Spec.CurveTable;
        Quantity.Curve.RowName = Spec.CurveRow;
        Field<FGameplayTag>(Cost, TEXT("Tag")) = Spec.Tag;
        if (!Spec.bPlayerStack) { Field<FGameplayTag>(Cost, TEXT("FailureTag")) = Spec.FailureTag; }
        FBoolProperty* OnlyHit = FindFProperty<FBoolProperty>(Cost->GetClass(), TEXT("bOnlyApplyCostOnHit"));
        check(OnlyHit); OnlyHit->SetPropertyValue_InContainer(Cost, Spec.bOnlyOnHit);
        Entries.Add(Cost);
    }
}

FGameplayAbilitySpecHandle UUEPNativeCostFixture::Grant(UAbilitySystemComponent* AbilitySystem, UClass* AbilityClass, UObject* SourceObject, int32 Level)
{
    return AbilitySystem->GiveAbility(FGameplayAbilitySpec(AbilityClass, Level, INDEX_NONE, SourceObject));
}

UCurveTable* UUEPNativeCostFixture::MakeCurve(FName Row, float First, float Second)
{
    UCurveTable* Table = NewObject<UCurveTable>();
    FRichCurve& Curve = Table->AddRichCurve(Row);
    Curve.AddKey(1.f, First); Curve.AddKey(2.f, Second);
    return Table;
}

UUEPNativeCostCase* UUEPNativeCostCase::Create(UObject* WorldContext, UClass* AbilityClass, int32 Available, int32 Level, bool bWithEquipment, bool bWithPlayerState)
{
    UWorld* World = WorldContext->GetWorld();
    check(World && !World->IsGameWorld());
    UUEPNativeCostCase* Case = NewObject<UUEPNativeCostCase>();
    Case->Controller = World->SpawnActor<APlayerController>();
    Case->Pawn = World->SpawnActor<APawn>();
    Case->PlayerState = World->SpawnActor<ALyraPlayerState>();
    Case->PlayerState->SetOwner(Case->Controller);
    Case->Controller->PlayerState = bWithPlayerState ? Case->PlayerState.Get() : nullptr;
    Case->Controller->Possess(Case->Pawn);
    Case->AbilitySystem = Case->PlayerState->GetLyraAbilitySystemComponent();
    Case->AbilitySystem->InitAbilityActorInfo(Case->PlayerState, Case->Pawn);
    Case->Item = NewObject<ULyraInventoryItemInstance>(Case->Pawn);
    if (bWithEquipment)
    {
        Case->Equipment = NewObject<ULyraEquipmentInstance>(Case->Pawn);
        Case->Equipment->SetInstigator(Case->Item);
    }
    TSet<FGameplayTag> ItemTags, PlayerTags;
    for (const TObjectPtr<ULyraAbilityCost>& Cost : CostArray(CastChecked<ULyraGameplayAbility>(AbilityClass->GetDefaultObject())))
    {
        const FGameplayTag Tag = Field<FGameplayTag>(Cost, TEXT("Tag"));
        if (Cost->IsA<ULyraAbilityCost_PlayerTagStack>()) { PlayerTags.Add(Tag); }
        else { ItemTags.Add(Tag); }
    }
    for (const FGameplayTag& Tag : ItemTags) { Case->Item->AddStatTagStack(Tag, Available); }
    for (const FGameplayTag& Tag : PlayerTags) { Case->PlayerState->AddStatTagStack(Tag, Available); }
    Case->Handle = UUEPNativeCostFixture::Grant(Case->AbilitySystem, AbilityClass, Case->Equipment, Level);
    FGameplayAbilitySpec* Spec = Case->AbilitySystem->FindAbilitySpecFromHandle(Case->Handle);
    check(Spec); Case->Ability = CastChecked<ULyraGameplayAbility>(Spec->GetPrimaryInstance());
    return Case;
}

FUEPCostFixtureResult UUEPNativeCostCase::Probe(bool bFailureOutput, bool bApply, bool bAuthority, bool bThroughCaller, bool bHit)
{
    auto& Costs = CostArray(Ability);
    check(!Costs.IsEmpty());
    const FGameplayTag Tag = Field<FGameplayTag>(Costs[0], TEXT("Tag"));
    const bool bPlayer = Costs[0]->IsA<ULyraAbilityCost_PlayerTagStack>();
    FUEPCostFixtureResult Result;
    Result.Before = bPlayer ? PlayerState->GetStatTagStackCount(Tag) : Item->GetStatTagStackCount(Tag);
    const ENetRole OldRole = PlayerState->GetLocalRole();
    PlayerState->SetRole(bAuthority ? ROLE_Authority : ROLE_SimulatedProxy);
    const FGameplayAbilityActorInfo* Info = Ability->GetCurrentActorInfo();
    Result.bAuthority = Info->IsNetAuthority();
    Result.bCanPay = bThroughCaller ? static_cast<UGameplayAbility*>(Ability.Get())->CheckCost(Handle, Info, bFailureOutput ? &Result.Failures : nullptr) : Costs[0]->CheckCost(Ability, Handle, Info, bFailureOutput ? &Result.Failures : nullptr);
    if (bApply)
    {
        const FGameplayAbilityActivationInfo ActivationInfo;
        if (bHit)
        {
            FGameplayAbilityTargetDataHandle Data;
            Data.Add(new FGameplayAbilityTargetData_SingleTargetHit());
            AbilitySystem->ServerSetReplicatedTargetData(Handle, ActivationInfo.GetActivationPredictionKey(), Data, FGameplayTag(), FPredictionKey());
        }
        if (bThroughCaller) { static_cast<UGameplayAbility*>(Ability.Get())->ApplyCost(Handle, Info, ActivationInfo); }
        else { Costs[0]->ApplyCost(Ability, Handle, Info, ActivationInfo); }
    }
    PlayerState->SetRole(OldRole);
    Result.After = bPlayer ? PlayerState->GetStatTagStackCount(Tag) : Item->GetStatTagStackCount(Tag);
    return Result;
}
void UUEPNativeCostCase::Clear()
{
    if (AbilitySystem) { AbilitySystem->ClearAbility(Handle); }
    Ability = nullptr; Equipment = nullptr; Item = nullptr;
}
