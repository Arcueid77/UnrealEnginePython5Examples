// Stage-only validation fixtures. Not copied into the distributable overlay.
#pragma once

#include "Abilities/GameplayAbility.h"
#include "GameFramework/Actor.h"
#include "Interaction/IInteractableTarget.h"
#include "UEPNativeInteractionFixture.generated.h"

UCLASS(Transient, NotPlaceable)
class AUEPNativeInteractionFixture : public AActor, public IInteractableTarget
{
    GENERATED_BODY()
public:
    AUEPNativeInteractionFixture();
    virtual void GatherInteractionOptions(const FInteractionQuery& Query, FInteractionOptionBuilder& Builder) override;
    virtual void CustomizeInteractionEventData(const FGameplayTag& Tag, FGameplayEventData& Payload) override;
    UFUNCTION(BlueprintCallable)
    static void UEPRouteInteractionInput(UAbilitySystemComponent* AbilitySystem, FGameplayAbilitySpecHandle Handle, bool bPressed);
    UPROPERTY() FInteractionOption Option;
    UPROPERTY() TObjectPtr<AActor> Retarget;
    UPROPERTY() bool bCustomizePayload = false;
    UPROPERTY() int32 CustomizeCount = 0;
    UPROPERTY() int32 TriggerCount = 0;
    UPROPERTY() FGameplayEventData LastEvent;
    UPROPERTY() TObjectPtr<AActor> SeenOwner;
    UPROPERTY() TObjectPtr<AActor> SeenAvatar;
};

UCLASS(Transient)
class UUEPNativeInteractionWitness : public UGameplayAbility
{
    GENERATED_BODY()
public:
    UUEPNativeInteractionWitness();
    virtual void ActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, const FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* Event) override;
};
