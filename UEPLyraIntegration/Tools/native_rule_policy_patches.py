"""Remaining six native rule families; SDK, transport and async owners stay native."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha
from native_lifecycle_patches import replace_function,original_function_body
from native_escape_patches import sources as escape_sources


def prepend(text,signature,prefix):return replace_function(text,signature,prefix+original_function_body(text,signature))


def device(text):
    old='''\tif (PlatformUserId != OwningLocalPlayerId)'''
    new='''    bool UEPNotify = PlatformUserId == OwningLocalPlayerId;
    if (auto Context = UEPMakeRuleContext<UUEPNativeDevicePolicyContext>(this, TEXT("Device.Connection")))
    {
        Context->OwnerUser = OwningLocalPlayerId.GetInternalId(); Context->ChangedUser = PlatformUserId.GetInternalId();
        if (!UEPApplyWorldPolicy(Context.Get())) { return; } UEPNotify = Context->bAct;
    }
    if (!UEPNotify)'''
    assert old in text;text=text.replace(old,new,1)
    old='''\tif (NewUserPlatformId == OwningLocalPlayerId || OldUserPlatformId == OwningLocalPlayerId)'''
    new='''    bool UEPNotify = NewUserPlatformId == OwningLocalPlayerId || OldUserPlatformId == OwningLocalPlayerId;
    if (auto Context = UEPMakeRuleContext<UUEPNativeDevicePolicyContext>(this, TEXT("Device.Pairing")))
    {
        Context->OwnerUser = OwningLocalPlayerId.GetInternalId(); Context->NewUser = NewUserPlatformId.GetInternalId(); Context->OldUser = OldUserPlatformId.GetInternalId();
        if (!UEPApplyWorldPolicy(Context.Get())) { return; } UEPNotify = Context->bAct;
    }
    if (UEPNotify)'''
    assert old in text;text=text.replace(old,new,1)
    text=text.replace('\t// Check the tags that we may be emulating in the editor too','    const bool UEPPlatformTraits = bHasAllRequiredTags;\n    bool UEPEditorTraits = false;\n\t// Check the tags that we may be emulating in the editor too',1)
    text=text.replace('bHasAllRequiredTags |= PlatformEmulationTags.HasAll(PlatformRequiresControllerDisconnectScreen);','UEPEditorTraits = PlatformEmulationTags.HasAll(PlatformRequiresControllerDisconnectScreen);\n    bHasAllRequiredTags |= UEPEditorTraits;',1)
    text=text.replace('\treturn bHasAllRequiredTags;','''    if (auto Context = UEPMakeRuleContext<UUEPNativeDevicePolicyContext>(GetWorld(), TEXT("Device.Platform")))
    {
        Context->bPlatformTraits = UEPPlatformTraits; Context->bEditorTraits = UEPEditorTraits;
        if (UEPApplyWorldPolicy(Context.Get())) { return Context->bAct; } return false;
    }
\treturn bHasAllRequiredTags;''',1)
    old='''\tif (!RequestProcessControllerStateHandle.IsValid())''';new='''    bool UEPSchedule = !RequestProcessControllerStateHandle.IsValid();
    if (auto Context = UEPMakeRuleContext<UUEPNativeDevicePolicyContext>(this, TEXT("Device.Schedule")))
    {
        Context->bPendingProcess = RequestProcessControllerStateHandle.IsValid();
        if (!UEPApplyWorldPolicy(Context.Get())) { return; } UEPSchedule = Context->bAct;
    }
    if (UEPSchedule)'''
    assert old in text;text=text.replace(old,new,1)
    marker='''    // Check if there are any other connected GAMEPAD devices mapped to this platform user.'''
    prefix='''    if (auto Context = UEPMakeRuleContext<UUEPNativeDevicePolicyContext>(this, TEXT("Device.Process")))
    {
        Context->OwnerUser = OwningLocalPlayerId.GetInternalId(); Context->bScreenPresent = SpawnedControllerDisconnectScreen != nullptr;
        for (FInputDeviceId Device : MappedInputDevices)
        {
            FUEPNativeInputDeviceRow& Row = Context->Devices.AddDefaulted_GetRef(); Row.DeviceId = Device.GetId();
            Row.bConnected = DeviceMapper.GetInputDeviceConnectionState(Device) == EInputDeviceConnectionState::Connected;
            Row.bGamepad = Row.bConnected && UInputDeviceSubsystem::Get()->GetInputDeviceHardwareIdentifier(Device).PrimaryDeviceType == EHardwareDevicePrimaryType::Gamepad;
        }
        if (!UEPApplyWorldPolicy(Context.Get())) { return; }
        if (Context->Action == TEXT("Show")) { DisplayControllerDisconnectedMenu(); }
        else if (Context->Action == TEXT("Hide")) { HideControllerDisconnectedMenu(); }
        else { ensure(Context->Action == TEXT("None")); }
        return;
    }
'''
    assert marker in text;return text.replace(marker,prefix+marker,1)


def replay(text):
    old='''\tif (LocalPlayer != nullptr && LocalPlayerDeletingReplays == nullptr && NumReplaysToKeep != 0)'''
    new='''    bool UEPStart = LocalPlayer != nullptr && LocalPlayerDeletingReplays == nullptr && NumReplaysToKeep != 0;
    if (auto Context = UEPMakeRuleContext<UUEPNativeReplayPolicyContext>(this, TEXT("Replay.Start")))
    {
        Context->bHasLocalPlayer = LocalPlayer != nullptr; Context->bBusy = LocalPlayerDeletingReplays != nullptr; Context->NumberToKeep = NumReplaysToKeep;
        if (!UEPApplyWorldPolicy(Context.Get())) { return; } UEPStart = Context->bAct;
    }
    if (UEPStart)'''
    assert old in text;text=text.replace(old,new,1)
    signature='void ULyraReplaySubsystem::OnEnumerateStreamsCompleteForDelete('
    prefix='''    if (auto Context = UEPMakeRuleContext<UUEPNativeReplayPolicyContext>(this, TEXT("Replay.Select")))
    {
        Context->bHasLocalPlayer = IsValid(LocalPlayerDeletingReplays); Context->bHasStreamer = CurrentReplayStreamer.IsValid(); Context->NumberToKeep = DeletingReplaysNumberToKeep;
        if (!Context->bHasLocalPlayer || !Context->bHasStreamer) { return; }
        UDemoNetDriver* Driver = GetDemoDriver(); Context->bRecording = Driver && Driver->IsRecording();
        // Native sorting preserves the original engine's tie order. Python
        // filters keep flags and selects one deletion from this typed snapshot.
        TArray<FNetworkReplayStreamInfo> Ordered = Result.FoundStreams;
        Algo::SortBy(Ordered, [](const FNetworkReplayStreamInfo& Info) { return Info.Timestamp.GetTicks(); }, TGreater<>());
        for (int32 Index = 0; Index < Ordered.Num(); ++Index)
        {
            const FNetworkReplayStreamInfo& Info = Ordered[Index];
            FUEPNativeReplayPolicyRow& Row = Context->Streams.AddDefaulted_GetRef();
            Row.Index = Index; Row.Name = Info.Name; Row.TimestampTicks = Info.Timestamp.GetTicks(); Row.bShouldKeep = Info.bShouldKeep; Row.bIsLive = Info.bIsLive;
        }
        if (!UEPApplyWorldPolicy(Context.Get())) { return; }
        if (Context->DeleteIndex != INDEX_NONE)
        {
            if (!ensure(Ordered.IsValidIndex(Context->DeleteIndex))) { return; }
            const FNetworkReplayStreamInfo& Info = Ordered[Context->DeleteIndex];
            if (!ensure(!Info.bShouldKeep && !Info.bIsLive)) { return; }
            CurrentReplayStreamer->DeleteFinishedStream(Info.Name, LocalPlayerDeletingReplays->GetPlatformUserIndex(), FDeleteFinishedStreamCallback::CreateUObject(this, &ThisClass::OnDeleteReplay));
        }
        else { CurrentReplayStreamer = nullptr; LocalPlayerDeletingReplays = nullptr; DeletingReplaysNumberToKeep = 0; }
        return;
    }
'''
    text=prepend(text,signature,prefix)
    old='''\tif (DeleteResult.WasSuccessful())''';new='''    bool UEPRepeat = DeleteResult.WasSuccessful();
    if (auto Context = UEPMakeRuleContext<UUEPNativeReplayPolicyContext>(this, TEXT("Replay.Deleted")))
    {
        Context->bDeleteSucceeded = DeleteResult.WasSuccessful();
        if (!UEPApplyWorldPolicy(Context.Get())) { return; } UEPRepeat = Context->bAct;
    }
    if (UEPRepeat)'''
    assert old in text;return text.replace(old,new,1)


def audio(text):
    signature='void ULyraAudioMixEffectsSubsystem::ApplyDynamicRangeEffectsChains('
    body=original_function_body(text,signature);start=body.index('\t// If HDR Audio is selected');end=body.index('\t// Override submixes')
    native=body[start:end]
    replacement='''    if (auto Context = UEPMakeRuleContext<UUEPNativeAudioPolicyContext>(this, TEXT("Audio.DynamicRange")))
    {
        Context->bHDR = bHDRAudio;
        for (const auto& Chain : HDRSubmixEffectChain) { Context->HDRSubmixes.Add(Chain.Submix.Get()); }
        for (const auto& Chain : LDRSubmixEffectChain) { Context->LDRSubmixes.Add(Chain.Submix.Get()); }
        if (!UEPApplyWorldPolicy(Context.Get())) { return; }
        const TArray<FLyraAudioSubmixEffectsChain>& Apply = bHDRAudio ? HDRSubmixEffectChain : LDRSubmixEffectChain;
        const TArray<FLyraAudioSubmixEffectsChain>& Clear = bHDRAudio ? LDRSubmixEffectChain : HDRSubmixEffectChain;
        for (int32 Index : Context->ApplyIndices) { if (!ensure(Apply.IsValidIndex(Index))) { return; } AudioSubmixEffectsChainToApply.Add(Apply[Index]); }
        for (int32 Index : Context->ClearIndices) { if (!ensure(Clear.IsValidIndex(Index))) { return; } SubmixesLeftToClear.Add(Clear[Index].Submix); }
    }
    else
    {
'''+native.replace('\tTArray<USoundSubmix*> SubmixesLeftToClear;','')+'''    }
'''
    body=body[:start]+'    TArray<USoundSubmix*> SubmixesLeftToClear;\n'+replacement+body[end:]
    text=replace_function(text,signature,body)
    old='''\tif (bAppliedLoadingScreenMix != bWantsLoadingScreenMix && LoadingScreenMix && World)'''
    new='''    bool UEPChange = bAppliedLoadingScreenMix != bWantsLoadingScreenMix && LoadingScreenMix && World;
    if (auto Context = UEPMakeRuleContext<UUEPNativeAudioPolicyContext>(this, TEXT("Audio.Loading")))
    {
        Context->bAppliedLoading = bAppliedLoadingScreenMix; Context->bWantsLoading = bWantsLoadingScreenMix; Context->bHasMix = LoadingScreenMix != nullptr; Context->bHasWorld = World != nullptr;
        if (!UEPApplyWorldPolicy(Context.Get())) { return; } UEPChange = Context->bAct;
    }
    if (UEPChange)'''
    assert old in text;return text.replace(old,new,1)


def damage(text):
    signature='bool ULyraTeamSubsystem::CanCauseDamage('
    prefix='''    if (auto Context = UEPMakeRuleContext<UUEPNativeDamagePolicyContext>(GetWorld(), TEXT("Damage.CanCause")))
    {
        Context->bAllowSelf = bAllowDamageToSelf; Context->bSameObject = Instigator == Target;
        Context->bSamePlayerState = FindPlayerStateFromActor(Cast<AActor>(Instigator)) == FindPlayerStateFromActor(Cast<AActor>(Target));
        if (!(bAllowDamageToSelf && (Context->bSameObject || Context->bSamePlayerState)))
        {
            int32 InstigatorTeam = INDEX_NONE, TargetTeam = INDEX_NONE;
            const ELyraTeamComparison Relationship = CompareTeams(Instigator, Target, InstigatorTeam, TargetTeam);
            Context->bDifferentTeams = Relationship == ELyraTeamComparison::DifferentTeams;
            Context->bInvalidRelationship = Relationship == ELyraTeamComparison::InvalidArgument;
            Context->bInstigatorHasTeam = InstigatorTeam != INDEX_NONE;
            if (Context->bInvalidRelationship && Context->bInstigatorHasTeam) { Context->bTargetHasASC = UAbilitySystemGlobals::GetAbilitySystemComponentFromActor(Cast<const AActor>(Target)) != nullptr; }
        }
        if (!UEPApplyWorldPolicy(Context.Get())) { return false; } return Context->bAllowed;
    }
'''
    return prepend(text,signature,prefix)


def attributes(text):
    return prepend(text,'void UTopDownArenaAttributeSet::ClampAttribute(','''    if (auto Context = UEPMakeRuleContext<UUEPNativeAttributePolicyContext>(GetWorld(), TEXT("Attribute.Clamp")))
    {
        Context->Attribute = FName(*Attribute.GetName()); Context->Input = NewValue; Context->BombCapacity = GetBombCapacity();
        if (UEPApplyWorldPolicy(Context.Get())) { NewValue = Context->Result; }
        return;
    }
''')


def pawn(text):
    text=prepend(text,'const ULyraPawnData* ALyraGameMode::GetPawnDataForController(','''    if (auto Context = UEPMakeRuleContext<UUEPNativePawnPolicyContext>(GetWorld(), TEXT("Pawn.Data")))
    {
        if (const ALyraPlayerState* State = InController ? InController->GetPlayerState<ALyraPlayerState>() : nullptr) { Context->PlayerStateData = const_cast<ULyraPawnData*>(State->GetPawnData<ULyraPawnData>()); }
        if (!Context->PlayerStateData)
        {
            check(GameState); ULyraExperienceManagerComponent* Component = GameState->FindComponentByClass<ULyraExperienceManagerComponent>(); check(Component);
            Context->bExperienceLoaded = Component->IsExperienceLoaded();
            if (Context->bExperienceLoaded)
            {
                Context->ExperienceData = const_cast<ULyraPawnData*>(Component->GetCurrentExperienceChecked()->DefaultPawnData.Get());
                if (!Context->ExperienceData) { Context->AssetManagerData = const_cast<ULyraPawnData*>(ULyraAssetManager::Get().GetDefaultPawnData()); }
            }
        }
        if (!UEPApplyWorldPolicy(Context.Get())) { return nullptr; }
        return Cast<ULyraPawnData>(Context->SelectedData.Get());
    }
''')
    text=prepend(text,'UClass* ALyraGameMode::GetDefaultPawnClassForController_Implementation(','''    UUEPNativeGameplayPolicy* Host = UUEPNativeGameplayPolicySubsystem::GetPolicyForContext(GetWorld());
    if (Host && Host->UEPUsesPythonPolicy(TEXT("Pawn.Class")))
    {
        const ULyraPawnData* Data = GetPawnDataForController(InController);
        UClass* Primary = Data ? Data->PawnClass.Get() : nullptr;
        UClass* Secondary = Primary ? nullptr : Super::GetDefaultPawnClassForController_Implementation(InController);
        UClass* Selected = Cast<UClass>(Host->UEPChooseObject(TEXT("Pawn.Class"), Primary, Secondary));
        return ensure(!Selected || Selected->IsChildOf(APawn::StaticClass())) ? Selected : nullptr;
    }
''')
    return prepend(text,'bool ALyraGameMode::ControllerCanRestart(','''    if (auto Context = UEPMakeRuleContext<UUEPNativePawnPolicyContext>(this, TEXT("Pawn.Restart")))
    {
        APlayerController* Player = Cast<APlayerController>(Controller);
        Context->bBaseRestartAllowed = Player ? Super::PlayerCanRestart_Implementation(Player) : Controller && !Controller->IsPendingKillPending();
        if (Context->bBaseRestartAllowed)
        {
            ULyraPlayerSpawningManagerComponent* Manager = GameState->FindComponentByClass<ULyraPlayerSpawningManagerComponent>();
            Context->bHasSpawningManager = Manager != nullptr;
            Context->bManagerRestartAllowed = Manager && Manager->ControllerCanRestart(Controller);
        }
        if (!UEPApplyWorldPolicy(Context.Get())) { return false; } return Context->bAllowed;
    }
''')


def sources():
    escaped={r['relative']:r['after'] for r in escape_sources()}
    rows=[]
    for relative,transform in (
        ('Source/LyraGame/UI/LyraHUDLayout.cpp',device),
        ('Source/LyraGame/Replays/LyraReplaySubsystem.cpp',replay),
        ('Source/LyraGame/Audio/LyraAudioMixEffectsSubsystem.cpp',audio),
        ('Source/LyraGame/Teams/LyraTeamSubsystem.cpp',damage),
        ('Source/LyraGame/GameModes/LyraGameMode.cpp',pawn),
        ('Plugins/GameFeatures/TopDownArena/Source/TopDownArenaRuntime/Private/TopDownArenaAttributeSet.cpp',attributes)):
        before=escaped.get(relative) or (REFERENCE/relative).read_text();after=transform(before)
        after=after.replace('#include UE_INLINE_GENERATED_CPP_BY_NAME(', '#include "UEPPolicy/UEPNativeRulePolicies.h"\n#include UE_INLINE_GENERATED_CPP_BY_NAME(',1)
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(REFERENCE/relative)))
    for suffix in ('.h','.cpp'):
        p=REPO/'Demos/UEPLyraIntegration/NativePolicyAdapters'/('UEPNativeRulePolicies'+suffix)
        rows.append(dict(relative='Source/LyraGame/UEPPolicy/'+p.name,before='',after=p.read_text(),original_sha256=None,source=str(p)))
    for relative,owner in (('Source/LyraGame/UI/LyraHUDLayout.h','ULyraHUDLayout'),('Source/LyraGame/Replays/LyraReplaySubsystem.h','ULyraReplaySubsystem'),('Source/LyraGame/Audio/LyraAudioMixEffectsSubsystem.h','ULyraAudioMixEffectsSubsystem')):
        before=escaped.get(relative) or (REFERENCE/relative).read_text();start=before.index('class '+owner+' :');body=before.index('GENERATED_BODY()',start)
        after=before[:body]+before[body:].replace('GENERATED_BODY()','GENERATED_BODY()\n\tfriend class UUEPNativeRuleFixture;',1)
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(REFERENCE/relative)))
    return rows


def patch_text():return ''.join(line if line.endswith('\n') else line+'\n' for r in sources() for line in difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'] if r['before'] else '/dev/null',tofile='b/'+r['relative']))


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve()
    if not stage.is_relative_to(REPO/'.build/LyraValidation/CppGameplayExtended') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned stage and fresh rule patch output required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP19-24-rule-policies.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned rule patch differs')
    rows=sources()
    for row in rows:
        p=stage/row['relative']
        if (p.read_text(encoding='utf-8-sig') if p.exists() else '') not in (row['before'],row['after']):raise ValueError('Unrelated rule source: '+row['relative'])
    output.mkdir(parents=True);records=[]
    for row in rows:
        p=stage/row['relative'];p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():
            backup=output/'PreviousSources'/row['relative'];backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(p.read_bytes())
        p.write_text(row['after'],encoding='utf-8',newline='\n');records.append(dict(path=str(p),original=str(REFERENCE/row['relative']) if row['original_sha256'] else None,original_sha256=row['original_sha256'],patched_sha256=sha(p)))
    result=dict(status='patched_requires_native_build',sources=records,escape_policy_seam_preserved=True,runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(apply(a.stage,a.output),indent=2))
