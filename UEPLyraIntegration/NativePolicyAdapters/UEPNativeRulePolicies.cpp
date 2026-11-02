#include "UEPNativeRulePolicies.h"
#include "AbilitySystemComponent.h"
#include "Audio/LyraAudioMixEffectsSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameModes/LyraGameMode.h"
#include "Character/LyraPawnData.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Guid.h"
#include "Modules/ModuleManager.h"
#include "Replays/LyraReplaySubsystem.h"
#include "Teams/LyraTeamSubsystem.h"
#include "UI/LyraHUDLayout.h"
#include UE_INLINE_GENERATED_CPP_BY_NAME(UEPNativeRulePolicies)

FGameplayTagContainer UUEPNativeRuleFixture::EnableDeviceFixture(ULyraHUDLayout* Layout)
{
    check(Layout); const FGameplayTagContainer Original = Layout->PlatformRequiresControllerDisconnectScreen;
    Layout->PlatformRequiresControllerDisconnectScreen.Reset(); return Original;
}
void UUEPNativeRuleFixture::RestoreDeviceFixture(ULyraHUDLayout* Layout, FGameplayTagContainer Tags)
{
    check(Layout && !Layout->RequestProcessControllerStateHandle.IsValid());
    if (Layout->SpawnedControllerDisconnectScreen) { Layout->HideControllerDisconnectedMenu(); }
    Layout->PlatformRequiresControllerDisconnectScreen = MoveTemp(Tags);
}
bool UUEPNativeRuleFixture::DeviceEvent(ULyraHUDLayout* Layout, int32 Case)
{
    check(Layout && Layout->GetOwningLocalPlayer());
    const FPlatformUserId Owner = Layout->GetOwningLocalPlayer()->GetPlatformUserId();
    const FPlatformUserId Other = FPlatformUserId::CreateFromInternalId(Owner.GetInternalId() + 1);
    const FInputDeviceId Device = FInputDeviceId::CreateFromInternalId(0);
    if (Case < 2) { Layout->HandleInputDeviceConnectionChanged(EInputDeviceConnectionState::Disconnected, Case == 0 ? Owner : Other, Device); }
    else { Layout->HandleInputDevicePairingChanged(Device, Case == 2 ? Owner : Other, Case == 3 ? Owner : Other); }
    return Layout->RequestProcessControllerStateHandle.IsValid();
}
bool UUEPNativeRuleFixture::DevicePending(ULyraHUDLayout* Layout) { return Layout && Layout->RequestProcessControllerStateHandle.IsValid(); }

FUEPNativeReplayFixtureResult UUEPNativeRuleFixture::ReplayRetention(UObject* WorldContext, int32 NumberToKeep)
{
    FUEPNativeReplayFixtureResult Result;
    FString Override;
    check(FParse::Value(FCommandLine::Get(), TEXT("-REPLAYSTREAMEROVERRIDE="), Override) && Override == TEXT("InMemoryNetworkReplayStreaming"));
    INetworkReplayStreamingFactory& Factory = FModuleManager::LoadModuleChecked<INetworkReplayStreamingFactory>(TEXT("InMemoryNetworkReplayStreaming"));
    UGameInstance* Game = UGameplayStatics::GetGameInstance(WorldContext); check(Game && Game->GetFirstGamePlayer());
    ULocalPlayer* Player = Game->GetFirstGamePlayer();
    TSharedPtr<INetworkReplayStreamer> Reader = Factory.CreateReplayStreamer(); check(Reader.IsValid());
    bool bEmpty = false;
    Reader->EnumerateStreams(FNetworkReplayVersion(), Player->GetPlatformUserIndex(), FString(), {}, FEnumerateStreamsCallback::CreateLambda([&bEmpty](const FEnumerateStreamsResult& Found) { bEmpty = Found.FoundStreams.IsEmpty(); }));
    if (!bEmpty) { return Result; }
    const FString Prefix = TEXT("UEP_POLICY_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    for (int32 Index = 0; Index < 4; ++Index)
    {
        TSharedPtr<INetworkReplayStreamer> Stream = Factory.CreateReplayStreamer();
        FStartStreamingParameters Params; Params.CustomName = Prefix + FString::FromInt(Index); Params.FriendlyName = Params.CustomName; Params.bRecord = true; Params.UserIndices.Add(Player->GetPlatformUserIndex());
        bool bStarted = false;
        Stream->StartStreaming(Params, FStartStreamingCallback::CreateLambda([&bStarted](const FStartStreamingResult& Started) { bStarted = Started.WasSuccessful(); }));
        check(bStarted && Stream->GetHeaderArchive());
        uint32 Header = 0x55455031; *Stream->GetHeaderArchive() << Header; Stream->StopStreaming();
        ++Result.Created; FPlatformProcess::SleepNoStats(0.002f);
    }
    TStrongObjectPtr<ULyraReplaySubsystem> Target(NewObject<ULyraReplaySubsystem>(Game));
    Target->CleanupLocalReplays(Player, NumberToKeep);
    TArray<FString> Remaining;
    Reader->EnumerateStreams(FNetworkReplayVersion(), Player->GetPlatformUserIndex(), FString(), {}, FEnumerateStreamsCallback::CreateLambda([&Remaining, &Prefix](const FEnumerateStreamsResult& Found) {
        for (const FNetworkReplayStreamInfo& Info : Found.FoundStreams) { check(Info.Name.StartsWith(Prefix)); Remaining.Add(Info.Name); }
    }));
    Result.Remaining = Remaining.Num(); Result.bTemporaryMemoryStreamsOnly = true;
    // Exercise a genuine failure result from the native temporary streamer.
    Target->CurrentReplayStreamer = Reader; Target->LocalPlayerDeletingReplays = Player; Target->DeletingReplaysNumberToKeep = 2;
    Reader->DeleteFinishedStream(Prefix + TEXT("_missing"), Player->GetPlatformUserIndex(), FDeleteFinishedStreamCallback::CreateUObject(Target.Get(), &ULyraReplaySubsystem::OnDeleteReplay));
    Result.bNativeFailureStopped = !Target->CurrentReplayStreamer.IsValid() && !Target->LocalPlayerDeletingReplays && Target->DeletingReplaysNumberToKeep == 0;
    for (const FString& Name : Remaining)
    {
        bool bDeleted = false;
        Reader->DeleteFinishedStream(Name, Player->GetPlatformUserIndex(), FDeleteFinishedStreamCallback::CreateLambda([&bDeleted](const FDeleteFinishedStreamResult& Deleted) { bDeleted = Deleted.WasSuccessful(); })); check(bDeleted);
    }
    int32 Left = 0;
    Reader->EnumerateStreams(FNetworkReplayVersion(), Player->GetPlatformUserIndex(), FString(), {}, FEnumerateStreamsCallback::CreateLambda([&Left](const FEnumerateStreamsResult& Found) { Left = Found.FoundStreams.Num(); }));
    Result.bCleaned = Left == 0; return Result;
}

void UUEPNativeRuleFixture::AudioLoading(ULyraAudioMixEffectsSubsystem* Audio, bool bWants)
{
    check(Audio); const bool Before = Audio->bAppliedLoadingScreenMix;
    const bool Expected = Before != bWants && Audio->LoadingScreenMix && Audio->GetWorld() ? bWants : Before;
    Audio->ApplyOrRemoveLoadingScreenMix(bWants); check(Audio->bAppliedLoadingScreenMix == Expected);
}
void UUEPNativeRuleFixture::AudioRange(ULyraAudioMixEffectsSubsystem* Audio, bool bHDR)
{
    check(Audio); const auto HDR = Audio->HDRSubmixEffectChain; const auto LDR = Audio->LDRSubmixEffectChain;
    Audio->ApplyDynamicRangeEffectsChains(bHDR);
    check(HDR.Num() == Audio->HDRSubmixEffectChain.Num() && LDR.Num() == Audio->LDRSubmixEffectChain.Num());
    for (int32 Index = 0; Index < HDR.Num(); ++Index) { check(HDR[Index].Submix == Audio->HDRSubmixEffectChain[Index].Submix && HDR[Index].SubmixEffectChain == Audio->HDRSubmixEffectChain[Index].SubmixEffectChain); }
    for (int32 Index = 0; Index < LDR.Num(); ++Index) { check(LDR[Index].Submix == Audio->LDRSubmixEffectChain[Index].Submix && LDR[Index].SubmixEffectChain == Audio->LDRSubmixEffectChain[Index].SubmixEffectChain); }
}
bool UUEPNativeRuleFixture::DamageAllowed(ULyraTeamSubsystem* Teams, UObject* Instigator, UObject* Target, bool bAllowSelf) { check(Teams); return Teams->CanCauseDamage(Instigator, Target, bAllowSelf); }
float UUEPNativeRuleFixture::SetAttributeBase(UAbilitySystemComponent* ASC, FGameplayAttribute Attribute, float Value) { check(ASC); ASC->SetNumericAttributeBase(Attribute, Value); return ASC->GetNumericAttribute(Attribute); }
UObject* UUEPNativeRuleFixture::PawnData(ALyraGameMode* GameMode, AController* Controller) { check(GameMode); return const_cast<ULyraPawnData*>(GameMode->GetPawnDataForController(Controller)); }
bool UUEPNativeRuleFixture::RestartAllowed(ALyraGameMode* GameMode, AController* Controller) { check(GameMode); return GameMode->ControllerCanRestart(Controller); }
