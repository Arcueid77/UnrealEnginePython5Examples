#include "UEPNativeGameplayPolicy.h"
#include "Engine/World.h"
#include "Misc/PackageName.h"
#include UE_INLINE_GENERATED_CPP_BY_NAME(UEPNativeGameplayPolicy)

UWorld* UUEPNativeGameplayPolicy::GetWorld() const
{
    return HasAnyFlags(RF_ClassDefaultObject) || !GetOuter() ? nullptr : GetOuter()->GetWorld();
}
bool UUEPNativeGameplayPolicy::UEPUsesPythonPolicy_Implementation(FName Operation) const { return false; }
void UUEPNativeGameplayPolicy::UEPApplyPolicy_Implementation(UUEPNativePolicyContext* Context) const {}
UObject* UUEPNativeGameplayPolicy::UEPChooseObject_Implementation(FName Operation, UObject* Primary, UObject* Secondary) const { return nullptr; }
UUEPNativeGameplayPolicy* UUEPNativeGameplayPolicySubsystem::GetPolicyForContext(UObject* WorldContext)
{
    UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
    if (!World || World->bIsTearingDown) { return nullptr; }
    UUEPNativeGameplayPolicySubsystem* Subsystem = World ? World->GetSubsystem<UUEPNativeGameplayPolicySubsystem>() : nullptr;
    return Subsystem ? Subsystem->GetPolicy() : nullptr;
}
UUEPNativeGameplayPolicy* UUEPNativeGameplayPolicySubsystem::GetPolicy()
{
    if (!Policy && FPackageName::DoesPackageExist(TEXT("/Game/UEPNative/BP_GlobalGameplayPolicy")))
    {
        if (UClass* Class = LoadClass<UUEPNativeGameplayPolicy>(nullptr, TEXT("/Game/UEPNative/BP_GlobalGameplayPolicy.BP_GlobalGameplayPolicy_C")))
        {
            Policy = NewObject<UUEPNativeGameplayPolicy>(this, Class);
        }
    }
    return Policy;
}
