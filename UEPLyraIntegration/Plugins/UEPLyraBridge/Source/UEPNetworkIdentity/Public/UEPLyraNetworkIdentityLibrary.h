#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "UEPLyraNetworkIdentityLibrary.generated.h"

/** Read-only wire identity, not a locally generated Actor name or spawn clock. */
USTRUCT(BlueprintType)
struct UEPNETWORKIDENTITY_API FUEPLyraNetworkIdentity
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly) bool bValid = false;
    UPROPERTY(BlueprintReadOnly) FString Transport;
    UPROPERTY(BlueprintReadOnly) FString WireId;
    UPROPERTY(BlueprintReadOnly) FString ObjectPath;
    UPROPERTY(BlueprintReadOnly) FString WorldPath;
    UPROPERTY(BlueprintReadOnly) FString DriverPath;
    UPROPERTY(BlueprintReadOnly) int32 LocalRole = -1;
    UPROPERTY(BlueprintReadOnly) double WorldSeconds = 0.0;
    UPROPERTY(BlueprintReadOnly) float ActorAgeSeconds = -1.0f;
};

/** Existing-id lookup only. Never creates/assigns ids or repairs gameplay state. */
UCLASS()
class UEPNETWORKIDENTITY_API UUEPLyraNetworkIdentityLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintPure, Category="UEP|Lyra|Validation")
    static FUEPLyraNetworkIdentity ReadNetworkIdentity(const UObject* Object);
};
