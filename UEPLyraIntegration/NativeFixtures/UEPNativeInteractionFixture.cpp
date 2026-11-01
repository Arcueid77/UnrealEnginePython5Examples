// Stage-only validation of a real native interface customization and GAS event.
#include "UEPNativeInteractionFixture.h"
#include "AbilitySystemComponent.h"
#include "Components/BoxComponent.h"
#include UE_INLINE_GENERATED_CPP_BY_NAME(UEPNativeInteractionFixture)

AUEPNativeInteractionFixture::AUEPNativeInteractionFixture()
{
    bReplicates = true;
    SetReplicateMovement(true);
    bAlwaysRelevant = true;
    UBoxComponent* Box = CreateDefaultSubobject<UBoxComponent>(TEXT("InteractionCollision"));
    Box->SetBoxExtent(FVector(45., 65., 80.));
    Box->SetCollisionProfileName(TEXT("Interactable_BlockDynamic"));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    RootComponent = Box;
    Option.InteractionAbilityToGrant = UUEPNativeInteractionWitness::StaticClass();
}

void AUEPNativeInteractionFixture::GatherInteractionOptions(const FInteractionQuery& Query, FInteractionOptionBuilder& Builder)
{
    Builder.AddInteractionOption(Option);
}

void AUEPNativeInteractionFixture::CustomizeInteractionEventData(const FGameplayTag& Tag, FGameplayEventData& Payload)
{
    ++CustomizeCount;
    if (bCustomizePayload)
    {
        Payload.Target = Retarget;
        Payload.EventMagnitude = 37.f;
        Payload.OptionalObject = this;
    }
}

void AUEPNativeInteractionFixture::UEPRouteInteractionInput(UAbilitySystemComponent* AbilitySystem, FGameplayAbilitySpecHandle Handle, bool bPressed)
{
    if (FGameplayAbilitySpec* Spec = AbilitySystem->FindAbilitySpecFromHandle(Handle))
    {
        // This is the virtual dispatch used by Lyra's ProcessAbilityInput.
        // UAbilitySystemComponent::PressInputID separately emits the same
        // generic event after this dispatch and therefore duplicates it in Lyra.
        Spec->InputPressed = bPressed;
        if (bPressed) { AbilitySystem->AbilitySpecInputPressed(*Spec); }
        else { AbilitySystem->AbilitySpecInputReleased(*Spec); }
    }
}

UUEPNativeInteractionWitness::UUEPNativeInteractionWitness()
{
    InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::LocalPredicted;
}

void UUEPNativeInteractionWitness::ActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, const FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* Event)
{
    AUEPNativeInteractionFixture* Source = Event ? const_cast<AUEPNativeInteractionFixture*>(Cast<AUEPNativeInteractionFixture>(Event->OptionalObject.Get())) : nullptr;
    if (AUEPNativeInteractionFixture* Target = Source)
    {
        ++Target->TriggerCount;
        if (Event) { Target->LastEvent = *Event; }
        Target->SeenOwner = Info->OwnerActor.Get();
        Target->SeenAvatar = Info->AvatarActor.Get();
    }
    EndAbility(Handle, Info, ActivationInfo, true, false);
}
