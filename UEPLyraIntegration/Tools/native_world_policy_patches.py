"""Frontend, controller parts and camera choices; native owners keep lifetimes."""
import argparse
import difflib
import json
from pathlib import Path
from native_team_patches import REPO,REFERENCE,sha
from native_lifecycle_patches import replace_function,original_function_body

HERO_GUARD='''\t\t// Wait for OnRep_PlayerState to select this simulated proxy before
\t\t// binding its persistent ASC. A queued closed channel can briefly
\t\t// spawn a retired pawn after a newer pawn already owns that ASC.
\t\tif (LyraPS && Pawn->GetLocalRole() == ROLE_SimulatedProxy && LyraPS->GetPawn() != Pawn)
\t\t{
\t\t\treturn false;
\t\t}

'''


def frontend(text):
    owner='ULyraFrontendStateComponent::'
    body='''    TArray<FName> Steps = {TEXT("Initialize"),TEXT("PressStart"),TEXT("JoinRequested"),TEXT("Main")};
    if (auto Context = UEPMakeFrontendContext(this, TEXT("Frontend.Plan")))
    {
        if (!UEPApplyWorldPolicy(Context.Get())) { return; }
        Steps = Context->Actions;
    }
    FControlFlow& Flow = FControlFlowStatics::Create(this, TEXT("FrontendFlow"));
    for (FName Step : Steps)
    {
        if (Step == TEXT("Initialize")) { Flow.QueueStep(TEXT("Wait For User Initialization"), this, &ThisClass::FlowStep_WaitForUserInitialization); }
        else if (Step == TEXT("PressStart")) { Flow.QueueStep(TEXT("Try Show Press Start Screen"), this, &ThisClass::FlowStep_TryShowPressStartScreen); }
        else if (Step == TEXT("JoinRequested")) { Flow.QueueStep(TEXT("Try Join Requested Session"), this, &ThisClass::FlowStep_TryJoinRequestedSession); }
        else if (Step == TEXT("Main")) { Flow.QueueStep(TEXT("Try Show Main Screen"), this, &ThisClass::FlowStep_TryShowMainScreen); }
        else { ensureMsgf(false, TEXT("Invalid Python frontend step")); return; }
    }
    Flow.ExecuteFlow();
    FrontEndFlow = Flow.AsShared();'''
    text=replace_function(text,'void '+owner+'OnExperienceLoaded(',body)
    sig='void '+owner+'FlowStep_WaitForUserInitialization('
    before=original_function_body(text,sig)
    prefix='''    if (auto Context = UEPMakeFrontendContext(this, TEXT("Frontend.Initialize")))
    {
        AGameModeBase* GameMode = GetWorld()->GetAuthGameMode<AGameModeBase>();
        UGameInstance* GameInstance = UGameplayStatics::GetGameInstance(this);
        UCommonUserSubsystem* Users = GameInstance->GetSubsystem<UCommonUserSubsystem>();
        UCommonSessionSubsystem* Sessions = GameInstance->GetSubsystem<UCommonSessionSubsystem>();
        Context->bHardDisconnect = ensure(GameMode) && UGameplayStatics::HasOption(GameMode->OptionsString, TEXT("closed"));
        Context->bHasUser = ensure(Users); Context->bHasSession = ensure(Sessions);
        if (!UEPApplyWorldPolicy(Context.Get())) { return; }
        for (FName Action : Context->Actions)
        {
            if (Action == TEXT("ResetUsers") && Users) { Users->ResetUserState(); }
            else if (Action == TEXT("CleanSessions") && Sessions) { Sessions->CleanUpSessions(); }
            else if (Action == TEXT("Continue")) { SubFlow->ContinueFlow(); return; }
            else { ensureMsgf(false, TEXT("Invalid Python frontend initialization action")); return; }
        }
        return;
    }
'''
    text=replace_function(text,sig,prefix+before)
    old='''\tif (const UCommonUserInfo* FirstUser = UserSubsystem->GetUserInfoForLocalPlayerIndex(0))'''
    new='''    const UCommonUserInfo* UEPFirstUser = UserSubsystem->GetUserInfoForLocalPlayerIndex(0);
    const bool UEPLoggedIn = UEPFirstUser && (UEPFirstUser->InitializationState == ECommonUserInitializationState::LoggedInLocalOnly || UEPFirstUser->InitializationState == ECommonUserInitializationState::LoggedInOnline);
    bool UEPAutoLogin = !UEPLoggedIn && !UserSubsystem->ShouldWaitForStartInput();
    bool UEPSkipStart = UEPLoggedIn;
    if (auto Context = UEPMakeFrontendContext(this, TEXT("Frontend.PressStart")))
    {
        Context->bLoggedIn = UEPLoggedIn; Context->bWaitForStart = !UEPAutoLogin;
        Context->bHasRootLayout = UPrimaryGameLayout::GetPrimaryGameLayoutForPrimaryPlayer(this) != nullptr;
        if (!UEPApplyWorldPolicy(Context.Get())) { return; }
        UEPSkipStart = Context->Actions.Contains(TEXT("Continue"));
        UEPAutoLogin = Context->Actions.Contains(TEXT("AutoLogin"));
        if (!UEPSkipStart && !UEPAutoLogin && !Context->Actions.Contains(TEXT("PushStart"))) { return; }
    }
    if (UEPSkipStart) { SubFlow->ContinueFlow(); return; }
    if (false)
    if (const UCommonUserInfo* FirstUser = UserSubsystem->GetUserInfoForLocalPlayerIndex(0))'''
    # Replace the old nested logged-in block completely, avoiding a second read.
    start=text.index(old);opening=text.index('{',start);depth=1;end=opening+1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    new=new[:new.index('    if (false)')]
    text=text[:start]+new+text[end:]
    text=text.replace('if (!UserSubsystem->ShouldWaitForStartInput())','if (UEPAutoLogin)',1)
    # Preserve native async widget creation, weak ownership and flow handles.
    switch='''\t\t\t\t\tswitch (State)'''
    callback='''                    if (auto Context = UEPMakeFrontendContext(this, TEXT("Frontend.StartWidget")))
                    {
                        Context->bWidgetReady = State == EAsyncWidgetLayerState::AfterPush;
                        Context->bWidgetCanceled = State == EAsyncWidgetLayerState::Canceled;
                        if (!UEPApplyWorldPolicy(Context.Get())) { return; }
                        for (FName Action : Context->Actions)
                        {
                            if (Action == TEXT("ClearLoading")) { bShouldShowLoadingScreen = false; }
                            else if (Action == TEXT("WaitForDeactivate")) { Screen->OnDeactivated().AddWeakLambda(this, [SubFlow]() { SubFlow->ContinueFlow(); }); }
                            else if (Action == TEXT("Continue")) { SubFlow->ContinueFlow(); return; }
                            else { ensureMsgf(false, TEXT("Invalid Python start-widget action")); return; }
                        }
                        return;
                    }
'''
    assert switch in text;text=text.replace(switch,callback+switch,1)
    start=text.index('\t\tif (bSuccess)',text.index('void '+owner+'OnUserInitialized('));opening=text.index('{',start);depth=1;end=opening+1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    else_start=text.index('\t\telse',end);opening=text.index('{',else_start);depth=1;end=opening+1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    text=text[:start]+'''        if (auto Context = UEPMakeFrontendContext(this, TEXT("Frontend.UserInitialized")))
        {
            Context->bSuccess = bSuccess;
            if (!UEPApplyWorldPolicy(Context.Get()) || !Context->Actions.Contains(TEXT("Continue"))) { return; }
        }
        FlowToContinue->ContinueFlow();'''+text[end:]
    old='''\tif (GameInstance->GetRequestedSession() != nullptr && GameInstance->CanJoinRequestedSession())'''
    new='''    bool UEPJoin = GameInstance->GetRequestedSession() != nullptr && GameInstance->CanJoinRequestedSession();
    if (auto Context = UEPMakeFrontendContext(this, TEXT("Frontend.JoinRequested")))
    {
        Context->bRequestedSession = GameInstance->GetRequestedSession() != nullptr; Context->bCanJoin = UEPJoin;
        if (!UEPApplyWorldPolicy(Context.Get())) { return; }
        UEPJoin = Context->Actions.Contains(TEXT("Join"));
    }
    if (UEPJoin)'''
    assert old in text;text=text.replace(old,new,1)
    old='''\t\t\t\tif (Result.bWasSuccessful)''';new='''                bool UEPCancel = Result.bWasSuccessful;
                if (auto Context = UEPMakeFrontendContext(this, TEXT("Frontend.JoinResult")))
                {
                    Context->bSuccess = Result.bWasSuccessful;
                    if (!UEPApplyWorldPolicy(Context.Get())) { return; }
                    UEPCancel = Context->Actions.Contains(TEXT("Cancel"));
                }
                if (UEPCancel)'''
    assert old in text;text=text.replace(old,new,1)
    sig='void '+owner+'FlowStep_TryShowMainScreen(';before=original_function_body(text,sig)
    text=replace_function(text,sig,'''    if (auto Context = UEPMakeFrontendContext(this, TEXT("Frontend.Main")))
    {
        Context->bHasRootLayout = UPrimaryGameLayout::GetPrimaryGameLayoutForPrimaryPlayer(this) != nullptr;
        if (!UEPApplyWorldPolicy(Context.Get()) || !Context->Actions.Contains(TEXT("PushMain"))) { return; }
    }
'''+before)
    switch='''\t\t\t\t    switch (State)'''
    assert switch in text
    callback=callback.replace('Frontend.StartWidget','Frontend.MainWidget').replace('else if (Action == TEXT("WaitForDeactivate")) { Screen->OnDeactivated().AddWeakLambda(this, [SubFlow]() { SubFlow->ContinueFlow(); }); }','')
    return text.replace(switch,callback+switch,1)


def parts(text):
    owner='ULyraControllerComponent_CharacterParts::'
    prefixes={
        'AddCharacterPartInternal':'''    FLyraControllerCharacterPartEntry& Entry = CharacterParts.AddDefaulted_GetRef();
    Entry.Part = NewPart; Entry.Source = Source;
    ULyraPawnComponent_CharacterParts* Customizer = GetPawnCustomizer();
    TArray<int32> Indices;
    if (UEPSelectCharacterPartIndices(this, TEXT("Parts.Add"), Customizer != nullptr, CharacterParts, nullptr, false, Indices))
    {
        for (int32 Index : Indices) { if (Customizer) { CharacterParts[Index].Handle = Customizer->AddCharacterPart(CharacterParts[Index].Part); } }
        return;
    }
    if (Customizer && Entry.Source != ECharacterPartSource::NaturalSuppressedViaCheat) { Entry.Handle = Customizer->AddCharacterPart(NewPart); }
''',
        'RemoveCharacterPart':'''    TArray<int32> Indices; ULyraPawnComponent_CharacterParts* Customizer = GetPawnCustomizer();
    if (UEPSelectCharacterPartIndices(this, TEXT("Parts.Remove"), Customizer != nullptr, CharacterParts, &PartToRemove, false, Indices))
    {
        if (!Indices.IsEmpty()) { const int32 Index = Indices[0]; if (Customizer) { Customizer->RemoveCharacterPart(CharacterParts[Index].Handle); } CharacterParts.RemoveAt(Index); }
        return;
    }
''',
        'RemoveAllCharacterParts':'''    TArray<int32> Indices; ULyraPawnComponent_CharacterParts* Customizer = GetPawnCustomizer();
    if (UEPSelectCharacterPartIndices(this, TEXT("Parts.RemoveAll"), Customizer != nullptr, CharacterParts, nullptr, false, Indices))
    {
        for (int32 Index : Indices) { if (Customizer) { Customizer->RemoveCharacterPart(CharacterParts[Index].Handle); } }
        CharacterParts.Reset(); return;
    }
''',
        'SetSuppressionOnNaturalParts':'''#if UE_WITH_CHEAT_MANAGER
    TArray<int32> Indices; ULyraPawnComponent_CharacterParts* Customizer = GetPawnCustomizer();
    if (UEPSelectCharacterPartIndices(this, TEXT("Parts.Suppress"), Customizer != nullptr, CharacterParts, nullptr, bSuppressed, Indices))
    {
        for (int32 Index : Indices)
        {
            FLyraControllerCharacterPartEntry& Entry = CharacterParts[Index];
            if (bSuppressed) { if (Customizer) { Customizer->RemoveCharacterPart(Entry.Handle); Entry.Handle.Reset(); } Entry.Source = ECharacterPartSource::NaturalSuppressedViaCheat; }
            else { if (Customizer) { Entry.Handle = Customizer->AddCharacterPart(Entry.Part); } Entry.Source = ECharacterPartSource::Natural; }
        }
        return;
    }
#endif
'''}
    for name,prefix in prefixes.items():
        sig='void '+owner+name+'(';old=original_function_body(text,sig)
        text=replace_function(text,sig,prefix if name=='AddCharacterPartInternal' else prefix+old)
    sig='void '+owner+'OnPossessedPawnChanged(';old=original_function_body(text,sig)
    body='''    ULyraPawnComponent_CharacterParts* Old = OldPawn ? OldPawn->FindComponentByClass<ULyraPawnComponent_CharacterParts>() : nullptr;
    ULyraPawnComponent_CharacterParts* New = NewPawn ? NewPawn->FindComponentByClass<ULyraPawnComponent_CharacterParts>() : nullptr;
    TArray<int32> Indices;
    if (UEPSelectCharacterPartIndices(this, TEXT("Parts.Detach"), Old != nullptr, CharacterParts, nullptr, false, Indices))
    {
        for (int32 Index : Indices) { if (Old) { Old->RemoveCharacterPart(CharacterParts[Index].Handle); CharacterParts[Index].Handle.Reset(); } }
        Indices.Reset();
        if (UEPSelectCharacterPartIndices(this, TEXT("Parts.Attach"), New != nullptr, CharacterParts, nullptr, false, Indices))
        {
            for (int32 Index : Indices) { if (New) { CharacterParts[Index].Handle = New->AddCharacterPart(CharacterParts[Index].Part); } }
        }
        return;
    }
'''
    return replace_function(text,sig,body+old)


def sources():
    rows=[]
    for relative,transform in (
        ('Source/LyraGame/UI/Frontend/LyraFrontendStateComponent.cpp',frontend),
        ('Source/LyraGame/Cosmetics/LyraControllerComponent_CharacterParts.cpp',parts),
        ('Source/LyraGame/Character/LyraHeroComponent.cpp',None)):
        before=(REFERENCE/relative).read_text()
        if transform is None:
            marker='\t\treturn LyraPS && Manager->HasFeatureReachedInitState('
            assert before.count(marker)==1;before=before.replace(marker,HERO_GUARD+marker,1)
            sig='TSubclassOf<ULyraCameraMode> ULyraHeroComponent::DetermineCameraMode() const';old=original_function_body(before,sig)
            after=replace_function(before,sig,'''    UUEPNativeGameplayPolicy* Host = UUEPNativeGameplayPolicySubsystem::GetPolicyForContext(GetWorld());
    if (Host && Host->UEPUsesPythonPolicy(TEXT("Camera.Determine")))
    {
        UClass* DefaultMode = nullptr;
        if (const APawn* Pawn = GetPawn<APawn>())
        {
            if (const ULyraPawnExtensionComponent* Extension = ULyraPawnExtensionComponent::FindPawnExtensionComponent(Pawn))
            {
                if (const ULyraPawnData* Data = Extension->GetPawnData<ULyraPawnData>()) { DefaultMode = Data->DefaultCameraMode.Get(); }
            }
        }
        UClass* Selected = Cast<UClass>(Host->UEPChooseObject(TEXT("Camera.Determine"), AbilityCameraMode.Get(), DefaultMode));
        if (ensureMsgf(!Selected || Selected->IsChildOf(ULyraCameraMode::StaticClass()), TEXT("Invalid Python camera mode class"))) { return Selected; }
        return nullptr;
    }
'''+old)
        else:after=transform(before)
        after=after.replace('#include UE_INLINE_GENERATED_CPP_BY_NAME(', '#include "UEPPolicy/UEPNativeWorldPolicies.h"\n#include UE_INLINE_GENERATED_CPP_BY_NAME(',1)
        rows.append(dict(relative=relative,before=before,after=after,original_sha256=sha(REFERENCE/relative)))
        header=relative[:-4]+'.h';before=(REFERENCE/header).read_text();class_start=before.index('class U'+Path(header).stem+' :');body_start=before.index('GENERATED_BODY()',class_start);after=before[:body_start]+before[body_start:].replace('GENERATED_BODY()','GENERATED_BODY()\n\tfriend class UUEPNativeWorldPolicyFixture;',1)
        rows.append(dict(relative=header,before=before,after=after,original_sha256=sha(REFERENCE/header)))
    for suffix in ('.h','.cpp'):
        source=REPO/'Demos/UEPLyraIntegration/NativePolicyAdapters'/('UEPNativeWorldPolicies'+suffix)
        rows.append(dict(relative='Source/LyraGame/UEPPolicy/'+source.name,before='',after=source.read_text(),original_sha256=None,source=str(source)))
    return rows


def patch_text():return ''.join(line if line.endswith('\n') else line+'\n' for r in sources() for line in difflib.unified_diff(r['before'].splitlines(True),r['after'].splitlines(True),fromfile='a/'+r['relative'] if r['before'] else '/dev/null',tofile='b/'+r['relative']))


def apply(stage,output):
    stage,output=stage.resolve(),output.resolve()
    if not stage.is_relative_to(REPO/'.build/LyraValidation/CppGameplayExtended') or not output.is_relative_to(REPO/'.build') or output.exists():raise ValueError('Owned stage and fresh patch output required')
    artifact=REPO/'Demos/UEPLyraIntegration/Migration/NativeGameplay/CPP16-18-world-policies.patch'
    if artifact.read_text()!=patch_text():raise ValueError('Versioned world-policy patch differs')
    rows=sources()
    for r in rows:
        p=stage/r['relative']
        if (p.read_text(encoding='utf-8-sig') if p.exists() else '') not in (r['before'],r['after']):raise ValueError('Unrelated world-policy source: '+r['relative'])
    output.mkdir(parents=True);records=[]
    for r in rows:
        p=stage/r['relative'];p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():
            backup=output/'PreviousSources'/r['relative'];backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(p.read_bytes())
        p.write_text(r['after'],encoding='utf-8',newline='\n');records.append(dict(path=str(p),original=str(REFERENCE/r['relative']) if r['original_sha256'] else None,original_sha256=r['original_sha256'],patched_sha256=sha(p)))
    result=dict(status='patched_requires_native_build',sources=records,retained_simulated_proxy_initialization_guard=True,runtime_acceptance=False)
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(apply(a.stage,a.output),indent=2))
