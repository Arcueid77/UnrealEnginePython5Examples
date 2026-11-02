// Disposable validation only; never copied to the distributable Overlay.
#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Inventory/InventoryFragment_SetStats.h"
#include "UEPNativeStatsFixture.generated.h"

UCLASS()
class UUEPNativeStatsFixture : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable)
    static UInventoryFragment_SetStats* ConfigureDefinition(UClass* DefinitionClass, const TArray<FUEPInitialItemStat>& Rows);
    UFUNCTION(BlueprintCallable)
    static void ApplyWithoutDefinition(const UInventoryFragment_SetStats* Fragment, ULyraInventoryItemInstance* Instance);
};
