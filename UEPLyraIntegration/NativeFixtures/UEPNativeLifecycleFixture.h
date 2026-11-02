#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "UEPNativeLifecycleFixture.generated.h"
class ULyraGameplayAbility_Jump;
UCLASS()
class UUEPNativeLifecycleFixture : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable)
    static bool ProbeJumpAdmission(ULyraGameplayAbility_Jump* Ability, bool bActorInfo, bool bAvatar);
};
