#include "UEPNativeWorldPolicies.h"
#include "Camera/LyraCameraMode.h"
#include "Character/LyraHeroComponent.h"
#include "Cosmetics/LyraControllerComponent_CharacterParts.h"
#include "UI/Frontend/LyraFrontendStateComponent.h"
#include "CommonUserSubsystem.h"
#include "ControlFlow.h"
#include "Kismet/GameplayStatics.h"
#include UE_INLINE_GENERATED_CPP_BY_NAME(UEPNativeWorldPolicies)

TStrongObjectPtr<UUEPNativeFrontendPolicyContext> UEPMakeFrontendContext(UObject* Owner, FName Operation)
{
    UUEPNativeGameplayPolicy* Host = UUEPNativeGameplayPolicySubsystem::GetPolicyForContext(Owner);
    if (!Host || !Host->UEPUsesPythonPolicy(Operation)) { return TStrongObjectPtr<UUEPNativeFrontendPolicyContext>(); }
    TStrongObjectPtr<UUEPNativeFrontendPolicyContext> Context(NewObject<UUEPNativeFrontendPolicyContext>(Host));
    Context->Operation = Operation;
    return Context;
}

bool UEPApplyWorldPolicy(UUEPNativePolicyContext* Context)
{
    check(Context);
    CastChecked<UUEPNativeGameplayPolicy>(Context->GetOuter())->UEPApplyPolicy(Context);
    if (!Context->bCompleted)
    {
        // Script failure is already logged by the router. Reject incomplete
        // output without an engine ensure or replaying the native policy.
        UE_LOG(LogTemp, Warning, TEXT("UEP_NATIVE_POLICY_ABORTED: %s"), *Context->Operation.ToString());
        return false;
    }
    return true;
}

static TArray<FUEPNativeCharacterPartPolicyRow> UEPPartRows(const TArray<FLyraControllerCharacterPartEntry>& Entries, const FLyraCharacterPart* EquivalentTo)
{
    TArray<FUEPNativeCharacterPartPolicyRow> Rows;
    for (int32 Index = 0; Index < Entries.Num(); ++Index)
    {
        const FLyraControllerCharacterPartEntry& Entry = Entries[Index];
        FUEPNativeCharacterPartPolicyRow& Row = Rows.AddDefaulted_GetRef();
        Row.Index = Index; Row.Source = static_cast<int32>(Entry.Source); Row.bHandleValid = Entry.Handle.IsValid();
        Row.bEquivalent = EquivalentTo && FLyraCharacterPart::AreEquivalentParts(Entry.Part, *EquivalentTo);
        Row.PartClass = Entry.Part.PartClass.Get();
    }
    return Rows;
}

bool UEPSelectCharacterPartIndices(UObject* Owner, FName Operation, bool bHasCustomizer, const TArray<FLyraControllerCharacterPartEntry>& Entries, const FLyraCharacterPart* EquivalentTo, bool bSuppressed, TArray<int32>& OutIndices)
{
    UUEPNativeGameplayPolicy* Host = UUEPNativeGameplayPolicySubsystem::GetPolicyForContext(Owner);
    if (!Host || !Host->UEPUsesPythonPolicy(Operation)) { return false; }
    TStrongObjectPtr<UUEPNativeCharacterPartPolicyContext> Context(NewObject<UUEPNativeCharacterPartPolicyContext>(Host));
    Context->Operation = Operation; Context->bHasCustomizer = bHasCustomizer; Context->bSuppressed = bSuppressed;
    Context->Entries = UEPPartRows(Entries, EquivalentTo);
    if (UEPApplyWorldPolicy(Context.Get()))
    {
        TSet<int32> Seen;
        for (int32 Index : Context->Indices)
        {
            if (!ensureMsgf(Entries.IsValidIndex(Index) && !Seen.Contains(Index), TEXT("Invalid or duplicate Python character-part index"))) { OutIndices.Reset(); return true; }
            Seen.Add(Index);
        }
        OutIndices = Context->Indices;
    }
    return true;
}

TSubclassOf<ULyraCameraMode> UUEPNativeWorldPolicyFixture::CameraChoice(ULyraHeroComponent* Hero) { return Hero ? Hero->DetermineCameraMode() : nullptr; }
void UUEPNativeWorldPolicyFixture::SetCamera(ULyraHeroComponent* Hero, TSubclassOf<ULyraCameraMode> Mode, FGameplayAbilitySpecHandle Handle) { check(Hero); Hero->SetAbilityCameraMode(Mode, Handle); }
void UUEPNativeWorldPolicyFixture::ClearCamera(ULyraHeroComponent* Hero, FGameplayAbilitySpecHandle Handle) { check(Hero); Hero->ClearAbilityCameraMode(Handle); }
TArray<FUEPNativeCharacterPartPolicyRow> UUEPNativeWorldPolicyFixture::PartRows(ULyraControllerComponent_CharacterParts* Parts) { return Parts ? UEPPartRows(Parts->CharacterParts, nullptr) : TArray<FUEPNativeCharacterPartPolicyRow>(); }
void UUEPNativeWorldPolicyFixture::AddSourcePart(ULyraControllerComponent_CharacterParts* Parts, FLyraCharacterPart Part, int32 Source) { check(Parts && Source >= 0 && Source <= 3); Parts->AddCharacterPartInternal(Part, static_cast<ECharacterPartSource>(Source)); }
void UUEPNativeWorldPolicyFixture::SuppressParts(ULyraControllerComponent_CharacterParts* Parts, bool bSuppress) { check(Parts); Parts->SetSuppressionOnNaturalParts(bSuppress); }
void UUEPNativeWorldPolicyFixture::NotifyPossession(ULyraControllerComponent_CharacterParts* Parts, APawn* OldPawn, APawn* NewPawn) { check(Parts); Parts->OnPossessedPawnChanged(OldPawn, NewPawn); }
bool UUEPNativeWorldPolicyFixture::FrontendLoading(ULyraFrontendStateComponent* Frontend) { FString Reason; return Frontend && Frontend->ShouldShowLoadingScreen(Reason); }
bool UUEPNativeWorldPolicyFixture::UserInitializationCallback(ULyraFrontendStateComponent* Frontend, bool bSuccess)
{
    check(Frontend && !Frontend->InProgressPressStartScreen.IsValid());
    bool bContinued = false;
    TSharedRef<FControlFlow> Flow = MakeShared<FControlFlow>(TEXT("UEP owned initialization callback"));
    Flow->QueueWait().BindLambda([Frontend](FControlFlowNodeRef Node) { Frontend->InProgressPressStartScreen = Node; });
    Flow->QueueFunction().BindLambda([&bContinued]() { bContinued = true; });
    Flow->ExecuteFlow();
    UCommonUserSubsystem* Users = UGameplayStatics::GetGameInstance(Frontend)->GetSubsystem<UCommonUserSubsystem>();
    check(Users);
    Users->OnUserInitializeComplete.AddDynamic(Frontend, &ULyraFrontendStateComponent::OnUserInitialized);
    Frontend->OnUserInitialized(nullptr, bSuccess, FText(), ECommonUserPrivilege::CanPlay, ECommonUserOnlineContext::Default);
    return bContinued && !Frontend->InProgressPressStartScreen.IsValid() && !Users->OnUserInitializeComplete.IsAlreadyBound(Frontend, &ULyraFrontendStateComponent::OnUserInitialized);
}
