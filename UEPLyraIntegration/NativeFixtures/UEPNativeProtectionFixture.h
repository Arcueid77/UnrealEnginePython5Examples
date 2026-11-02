#pragma once
#include "AbilitySystem/Abilities/LyraGameplayAbility.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "UEPNativeProtectionFixture.generated.h"
class ULyraAbilitySystemComponent;
UCLASS()
class UUEPNativeOrdinaryAbilityWitness : public ULyraGameplayAbility
{
    GENERATED_BODY()
public:
    UUEPNativeOrdinaryAbilityWitness();
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* Event) override;
};
UCLASS()
class UUEPNativeProtectedAbilityWitness : public UUEPNativeOrdinaryAbilityWitness
{
    GENERATED_BODY()
public:
    UUEPNativeProtectedAbilityWitness();
};
UCLASS()
class UUEPNativeProtectionFixture : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable) static FGameplayAbilitySpecHandle GrantActive(ULyraAbilitySystemComponent* ASC, bool bProtected);
    UFUNCTION(BlueprintCallable) static bool WitnessActive(ULyraAbilitySystemComponent* ASC, FGameplayAbilitySpecHandle Handle);
    UFUNCTION(BlueprintCallable) static bool RemoveWitness(ULyraAbilitySystemComponent* ASC, FGameplayAbilitySpecHandle Handle);
    UFUNCTION(BlueprintCallable) static bool SelfDestruct(AActor* Actor);
};
