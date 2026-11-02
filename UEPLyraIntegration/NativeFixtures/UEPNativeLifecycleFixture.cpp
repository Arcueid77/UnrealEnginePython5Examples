#include "UEPNativeLifecycleFixture.h"
#include "AbilitySystem/Abilities/LyraGameplayAbility_Jump.h"
#include "Abilities/GameplayAbility.h"
#include UE_INLINE_GENERATED_CPP_BY_NAME(UEPNativeLifecycleFixture)
bool UUEPNativeLifecycleFixture::ProbeJumpAdmission(ULyraGameplayAbility_Jump* Ability, bool bActorInfo, bool bAvatar)
{
    if (!Ability) { return false; }
    const FGameplayAbilityActorInfo* Original = Ability->GetCurrentActorInfo();
    if (!bActorInfo || !Original) { return static_cast<UGameplayAbility*>(Ability)->CanActivateAbility(Ability->GetCurrentAbilitySpecHandle(), nullptr); }
    FGameplayAbilityActorInfo Snapshot = *Original;
    if (!bAvatar) { Snapshot.AvatarActor.Reset(); }
    return static_cast<UGameplayAbility*>(Ability)->CanActivateAbility(Ability->GetCurrentAbilitySpecHandle(), &Snapshot);
}
