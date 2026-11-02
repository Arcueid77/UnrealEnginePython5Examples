#pragma once
#include "UEPNativeWorldPolicies.h"
#include "AttributeSet.h"
#include "UEPNativeRulePolicies.generated.h"

template<typename T>
TStrongObjectPtr<T> UEPMakeRuleContext(UObject* Owner, FName Operation)
{
    UUEPNativeGameplayPolicy* Host = UUEPNativeGameplayPolicySubsystem::GetPolicyForContext(Owner);
    if (!Host || !Host->UEPUsesPythonPolicy(Operation)) { return TStrongObjectPtr<T>(); }
    TStrongObjectPtr<T> Context(NewObject<T>(Host));
    Context->Operation = Operation;
    return Context;
}

USTRUCT(BlueprintType)
struct FUEPNativeInputDeviceRow
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) int32 DeviceId = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) bool bConnected = false;
    UPROPERTY(BlueprintReadOnly) bool bGamepad = false;
};

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativeDevicePolicyContext : public UUEPNativePolicyContext
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) int32 OwnerUser = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) int32 ChangedUser = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) int32 NewUser = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) int32 OldUser = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) bool bPlatformTraits = false;
    UPROPERTY(BlueprintReadOnly) bool bEditorTraits = false;
    UPROPERTY(BlueprintReadOnly) bool bPendingProcess = false;
    UPROPERTY(BlueprintReadOnly) bool bScreenPresent = false;
    UPROPERTY(BlueprintReadOnly) TArray<FUEPNativeInputDeviceRow> Devices;
    UPROPERTY(BlueprintReadWrite) bool bAct = false;
    UPROPERTY(BlueprintReadWrite) FName Action;
};

USTRUCT(BlueprintType)
struct FUEPNativeReplayPolicyRow
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) int32 Index = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) FString Name;
    UPROPERTY(BlueprintReadOnly) int64 TimestampTicks = 0;
    UPROPERTY(BlueprintReadOnly) bool bShouldKeep = false;
    UPROPERTY(BlueprintReadOnly) bool bIsLive = false;
};

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativeReplayPolicyContext : public UUEPNativePolicyContext
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) bool bHasLocalPlayer = false;
    UPROPERTY(BlueprintReadOnly) bool bBusy = false;
    UPROPERTY(BlueprintReadOnly) bool bHasStreamer = false;
    UPROPERTY(BlueprintReadOnly) bool bRecording = false;
    UPROPERTY(BlueprintReadOnly) bool bDeleteSucceeded = false;
    UPROPERTY(BlueprintReadOnly) int32 NumberToKeep = 0;
    UPROPERTY(BlueprintReadOnly) TArray<FUEPNativeReplayPolicyRow> Streams;
    UPROPERTY(BlueprintReadWrite) bool bAct = false;
    UPROPERTY(BlueprintReadWrite) int32 DeleteIndex = INDEX_NONE;
};

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativeAudioPolicyContext : public UUEPNativePolicyContext
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) bool bHDR = false;
    UPROPERTY(BlueprintReadOnly) bool bAppliedLoading = false;
    UPROPERTY(BlueprintReadOnly) bool bWantsLoading = false;
    UPROPERTY(BlueprintReadOnly) bool bHasMix = false;
    UPROPERTY(BlueprintReadOnly) bool bHasWorld = false;
    UPROPERTY(BlueprintReadOnly) TArray<TObjectPtr<UObject>> HDRSubmixes;
    UPROPERTY(BlueprintReadOnly) TArray<TObjectPtr<UObject>> LDRSubmixes;
    UPROPERTY(BlueprintReadWrite) TArray<int32> ApplyIndices;
    UPROPERTY(BlueprintReadWrite) TArray<int32> ClearIndices;
    UPROPERTY(BlueprintReadWrite) bool bAct = false;
};

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativeDamagePolicyContext : public UUEPNativePolicyContext
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) bool bAllowSelf = false;
    UPROPERTY(BlueprintReadOnly) bool bSameObject = false;
    UPROPERTY(BlueprintReadOnly) bool bSamePlayerState = false;
    UPROPERTY(BlueprintReadOnly) bool bDifferentTeams = false;
    UPROPERTY(BlueprintReadOnly) bool bInvalidRelationship = false;
    UPROPERTY(BlueprintReadOnly) bool bInstigatorHasTeam = false;
    UPROPERTY(BlueprintReadOnly) bool bTargetHasASC = false;
    UPROPERTY(BlueprintReadWrite) bool bAllowed = false;
};

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativeAttributePolicyContext : public UUEPNativePolicyContext
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) FName Attribute;
    UPROPERTY(BlueprintReadOnly) float Input = 0.f;
    UPROPERTY(BlueprintReadOnly) float BombCapacity = 1.f;
    UPROPERTY(BlueprintReadWrite) float Result = 0.f;
};

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativePawnPolicyContext : public UUEPNativePolicyContext
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) TObjectPtr<UObject> PlayerStateData = nullptr;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<UObject> ExperienceData = nullptr;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<UObject> AssetManagerData = nullptr;
    UPROPERTY(BlueprintReadOnly) bool bExperienceLoaded = false;
    UPROPERTY(BlueprintReadOnly) bool bBaseRestartAllowed = false;
    UPROPERTY(BlueprintReadOnly) bool bHasSpawningManager = false;
    UPROPERTY(BlueprintReadOnly) bool bManagerRestartAllowed = false;
    UPROPERTY(BlueprintReadWrite) TObjectPtr<UObject> SelectedData = nullptr;
    UPROPERTY(BlueprintReadWrite) bool bAllowed = false;
};

class ULyraHUDLayout;
class ULyraReplaySubsystem;
class ULyraAudioMixEffectsSubsystem;
class ULyraTeamSubsystem;
class ALyraGameMode;
class UAbilitySystemComponent;

USTRUCT(BlueprintType)
struct FUEPNativeReplayFixtureResult
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) int32 Created = 0;
    UPROPERTY(BlueprintReadOnly) int32 Remaining = 0;
    UPROPERTY(BlueprintReadOnly) bool bNativeFailureStopped = false;
    UPROPERTY(BlueprintReadOnly) bool bTemporaryMemoryStreamsOnly = false;
    UPROPERTY(BlueprintReadOnly) bool bCleaned = false;
};

UCLASS()
class UUEPNativeRuleFixture : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable) static FGameplayTagContainer EnableDeviceFixture(ULyraHUDLayout* Layout);
    UFUNCTION(BlueprintCallable) static void RestoreDeviceFixture(ULyraHUDLayout* Layout, FGameplayTagContainer Tags);
    UFUNCTION(BlueprintCallable) static bool DeviceEvent(ULyraHUDLayout* Layout, int32 Case);
    UFUNCTION(BlueprintCallable) static bool DevicePending(ULyraHUDLayout* Layout);
    UFUNCTION(BlueprintCallable) static FUEPNativeReplayFixtureResult ReplayRetention(UObject* WorldContext, int32 NumberToKeep);
    UFUNCTION(BlueprintCallable) static void AudioLoading(ULyraAudioMixEffectsSubsystem* Audio, bool bWants);
    UFUNCTION(BlueprintCallable) static void AudioRange(ULyraAudioMixEffectsSubsystem* Audio, bool bHDR);
    UFUNCTION(BlueprintCallable) static bool DamageAllowed(ULyraTeamSubsystem* Teams, UObject* Instigator, UObject* Target, bool bAllowSelf);
    UFUNCTION(BlueprintCallable) static float SetAttributeBase(UAbilitySystemComponent* ASC, FGameplayAttribute Attribute, float Value);
    UFUNCTION(BlueprintCallable) static UObject* PawnData(ALyraGameMode* GameMode, AController* Controller);
    UFUNCTION(BlueprintCallable) static bool RestartAllowed(ALyraGameMode* GameMode, AController* Controller);
};
