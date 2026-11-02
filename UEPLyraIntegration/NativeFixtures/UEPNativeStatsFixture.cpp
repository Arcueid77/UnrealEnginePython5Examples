#include "UEPNativeStatsFixture.h"
#include "Inventory/LyraInventoryItemInstance.h"
#include "UObject/UnrealType.h"
#include UE_INLINE_GENERATED_CPP_BY_NAME(UEPNativeStatsFixture)

UInventoryFragment_SetStats* UUEPNativeStatsFixture::ConfigureDefinition(UClass* DefinitionClass, const TArray<FUEPInitialItemStat>& Rows)
{
    check(DefinitionClass && DefinitionClass->IsChildOf(ULyraInventoryItemDefinition::StaticClass()));
    ULyraInventoryItemDefinition* Definition = CastChecked<ULyraInventoryItemDefinition>(DefinitionClass->GetDefaultObject());
    UInventoryFragment_SetStats* Fragment = NewObject<UInventoryFragment_SetStats>(Definition);
    FMapProperty* Property = FindFProperty<FMapProperty>(UInventoryFragment_SetStats::StaticClass(), TEXT("InitialItemStats"));
    check(Property);
    TMap<FGameplayTag, int32>* Map = Property->ContainerPtrToValuePtr<TMap<FGameplayTag, int32>>(Fragment);
    for (const FUEPInitialItemStat& Row : Rows) { Map->Add(Row.Tag, Row.Count); }
    Definition->Fragments = { Fragment };
    return Fragment;
}

void UUEPNativeStatsFixture::ApplyWithoutDefinition(const UInventoryFragment_SetStats* Fragment, ULyraInventoryItemInstance* Instance)
{
    check(Fragment && Instance && !Instance->GetItemDef());
    Fragment->OnInstanceCreated(Instance);
}
