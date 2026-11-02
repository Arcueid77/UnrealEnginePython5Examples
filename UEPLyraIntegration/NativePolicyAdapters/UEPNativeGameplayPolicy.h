#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "UEPNativeGameplayPolicy.generated.h"

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativePolicyContext : public UObject
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) FName Operation;
    UPROPERTY(BlueprintReadWrite) bool bCompleted = false;
};

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativeResetPolicyContext : public UUEPNativePolicyContext
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) bool bHasCharacter = false;
    UPROPERTY(BlueprintReadWrite) TArray<FName> Actions;
};

UCLASS(Blueprintable)
class LYRAGAME_API UUEPNativeGameplayPolicy : public UObject
{
    GENERATED_BODY()
public:
    virtual UWorld* GetWorld() const override;
    UFUNCTION(BlueprintNativeEvent, BlueprintPure)
    bool UEPUsesPythonPolicy(FName Operation) const;
    UFUNCTION(BlueprintNativeEvent)
    void UEPApplyPolicy(UUEPNativePolicyContext* Context) const;
    UFUNCTION(BlueprintNativeEvent)
    UObject* UEPChooseObject(FName Operation, UObject* Primary, UObject* Secondary) const;
};

UCLASS()
class LYRAGAME_API UUEPNativeGameplayPolicySubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, meta=(WorldContext="WorldContext"))
    static UUEPNativeGameplayPolicy* GetPolicyForContext(UObject* WorldContext);
    UUEPNativeGameplayPolicy* GetPolicy();
private:
    UPROPERTY(Transient) TObjectPtr<UUEPNativeGameplayPolicy> Policy;
};
