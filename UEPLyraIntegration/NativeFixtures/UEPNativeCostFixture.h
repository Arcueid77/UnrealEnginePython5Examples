// Stage-only cost contexts and native GAS witness; excluded from Overlay.
#pragma once
#include "Equipment/LyraGameplayAbility_FromEquipment.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "UEPNativeCostFixture.generated.h"

class APlayerController;
class ALyraPlayerState;
class APawn;
class ULyraAbilitySystemComponent;
class ULyraInventoryItemInstance;
class ULyraEquipmentInstance;
class UCurveTable;

USTRUCT(BlueprintType)
struct FUEPCostFixtureSpec
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadWrite) bool bPlayerStack = false;
    UPROPERTY(BlueprintReadWrite) float Quantity = 1.f;
    UPROPERTY(BlueprintReadWrite) FGameplayTag Tag;
    UPROPERTY(BlueprintReadWrite) FGameplayTag FailureTag;
    UPROPERTY(BlueprintReadWrite) bool bOnlyOnHit = false;
    UPROPERTY(BlueprintReadWrite) TObjectPtr<UCurveTable> CurveTable;
    UPROPERTY(BlueprintReadWrite) FName CurveRow;
};

USTRUCT(BlueprintType)
struct FUEPCostFixtureResult
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) bool bCanPay = false;
    UPROPERTY(BlueprintReadOnly) FGameplayTagContainer Failures;
    UPROPERTY(BlueprintReadOnly) int32 Before = 0;
    UPROPERTY(BlueprintReadOnly) int32 After = 0;
    UPROPERTY(BlueprintReadOnly) bool bAuthority = false;
};

UCLASS(Blueprintable)
class UUEPNativeCostWitness : public ULyraGameplayAbility_FromEquipment
{
    GENERATED_BODY()
public:
    UUEPNativeCostWitness();
    virtual void ActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, const FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* Event) override;
    UPROPERTY() int32 NativeActivations = 0;
    UPROPERTY() int32 NativeCommits = 0;
};

UCLASS()
class UUEPNativeCostCase : public UObject
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable)
    static UUEPNativeCostCase* Create(UObject* WorldContext, UClass* AbilityClass, int32 Available, int32 Level, bool bWithEquipment, bool bWithPlayerState);
    UFUNCTION(BlueprintCallable)
    FUEPCostFixtureResult Probe(bool bFailureOutput, bool bApply, bool bAuthority, bool bThroughCaller, bool bHit);
    UFUNCTION(BlueprintCallable)
    void Clear();
    UPROPERTY() TObjectPtr<APlayerController> Controller;
    UPROPERTY() TObjectPtr<ALyraPlayerState> PlayerState;
    UPROPERTY() TObjectPtr<APawn> Pawn;
    UPROPERTY() TObjectPtr<ULyraAbilitySystemComponent> AbilitySystem;
    UPROPERTY() TObjectPtr<ULyraInventoryItemInstance> Item;
    UPROPERTY() TObjectPtr<ULyraEquipmentInstance> Equipment;
    UPROPERTY() TObjectPtr<ULyraGameplayAbility> Ability;
    UPROPERTY() FGameplayAbilitySpecHandle Handle;
};

UCLASS()
class UUEPNativeCostFixture : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable)
    static void Configure(UClass* AbilityClass, const TArray<FUEPCostFixtureSpec>& Costs);
    UFUNCTION(BlueprintCallable)
    static FGameplayAbilitySpecHandle Grant(UAbilitySystemComponent* AbilitySystem, UClass* AbilityClass, UObject* SourceObject, int32 Level);
    UFUNCTION(BlueprintCallable)
    static UCurveTable* MakeCurve(FName Row, float First, float Second);
};
