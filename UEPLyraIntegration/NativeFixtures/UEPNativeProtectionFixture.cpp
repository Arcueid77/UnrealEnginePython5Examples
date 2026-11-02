#include "UEPNativeProtectionFixture.h"
#include "AbilitySystem/LyraAbilitySystemComponent.h"
#include "Character/LyraHealthComponent.h"
#include "LyraGameplayTags.h"
#include UE_INLINE_GENERATED_CPP_BY_NAME(UEPNativeProtectionFixture)
UUEPNativeOrdinaryAbilityWitness::UUEPNativeOrdinaryAbilityWitness()
{
    InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::ServerOnly;
}
void UUEPNativeOrdinaryAbilityWitness::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, FGameplayAbilityActivationInfo ActivationInfo, const FGameplayEventData* Event) {}
UUEPNativeProtectedAbilityWitness::UUEPNativeProtectedAbilityWitness()
{
    FGameplayTagContainer Tags; Tags.AddTag(LyraGameplayTags::Ability_Behavior_SurvivesDeath); SetAssetTags(Tags);
}
FGameplayAbilitySpecHandle UUEPNativeProtectionFixture::GrantActive(ULyraAbilitySystemComponent* ASC, bool bProtected)
{
    check(ASC);
    UClass* Class = bProtected ? UUEPNativeProtectedAbilityWitness::StaticClass() : UUEPNativeOrdinaryAbilityWitness::StaticClass();
    const FGameplayAbilitySpecHandle Handle = ASC->GiveAbility(FGameplayAbilitySpec(Class, 1));
    check(ASC->TryActivateAbility(Handle, false)); return Handle;
}
bool UUEPNativeProtectionFixture::WitnessActive(ULyraAbilitySystemComponent* ASC, FGameplayAbilitySpecHandle Handle)
{
    const FGameplayAbilitySpec* Spec = ASC ? ASC->FindAbilitySpecFromHandle(Handle) : nullptr; return Spec && Spec->IsActive();
}
bool UUEPNativeProtectionFixture::RemoveWitness(ULyraAbilitySystemComponent* ASC, FGameplayAbilitySpecHandle Handle)
{
    if (!ASC) { return false; }
    if (FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromHandle(Handle))
    {
        ASC->CancelAbilityHandle(Handle);
        ASC->ClearAbility(Handle);
    }
    return ASC->FindAbilitySpecFromHandle(Handle) == nullptr;
}
bool UUEPNativeProtectionFixture::SelfDestruct(AActor* Actor)
{
    if (ULyraHealthComponent* Health = ULyraHealthComponent::FindHealthComponent(Actor)) { Health->DamageSelfDestruct(false); return true; }
    return false;
}
