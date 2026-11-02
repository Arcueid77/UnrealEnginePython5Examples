#pragma once
#include "UEPNativeGameplayPolicy.h"
#include "Cosmetics/LyraCharacterPartTypes.h"
#include "GameplayAbilitySpecHandle.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "UObject/StrongObjectPtr.h"
#include "UEPNativeWorldPolicies.generated.h"
class ULyraHeroComponent;
class ULyraCameraMode;
class ULyraFrontendStateComponent;
class ULyraControllerComponent_CharacterParts;
class APawn;
struct FLyraControllerCharacterPartEntry;

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativeFrontendPolicyContext : public UUEPNativePolicyContext
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) bool bHardDisconnect = false;
    UPROPERTY(BlueprintReadOnly) bool bHasUser = false;
    UPROPERTY(BlueprintReadOnly) bool bHasSession = false;
    UPROPERTY(BlueprintReadOnly) bool bLoggedIn = false;
    UPROPERTY(BlueprintReadOnly) bool bWaitForStart = false;
    UPROPERTY(BlueprintReadOnly) bool bHasRootLayout = false;
    UPROPERTY(BlueprintReadOnly) bool bRequestedSession = false;
    UPROPERTY(BlueprintReadOnly) bool bCanJoin = false;
    UPROPERTY(BlueprintReadOnly) bool bSuccess = false;
    UPROPERTY(BlueprintReadOnly) bool bWidgetReady = false;
    UPROPERTY(BlueprintReadOnly) bool bWidgetCanceled = false;
    UPROPERTY(BlueprintReadWrite) TArray<FName> Actions;
};

USTRUCT(BlueprintType)
struct FUEPNativeCharacterPartPolicyRow
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) int32 Index = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) int32 Source = 0;
    UPROPERTY(BlueprintReadOnly) bool bHandleValid = false;
    UPROPERTY(BlueprintReadOnly) bool bEquivalent = false;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<UClass> PartClass = nullptr;
};

UCLASS(BlueprintType)
class LYRAGAME_API UUEPNativeCharacterPartPolicyContext : public UUEPNativePolicyContext
{
    GENERATED_BODY()
public:
    UPROPERTY(BlueprintReadOnly) bool bHasCustomizer = false;
    UPROPERTY(BlueprintReadOnly) bool bSuppressed = false;
    UPROPERTY(BlueprintReadOnly) TArray<FUEPNativeCharacterPartPolicyRow> Entries;
    UPROPERTY(BlueprintReadWrite) TArray<int32> Indices;
};

LYRAGAME_API TStrongObjectPtr<UUEPNativeFrontendPolicyContext> UEPMakeFrontendContext(UObject* Owner, FName Operation);
LYRAGAME_API bool UEPApplyWorldPolicy(UUEPNativePolicyContext* Context);
LYRAGAME_API bool UEPSelectCharacterPartIndices(UObject* Owner, FName Operation, bool bHasCustomizer, const TArray<FLyraControllerCharacterPartEntry>& Entries, const FLyraCharacterPart* EquivalentTo, bool bSuppressed, TArray<int32>& OutIndices);

UCLASS()
class UUEPNativeWorldPolicyFixture : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable) static TSubclassOf<ULyraCameraMode> CameraChoice(ULyraHeroComponent* Hero);
    UFUNCTION(BlueprintCallable) static void SetCamera(ULyraHeroComponent* Hero, TSubclassOf<ULyraCameraMode> Mode, FGameplayAbilitySpecHandle Handle);
    UFUNCTION(BlueprintCallable) static void ClearCamera(ULyraHeroComponent* Hero, FGameplayAbilitySpecHandle Handle);
    UFUNCTION(BlueprintCallable) static TArray<FUEPNativeCharacterPartPolicyRow> PartRows(ULyraControllerComponent_CharacterParts* Parts);
    UFUNCTION(BlueprintCallable) static void AddSourcePart(ULyraControllerComponent_CharacterParts* Parts, FLyraCharacterPart Part, int32 Source);
    UFUNCTION(BlueprintCallable) static void SuppressParts(ULyraControllerComponent_CharacterParts* Parts, bool bSuppress);
    UFUNCTION(BlueprintCallable) static void NotifyPossession(ULyraControllerComponent_CharacterParts* Parts, APawn* OldPawn, APawn* NewPawn);
    UFUNCTION(BlueprintCallable) static bool FrontendLoading(ULyraFrontendStateComponent* Frontend);
    UFUNCTION(BlueprintCallable) static bool UserInitializationCallback(ULyraFrontendStateComponent* Frontend, bool bSuccess);
};
