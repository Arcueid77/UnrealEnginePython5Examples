[CmdletBinding()]
param(
    [string]$EngineRoot = "F:\UnrealEngine",
    [string]$PluginRoot = "",
    [ValidateSet("Overlay", "PythonFirst", "Mixin")]
    [string]$Variant = "PythonFirst",
    [ValidateSet("Prepare", "GenerateMixinAssets", "Audit", "Smoke", "Package", "Play", "Editor")]
    [string]$Mode = "Prepare",
    [ValidateRange(1, 64)]
    [int]$MaxParallelActions = 4,
    [switch]$Incremental
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path)
}

function Assert-PathIsUnder {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Parent
    )

    $fullPath = Get-FullPath $Path
    $fullParent = (Get-FullPath $Parent).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    if (!$fullPath.StartsWith($fullParent, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside $fullParent (resolved path: $fullPath)"
    }
}

function Copy-DirectoryContents {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (!(Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Source directory does not exist: $Source"
    }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
}

function Copy-FileIfChanged {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $destinationParent = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    if (Test-Path -LiteralPath $Destination -PathType Leaf) {
        $sourceItem = Get-Item -LiteralPath $Source
        $destinationItem = Get-Item -LiteralPath $Destination
        if ($sourceItem.Length -eq $destinationItem.Length) {
            $sourceHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
            $destinationHash = (
                Get-FileHash -LiteralPath $Destination -Algorithm SHA256
            ).Hash
            if ($sourceHash -eq $destinationHash) {
                return
            }
        }
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Format-ProcessCommand {
    param([string]$FilePath, [string[]]$ArgumentList)
    $displayArguments = $ArgumentList | ForEach-Object {
        if ($_ -match "\s") { '"' + $_.Replace('"', '\"') + '"' } else { $_ }
    }
    return "$FilePath $($displayArguments -join ' ')"
}

function Invoke-CheckedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [int]$TimeoutSeconds = 0,
        [hashtable]$EnvironmentVariables = @{}
    )

    Write-Host "[$Label] $(Format-ProcessCommand $FilePath $ArgumentList)"
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    foreach ($argument in $ArgumentList) {
        $startInfo.ArgumentList.Add($argument)
    }
    foreach ($entry in $EnvironmentVariables.GetEnumerator()) {
        $startInfo.Environment[$entry.Key] = [string]$entry.Value
    }

    $process = [System.Diagnostics.Process]::Start($startInfo)
    if (!$process) {
        throw "$Label failed to start"
    }
    try {
        if ($TimeoutSeconds -gt 0) {
            if (!$process.WaitForExit($TimeoutSeconds * 1000)) {
                $process.Kill($true)
                $process.WaitForExit()
                throw "$Label timed out after $TimeoutSeconds seconds"
            }
        }
        else {
            $process.WaitForExit()
        }
        if ($process.ExitCode -ne 0) {
            throw "$Label exited with code $($process.ExitCode)"
        }
    }
    finally {
        $process.Dispose()
    }
}

function Assert-AutomationLog {
    param([Parameter(Mandatory = $true)][string]$LogPath)

    if (!(Test-Path -LiteralPath $LogPath -PathType Leaf)) {
        throw "AutomationTool log was not created: $LogPath"
    }
    $contents = Get-Content -LiteralPath $LogPath -Raw
    foreach ($marker in @("BUILD SUCCESSFUL", "AutomationTool exiting with ExitCode=0")) {
        if (!$contents.Contains($marker)) {
            throw "AutomationTool log does not contain '$marker': $LogPath"
        }
    }
    $diagnostics = @([regex]::Matches(
        $contents,
        "(?im)Fatal error:|Assertion failed:|Unhandled Exception:|^.*Log[A-Za-z0-9_]+:\s+Error:.*$"
    ))
    if ($diagnostics.Count -gt 0) {
        $preview = @($diagnostics | Select-Object -First 5 | ForEach-Object { $_.Value }) -join "`n"
        throw "AutomationTool log contains $($diagnostics.Count) fatal/assert/error diagnostic(s): $LogPath`n$preview"
    }
}

function Assert-BuildLog {
    param([Parameter(Mandatory = $true)][string]$LogPath)

    if (!(Test-Path -LiteralPath $LogPath -PathType Leaf)) {
        throw "Build log was not created: $LogPath"
    }
    $contents = Get-Content -LiteralPath $LogPath -Raw
    if ($contents -notmatch "Result:\s+Succeeded") {
        throw "Build log does not contain a successful result: $LogPath"
    }
    $diagnostics = [regex]::Matches(
        $contents,
        "(?im)\b(?:warning C\d+|error C\d+|fatal error C\d+|error LNK\d+)\b"
    )
    if ($diagnostics.Count -gt 0) {
        throw "Build produced $($diagnostics.Count) compiler/linker diagnostic(s): $LogPath"
    }
}

function Assert-CleanRuntimeLog {
    param([Parameter(Mandatory = $true)][string]$LogPath)

    if (!(Test-Path -LiteralPath $LogPath -PathType Leaf)) {
        throw "Runtime log was not created: $LogPath"
    }
    $contents = Get-Content -LiteralPath $LogPath -Raw
    $diagnostics = @([regex]::Matches(
        $contents,
        "(?im)Fatal error:|Assertion failed:|Unhandled Exception:|LogWindows:\s+Error:|^.*Log[A-Za-z0-9_]+:\s+Error:.*$"
    ))
    if ($diagnostics.Count -gt 0) {
        $preview = @($diagnostics | Select-Object -First 5 | ForEach-Object { $_.Value }) -join "`n"
        throw "Runtime log contains $($diagnostics.Count) fatal/assert/error diagnostic(s): $LogPath`n$preview"
    }
}

function Assert-PythonFirstReport {
    param(
        [Parameter(Mandatory = $true)][psobject]$Report,
        [Parameter(Mandatory = $true)][string]$ResultPath,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if ($Report.schema_version -ne 5 -or
        $Report.status -ne "passed" -or
        @($Report.engine_version).Count -ne 3 -or
        $Report.engine_version[0] -ne 5 -or
        $Report.engine_version[1] -ne 8 -or
        $Report.python_version -notlike "3.11.*" -or
        $Report.uep_version -ne "0.7.0" -or
        $Report.demo_version -ne "0.6.0" -or
        $Report.game_mode_class -ne "UEPThirdPersonGameMode" -or
        $Report.controller_class -ne "UEPThirdPersonPlayerController" -or
        $Report.character_class -ne "UEPThirdPersonCharacter" -or
        !$Report.mapping_contexts.default -or
        !$Report.mapping_contexts.mouse_look -or
        $Report.input_binding_count -ne 5 -or
        $Report.movement_distance -le 25.0 -or
        $Report.look_delta -le 0.1 -or
        !$Report.jump_observed -or
        $Report.input_events.jump_started -le 0 -or
        $Report.input_events.jump_completed -le 0 -or
        $Report.input_events.source -ne "enhanced_input_mapped_keys" -or
        $Report.input_delivery.mode -ne "enhanced_input_mapped_keys" -or
        $Report.input_delivery.move_key -ne "W" -or
        $Report.input_delivery.look_key -ne "Mouse2D" -or
        @($Report.input_delivery.look_axes).Count -ne 2 -or
        $Report.input_delivery.look_axes[0] -ne "MouseX" -or
        $Report.input_delivery.look_axes[1] -ne "MouseY" -or
        $Report.input_delivery.jump_key -ne "SpaceBar" -or
        @($Report.input_delivery.events).Count -ne 4 -or
        $Report.input_delivery.axis_samples -le 0 -or
        !$Report.input_delivery.all_keys_released -or
        @($Report.animation_states_observed).Count -lt 4 -or
        @($Report.animation_states_observed | Where-Object { $_ -in @("locomotion", "jump", "fall", "land") } | Sort-Object -Unique).Count -ne 4 -or
        !$Report.camera_boom_valid -or
        !$Report.follow_camera_valid -or
        $Report.python_tick_count -le 0 -or
        $Report.map_travel_count -ne 1 -or
        $Report.runtime_session_generation -lt 2 -or
        $Report.gameplay.progress.phase -ne "victory" -or
        $Report.gameplay.progress.round_score -ne 6 -or
        $Report.gameplay.progress.total_score -ne 6 -or
        $Report.gameplay.remaining_pickups -ne 0 -or
        !$Report.gameplay.companion_valid -or
        $Report.gameplay.companion_movement -le 1.0 -or
        !$Report.gameplay.hud.attached -or
        $Report.gameplay.hud.update_count -le 0 -or
        $Report.post_travel.generation -lt 2 -or
        $Report.post_travel.progress.round_score -ne 0 -or
        $Report.post_travel.remaining_pickups -ne 6 -or
        !$Report.post_travel.hud.attached -or
        $Report.teardown.runtime_active -ne $false -or
        !$Report.teardown.session_released -or
        !$Report.teardown.hud_detached -or
        !$Report.teardown.input_bindings_removed -or
        !$Report.teardown.mapping_contexts_removed) {
        throw "Python-first demo $Label report failed its contract: $ResultPath"
    }
}

function Assert-MixinReport {
    param(
        [Parameter(Mandatory = $true)][psobject]$Report,
        [Parameter(Mandatory = $true)][string]$ResultPath,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if ($Report.status -ne "passed") {
        $details = if ($Report.PSObject.Properties.Name -contains "error") {
            "`n$($Report.error)"
        }
        else {
            ""
        }
        throw "Mixin demo $Label reported failure: $ResultPath$details"
    }

    $expectedFunctions = @("Aim", "Move", "ReceiveBeginPlay")
    $expectedProfiles = @("BlueprintFallback", "Python")
    $expectedFallbackFunctions = @("Aim", "ReceiveBeginPlay")
    $registeredFunctions = @($Report.registration_before.functions)
    $directFunctions = @($Report.registration_direct.functions)
    $reregisteredFunctions = @($Report.registration_after_reregister.functions)
    $registeredProfiles = @(
        $Report.registration_before.profiles.PSObject.Properties.Name
    )
    $reregisteredProfiles = @($Report.registration_after_reregister.profiles)
    $directProfiles = @($Report.registration_direct.profiles)
    $interfaceFallbackResults = @($Report.interface_contract.fallback_results)
    $interfaceSnapshots = @($Report.interface_contract.snapshots)
    $interfaceTeardowns = @($Report.teardown.interface_probe.teardowns)
    $interfaceArrayFunctions = @(
        $Report.interface_contract.profile_functions.ArrayRoute
    )
    $expectedInterfaceArrayFunctions = @(
        "AddInstances",
        "BatchUpdateInstancesTransforms"
    )
    if ($Report.schema_version -ne 4 -or
        @($Report.engine_version).Count -ne 3 -or
        $Report.engine_version[0] -ne 5 -or
        $Report.engine_version[1] -ne 8 -or
        $Report.python_version -notlike "3.11.*" -or
        $Report.uep_version -ne "0.7.0" -or
        $Report.demo_version -ne "0.7.0" -or
        $Report.game_mode_class -ne "BP_ThirdPersonGameMode_C" -or
        $Report.controller_class -ne "BP_ThirdPersonPlayerController_C" -or
        $Report.character_class -ne "BP_ThirdPersonCharacter_C" -or
        $Report.registration_before.target_class -ne "BP_ThirdPersonCharacter_C" -or
        $Report.registration_before.default_profile -ne "Python" -or
        $Report.registration_before.mixin_set -ne "DA_ThirdPersonCharacterMixin" -or
        $registeredProfiles.Count -ne $expectedProfiles.Count -or
        @(Compare-Object $registeredProfiles $expectedProfiles).Count -ne 0 -or
        @(Compare-Object @($Report.registration_before.profiles.Python) $expectedFunctions).Count -ne 0 -or
        @(Compare-Object @($Report.registration_before.profiles.BlueprintFallback) $expectedFallbackFunctions).Count -ne 0 -or
        $registeredFunctions.Count -ne $expectedFunctions.Count -or
        @(Compare-Object $registeredFunctions $expectedFunctions).Count -ne 0 -or
        $Report.registration_direct.mixin_set -ne $null -or
        $directFunctions.Count -ne $expectedFunctions.Count -or
        @(Compare-Object $directFunctions $expectedFunctions).Count -ne 0 -or
        $directProfiles.Count -ne $expectedProfiles.Count -or
        @(Compare-Object $directProfiles $expectedProfiles).Count -ne 0 -or
        $Report.registration_direct.registration_id -eq
            $Report.registration_before.registration_id -or
        $Report.registration_after_reregister.registration_id -eq
            $Report.registration_before.registration_id -or
        $Report.registration_after_reregister.registration_id -eq
            $Report.registration_direct.registration_id -or
        $Report.registration_after_reregister.mixin_set -ne "DA_ThirdPersonCharacterMixin" -or
        $reregisteredFunctions.Count -ne $expectedFunctions.Count -or
        @(Compare-Object $reregisteredFunctions $expectedFunctions).Count -ne 0 -or
        $reregisteredProfiles.Count -ne $expectedProfiles.Count -or
        @(Compare-Object $reregisteredProfiles $expectedProfiles).Count -ne 0 -or
        !$Report.invalid_registration.rejected -or
        !$Report.invalid_registration.preserved_active -or
        !$Report.initial_snapshot.initialized -or
        $Report.initial_snapshot.initializations -ne 1 -or
        $Report.initial_snapshot.teardowns -ne 0 -or
        $Report.initial_snapshot.begin_play -ne 1 -or
        $Report.initial_snapshot.original_begin_play -ne 1 -or
        $Report.initial_snapshot.profile -ne "Python" -or
        $Report.character_interface.mixin_set -ne "DA_ThirdPersonCharacterMixin" -or
        $Report.character_interface.profile_variable -ne "PythonMixinProfile" -or
        $Report.character_interface.cdo_profile -ne "Python" -or
        $Report.character_interface.pawn_profile_property -ne "Python" -or
        $Report.interface_contract.interface_class -ne "UEPPythonMixinInterface" -or
        $Report.interface_contract.mixin_set_class -ne "UEPPythonMixinSet" -or
        $Report.interface_contract.mixin_set_asset -ne "DA_MixinInterfaceProbe" -or
        $Report.interface_contract.default_profile -ne "BlueprintFallback" -or
        $Report.interface_contract.profile_count -ne 2 -or
        $Report.interface_contract.declaring_class -ne "BP_MixinInterfaceProbe_C" -or
        $Report.interface_contract.inherited_child_class -ne "BP_MixinInterfaceProbeChild_C" -or
        $Report.interface_contract.router_owner_count -ne 1 -or
        @(Compare-Object $interfaceArrayFunctions $expectedInterfaceArrayFunctions).Count -ne 0 -or
        @($Report.interface_contract.profile_functions.BlueprintFallback).Count -ne 1 -or
        $Report.interface_contract.profile_functions.BlueprintFallback[0] -ne "SetCullDistances" -or
        $interfaceFallbackResults.Count -ne 2 -or
        $interfaceFallbackResults[0].explicit_return_value[0] -ne 0 -or
        $interfaceFallbackResults[1].explicit_return_value[0] -ne 0 -or
        $interfaceFallbackResults[0].return_value[0] -ne 0 -or
        $interfaceFallbackResults[1].return_value[0] -ne 0 -or
        $interfaceFallbackResults[0].tuple_arity -ne 2 -or
        $interfaceFallbackResults[1].tuple_arity -ne 2 -or
        $interfaceFallbackResults[0].const_input_echo_count -ne 1 -or
        $interfaceFallbackResults[1].const_input_echo_count -ne 1 -or
        !$interfaceFallbackResults[0].scalar_fallback.explicit_return -or
        !$interfaceFallbackResults[1].scalar_fallback.explicit_return -or
        !$interfaceFallbackResults[0].scalar_fallback.automatic_return -or
        !$interfaceFallbackResults[1].scalar_fallback.automatic_return -or
        $interfaceFallbackResults[0].scalar_fallback.tuple_arity -ne 2 -or
        $interfaceFallbackResults[1].scalar_fallback.tuple_arity -ne 2 -or
        $interfaceFallbackResults[0].scalar_fallback.const_input_echo_count -ne 1 -or
        $interfaceFallbackResults[1].scalar_fallback.const_input_echo_count -ne 1 -or
        $interfaceSnapshots.Count -ne 2 -or
        $interfaceSnapshots[0].profile -ne "BlueprintFallback" -or
        $interfaceSnapshots[1].profile -ne "BlueprintFallback" -or
        $Report.reentrancy.initializer_mutations_rejected -lt 3 -or
        $Report.reentrancy.teardown_mutations_rejected -lt 3 -or
        $Report.reentrancy.nested_peer_dispatches -ne 1 -or
        !$Report.profile_router.same_blueprint_class -or
        $Report.profile_router.selection_source -ne "Blueprint instance variable" -or
        $Report.profile_router.main_profile -ne "Python" -or
        $Report.profile_router.peer_profile -ne "BlueprintFallback" -or
        $Report.profile_router.peer_profile_property -ne "BlueprintFallback" -or
        $Report.profile_router.peer_snapshot.profile -ne "BlueprintFallback" -or
        $Report.profile_router.peer_snapshot.aim -ne 1 -or
        $Report.pre_restore_snapshot.move -le 0 -or
        $Report.pre_restore_snapshot.aim -le 0 -or
        $Report.movement_distance -le 25.0 -or
        $Report.profile_fallback_move_distance -le 25.0 -or
        $Report.look_delta -le 0.1 -or
        $Report.jump_height -le 10.0 -or
        $Report.blueprint_original_move_distance -le 25.0 -or
        $Report.direct_reregister_move_distance -le 25.0 -or
        $Report.live_reregister_move_distance -le 25.0 -or
        !$Report.function_identity.injected_differs_from_restored -or
        !$Report.function_identity.restored_differs_from_reregistered -or
        !$Report.function_identity.direct_differs_from_restored -or
        !$Report.function_identity.declared_differs_from_direct -or
        $Report.gameplay.progress.phase -ne "victory" -or
        $Report.gameplay.progress.round_score -ne 6 -or
        $Report.gameplay.remaining_pickups -ne 0 -or
        !$Report.gameplay.companion_valid -or
        $Report.gameplay.companion_movement -le 1.0 -or
        !$Report.gameplay.hud.attached -or
        $Report.gameplay.hud.update_count -le 0 -or
        $Report.teardown.unregister_all_count -ne 2 -or
        $Report.teardown.mixin_count -ne 0 -or
        $Report.teardown.initialization_events -ne 5 -or
        $Report.teardown.teardown_events -ne 5 -or
        $Report.teardown.runtime_active -ne $false -or
        !$Report.teardown.session_released -or
        !$Report.teardown.class_preserved -or
        !$Report.teardown.helper_removed -or
        $interfaceTeardowns.Count -ne 2 -or
        $interfaceTeardowns[0] -ne 1 -or
        $interfaceTeardowns[1] -ne 1 -or
        !$Report.teardown.interface_probe.helpers_removed) {
        throw "Mixin demo $Label report failed its contract: $ResultPath"
    }
}

$embeddedPluginRoot = Get-FullPath (Join-Path $PSScriptRoot "..")
$isEmbeddedInPlugin = Test-Path -LiteralPath (
    Join-Path $embeddedPluginRoot "UnrealEnginePython.uplugin"
) -PathType Leaf
if ($PluginRoot) {
    $repoRoot = Get-FullPath $PluginRoot
}
elseif ($isEmbeddedInPlugin) {
    $repoRoot = $embeddedPluginRoot
}
else {
    $siblingPluginRoot = Get-FullPath (
        Join-Path $PSScriptRoot "..\UnrealEnginePython5"
    )
    if (Test-Path -LiteralPath (
        Join-Path $siblingPluginRoot "UnrealEnginePython.uplugin"
    ) -PathType Leaf) {
        $repoRoot = $siblingPluginRoot
    }
    else {
        throw "UnrealEnginePython5 was not found. Pass -PluginRoot <path>."
    }
}
$demoWorkspaceRoot = if ($isEmbeddedInPlugin) { $embeddedPluginRoot } else { $PSScriptRoot }
$engineRootPath = Get-FullPath $EngineRoot
$engineVersionPath = Join-Path $engineRootPath "Engine\Build\Build.version"
$templateRoot = Join-Path $engineRootPath "Templates\TP_ThirdPersonBP"
$templateResourcesRoot = Join-Path $engineRootPath "Templates\TemplateResources\High"
$demoName = if ($Variant -eq "Overlay") { "UEPThirdPersonDemo" } else { "UEPPythonThirdPerson" }
$projectFileName = "$demoName.uproject"
$overlayRoot = Join-Path $PSScriptRoot "$demoName\Overlay"
$variantOverlayRoot = if ($Variant -eq "Mixin") {
    Join-Path $PSScriptRoot "UEPPythonThirdPerson\Mixin"
}
else {
    $null
}
$demoBuildRoot = Join-Path $demoWorkspaceRoot ".build\Demos"
$stageRoot = Join-Path $demoBuildRoot $demoName
$stageMarker = Join-Path $stageRoot ".uep-demo-stage"
$projectPath = Join-Path $stageRoot $projectFileName
$pluginStage = Join-Path $stageRoot "Plugins\UnrealEnginePython"
$pluginDescriptor = Join-Path $pluginStage "UnrealEnginePython.uplugin"
$disabledNetworkPlugins = "AndroidFileServer,UdpMessaging,TcpMessaging"
$disableNetworkPluginsArgument = "-DisablePlugins=$disabledNetworkPlugins"
$disableTraceServerArgument = "-notraceserver"
$runId = Get-Date -Format "yyyyMMdd-HHmmss"
$resultRoot = Join-Path $demoBuildRoot "Results\$runId"

$dotnetRoot = Join-Path $engineRootPath "Engine\Binaries\ThirdParty\DotNet"
$dotnetPath = Get-ChildItem -LiteralPath $dotnetRoot -Directory -ErrorAction Stop |
    Sort-Object { [version]$_.Name } -Descending |
    ForEach-Object { Join-Path $_.FullName "win-x64\dotnet.exe" } |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1
$ubtPath = Join-Path $engineRootPath "Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.dll"
$automationToolPath = Join-Path $engineRootPath "Engine\Binaries\DotNET\AutomationTool\AutomationTool.dll"
$editorPath = Join-Path $engineRootPath "Engine\Binaries\Win64\UnrealEditor.exe"
$editorCmdPath = Join-Path $engineRootPath "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"

foreach ($requiredFile in @(
    $engineVersionPath,
    $dotnetPath,
    $ubtPath,
    $automationToolPath,
    $editorPath,
    $editorCmdPath,
    (Join-Path $templateRoot "TP_ThirdPersonBP.uproject"),
    (Join-Path $overlayRoot $projectFileName),
    (Join-Path $repoRoot "UnrealEnginePython.uplugin")
)) {
    if (!$requiredFile -or !(Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required file was not found: $requiredFile"
    }
}
if ($variantOverlayRoot -and !(Test-Path -LiteralPath (
    Join-Path $variantOverlayRoot "Content\Scripts\ue_site.py"
) -PathType Leaf)) {
    throw "Mixin overlay was not found: $variantOverlayRoot"
}

$engineVersion = Get-Content -LiteralPath $engineVersionPath -Raw | ConvertFrom-Json
if ($engineVersion.MajorVersion -ne 5 -or $engineVersion.MinorVersion -ne 8) {
    throw "Expected Unreal Engine 5.8, found $($engineVersion.MajorVersion).$($engineVersion.MinorVersion).$($engineVersion.PatchVersion)"
}

if ($Variant -eq "Overlay" -and $Mode -in @("Audit", "Package")) {
    throw "Mode $Mode is available only for the PythonFirst and Mixin variants"
}
if ($Mode -eq "GenerateMixinAssets" -and $Variant -ne "Mixin") {
    throw "Mode GenerateMixinAssets is available only for the Mixin variant"
}

New-Item -ItemType Directory -Path $demoBuildRoot -Force | Out-Null
New-Item -ItemType Directory -Path $resultRoot -Force | Out-Null

try {
    if ((Test-Path -LiteralPath $stageRoot) -and !(Test-Path -LiteralPath $stageMarker -PathType Leaf)) {
        throw "Refusing to use an unmarked staging directory: $stageRoot"
    }

    if (!$Incremental -and (Test-Path -LiteralPath $stageRoot)) {
        Assert-PathIsUnder -Path $stageRoot -Parent $demoBuildRoot
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }

    $templateMap = Join-Path $stageRoot "Content\ThirdPerson\Lvl_ThirdPerson.umap"
    $sharedMesh = Join-Path $stageRoot "Content\LevelPrototyping\Meshes\SM_ChamferCube.uasset"
    $needsTemplateCopy = !(Test-Path -LiteralPath $templateMap -PathType Leaf) -or
        !(Test-Path -LiteralPath $sharedMesh -PathType Leaf)

    if ($needsTemplateCopy) {
        New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null

        $legacySharedContent = @(
            "Actions",
            "Touch",
            "Mannequins",
            "Interactable",
            "Materials",
            "Meshes",
            "Textures",
            "IMC_Default.uasset",
            "IMC_MouseLook.uasset"
        )
        $legacyMountDetected =
            (Test-Path -LiteralPath (Join-Path $stageRoot "Content\IMC_Default.uasset")) -or
            (Test-Path -LiteralPath (Join-Path $stageRoot "Content\Mannequins"))
        if ($legacyMountDetected) {
            foreach ($relativePath in $legacySharedContent) {
                $legacyPath = Join-Path $stageRoot "Content\$relativePath"
                Assert-PathIsUnder -Path $legacyPath -Parent $stageRoot
                if (Test-Path -LiteralPath $legacyPath) {
                    Remove-Item -LiteralPath $legacyPath -Recurse -Force
                }
            }
        }

        Copy-DirectoryContents (Join-Path $templateRoot "Config") (Join-Path $stageRoot "Config")
        Copy-DirectoryContents (Join-Path $templateRoot "Content") (Join-Path $stageRoot "Content")
        foreach ($resourceName in @("Characters", "Input", "LevelPrototyping")) {
            $resourceContent = Join-Path $templateResourcesRoot "$resourceName\Content"
            # Shared template packs are mounted below Content by the MountName
            # declared in TemplateDefs.ini. Preserve that layout so object paths
            # embedded in the assets (for example /Game/Input/Actions/IA_Move)
            # resolve to the same objects that the Python bindings load.
            Copy-DirectoryContents `
                $resourceContent `
                (Join-Path $stageRoot "Content\$resourceName")
        }
    }

    foreach ($requiredTemplateAsset in @(
        "Content\Input\Actions\IA_Move.uasset",
        "Content\Input\IMC_Default.uasset",
        "Content\Characters\Mannequins\Meshes\SKM_Manny_Simple.uasset",
        "Content\LevelPrototyping\Meshes\SM_ChamferCube.uasset"
    )) {
        $requiredTemplatePath = Join-Path $stageRoot $requiredTemplateAsset
        if (!(Test-Path -LiteralPath $requiredTemplatePath -PathType Leaf)) {
            throw "Mounted template asset was not staged: $requiredTemplatePath"
        }
    }
    foreach ($legacyTemplateAsset in @(
        "Content\Actions\IA_Move.uasset",
        "Content\IMC_Default.uasset",
        "Content\Mannequins\Meshes\SKM_Manny_Simple.uasset"
    )) {
        $legacyTemplatePath = Join-Path $stageRoot $legacyTemplateAsset
        if (Test-Path -LiteralPath $legacyTemplatePath) {
            throw "Legacy flattened template asset remains staged: $legacyTemplatePath"
        }
    }

    # Variants share one disposable stage. Restore template Blueprint shells on
    # every incremental prepare before applying the selected variant: otherwise
    # switching Mixin -> PythonFirst keeps a CDO importing removed Mixin scripts.
    Copy-DirectoryContents (Join-Path $templateRoot 'Content\ThirdPerson\Blueprints') (Join-Path $stageRoot 'Content\ThirdPerson\Blueprints')
    if ($Variant -ne 'Mixin') {
        $mixinContent = Join-Path $PSScriptRoot 'UEPPythonThirdPerson\Mixin\Content'
        foreach ($asset in Get-ChildItem -LiteralPath $mixinContent -Recurse -File -Filter '*.uasset') {
            $relative = [IO.Path]::GetRelativePath($mixinContent, $asset.FullName)
            if (!(Test-Path -LiteralPath (Join-Path $templateRoot "Content\$relative")) -and
                !(Test-Path -LiteralPath (Join-Path $overlayRoot "Content\$relative"))) {
                $stale = Join-Path $stageRoot "Content\$relative"
                Assert-PathIsUnder -Path $stale -Parent $stageRoot
                if (Test-Path -LiteralPath $stale -PathType Leaf) { Remove-Item -LiteralPath $stale -Force }
            }
        }
    }
    Copy-DirectoryContents $overlayRoot $stageRoot
    $overlayScripts = Join-Path $overlayRoot "Content\Scripts"
    $stagedScripts = Join-Path $stageRoot "Content\Scripts"
    if (Test-Path -LiteralPath $overlayScripts -PathType Container) {
        Assert-PathIsUnder -Path $stagedScripts -Parent $stageRoot
        if (Test-Path -LiteralPath $stagedScripts -PathType Container) {
            Remove-Item -LiteralPath $stagedScripts -Recurse -Force
        }
        Copy-DirectoryContents $overlayScripts $stagedScripts
    }
    if ($variantOverlayRoot) {
        Copy-DirectoryContents $variantOverlayRoot $stageRoot
    }
    Set-Content -LiteralPath $stageMarker -Value "Managed by Run-UEPThirdPersonDemo.ps1" -Encoding utf8

    New-Item -ItemType Directory -Path $pluginStage -Force | Out-Null
    foreach ($directoryName in @("Source", "Config", "Resources", "Content")) {
        $sourceDirectory = Join-Path $repoRoot $directoryName
        if (Test-Path -LiteralPath $sourceDirectory -PathType Container) {
            Copy-DirectoryContents $sourceDirectory (Join-Path $pluginStage $directoryName)
        }
    }
    Copy-FileIfChanged `
        -Source (Join-Path $repoRoot "UnrealEnginePython.uplugin") `
        -Destination $pluginDescriptor

    $buildLog = $null
    if ($Mode -ne "Prepare") {
        $buildLog = Join-Path $resultRoot "build-editor.log"
        $editorTarget = if ($Variant -ne "Overlay") {
            "UEPPythonThirdPersonEditor"
        }
        else {
            "UnrealEditor"
        }
        $buildArguments = @(
            $ubtPath,
            $editorTarget,
            "Win64",
            "Development",
            "-Project=$projectPath",
            "-NoHotReload",
            "-NoMutex",
            "-NoUBA",
            "-MaxParallelActions=$MaxParallelActions",
            "-Log=$buildLog"
        )
        if ($Variant -eq "Overlay") {
            $buildArguments += "-plugin=$pluginDescriptor"
        }
        Invoke-CheckedProcess -FilePath $dotnetPath -ArgumentList $buildArguments -Label "Build demo plugin" -WorkingDirectory $repoRoot -TimeoutSeconds 3600
        Assert-BuildLog $buildLog
    }

    if ($Mode -eq "GenerateMixinAssets") {
        $generatorScript = Join-Path $PSScriptRoot "UEPPythonThirdPerson\Tools\generate_mixin_assets.py"
        $generatorResultPath = Join-Path $resultRoot "mixin-assets.json"
        $generatorLogPath = Join-Path $resultRoot "mixin-assets.log"
        if (!(Test-Path -LiteralPath $generatorScript -PathType Leaf)) {
            throw "Mixin asset generator was not found: $generatorScript"
        }
        $generatorArguments = @(
            $projectPath,
            "-unattended",
            "-nop4",
            "-NullRHI",
            "-NoSound",
            "-NoSplash",
            "-UTF8Output",
            "-DisablePython",
            $disableNetworkPluginsArgument,
            $disableTraceServerArgument,
            "-run=Py",
            $generatorScript,
            "-UEPGenerateMixinAssetsResult=$generatorResultPath",
            "-abslog=$generatorLogPath"
        )
        Invoke-CheckedProcess -FilePath $editorCmdPath -ArgumentList $generatorArguments -Label "Generate Mixin Interface assets" -WorkingDirectory $stageRoot -TimeoutSeconds 300
        if (!(Test-Path -LiteralPath $generatorResultPath -PathType Leaf)) {
            throw "Mixin asset generation result was not created: $generatorResultPath"
        }
        $generatorReport = Get-Content -LiteralPath $generatorResultPath -Raw | ConvertFrom-Json
        if ($generatorReport.schema_version -ne 2 -or
            $generatorReport.status -ne "passed" -or
            $generatorReport.direct_interface_owner -ne "BP_MixinInterfaceProbe_C" -or
            $generatorReport.inherited_child -ne "BP_MixinInterfaceProbeChild_C" -or
            $generatorReport.default_profile -ne "BlueprintFallback" -or
            $generatorReport.profile_count -ne 2 -or
            $generatorReport.character.generated_class -ne "BP_ThirdPersonCharacter_C" -or
            $generatorReport.character.mixin_set -ne "DA_ThirdPersonCharacterMixin" -or
            $generatorReport.character.default_profile -ne "Python" -or
            $generatorReport.character.profile_count -ne 2 -or
            $generatorReport.character.profile_variable -ne "PythonMixinProfile" -or
            $generatorReport.character.profile_value -ne "Python") {
            throw "Mixin asset generation report failed its contract: $generatorResultPath"
        }
        $generatorLog = Get-Content -LiteralPath $generatorLogPath -Raw
        if (!$generatorLog.Contains("UEP_MIXIN_ASSET_GENERATION_PASSED") -or
            $generatorLog.Contains("UEP_MIXIN_ASSET_GENERATION_FAILED") -or
            $generatorLog.Contains("Fatal error:") -or
            $generatorLog.Contains("Assertion failed:")) {
            throw "Mixin asset generation log failed its contract: $generatorLogPath"
        }

        $assetMappings = @(
            @{
                source = "Content\UEPTests\DA_MixinInterfaceProbe.uasset"
                destination = "Content\UEPTests\DA_MixinInterfaceProbe.uasset"
            },
            @{
                source = "Content\UEPTests\BP_MixinInterfaceProbe.uasset"
                destination = "Content\UEPTests\BP_MixinInterfaceProbe.uasset"
            },
            @{
                source = "Content\UEPTests\BP_MixinInterfaceProbeChild.uasset"
                destination = "Content\UEPTests\BP_MixinInterfaceProbeChild.uasset"
            },
            @{
                source = "Content\UEPMixins\DA_ThirdPersonCharacterMixin.uasset"
                destination = "Content\UEPMixins\DA_ThirdPersonCharacterMixin.uasset"
            },
            @{
                source = "Content\ThirdPerson\Blueprints\BP_ThirdPersonCharacter.uasset"
                destination = "Content\ThirdPerson\Blueprints\BP_ThirdPersonCharacter.uasset"
            }
        )
        foreach ($assetMapping in $assetMappings) {
            $generatedAsset = Join-Path $stageRoot $assetMapping.source
            if (!(Test-Path -LiteralPath $generatedAsset -PathType Leaf)) {
                throw "Generated Mixin asset was not found: $generatedAsset"
            }
            Copy-FileIfChanged `
                -Source $generatedAsset `
                -Destination (Join-Path $variantOverlayRoot $assetMapping.destination)
        }

        $summary = [ordered]@{
            schema_version = 1
            status = "passed"
            run_id = $runId
            variant = $Variant
            engine = "$($engineVersion.MajorVersion).$($engineVersion.MinorVersion).$($engineVersion.PatchVersion)"
            project = $projectPath
            build_log = $buildLog
            generation_log = $generatorLogPath
            generation = $generatorReport
            destination = $variantOverlayRoot
        }
        $summaryPath = Join-Path $resultRoot "summary.json"
        $summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryPath -Encoding utf8
        Write-Host "UEP Mixin Interface assets generated and copied to the overlay."
        Write-Host "Summary: $summaryPath"
    }
    elseif ($Mode -eq "Audit") {
        $auditScript = Join-Path $PSScriptRoot "UEPPythonThirdPerson\Tools\audit_template.py"
        $auditResultPath = Join-Path $resultRoot "template-audit.json"
        $auditLogPath = Join-Path $resultRoot "template-audit.log"
        if (!(Test-Path -LiteralPath $auditScript -PathType Leaf)) {
            throw "Template audit script was not found: $auditScript"
        }
        $auditArguments = @(
            $projectPath,
            "-unattended",
            "-nop4",
            "-NullRHI",
            "-NoSound",
            "-NoSplash",
            "-UTF8Output",
            "-DisablePython",
            $disableNetworkPluginsArgument,
            $disableTraceServerArgument,
            "-run=Py",
            $auditScript,
            "-UEPTemplateAuditResult=$auditResultPath",
            "-abslog=$auditLogPath"
        )
        Invoke-CheckedProcess -FilePath $editorCmdPath -ArgumentList $auditArguments -Label "Audit reference Blueprints" -WorkingDirectory $stageRoot -TimeoutSeconds 300
        if (!(Test-Path -LiteralPath $auditResultPath -PathType Leaf)) {
            throw "Template audit result was not created: $auditResultPath"
        }
        $auditReport = Get-Content -LiteralPath $auditResultPath -Raw | ConvertFrom-Json
        if ($auditReport.status -ne "passed" -or
            $auditReport.engine_version[0] -ne 5 -or
            $auditReport.engine_version[1] -ne 8 -or
            $auditReport.summary.blueprint_count -ne 4 -or
            $auditReport.summary.graph_count -le 0 -or
            $auditReport.summary.node_count -le 0) {
            throw "Template audit report failed its contract: $auditResultPath"
        }
        $auditLog = Get-Content -LiteralPath $auditLogPath -Raw
        if (!$auditLog.Contains("UEP_TEMPLATE_AUDIT_PASSED") -or
            $auditLog.Contains("UEP_TEMPLATE_AUDIT_FAILED") -or
            $auditLog.Contains("Fatal error:") -or
            $auditLog.Contains("Assertion failed:")) {
            throw "Template audit log failed its contract: $auditLogPath"
        }
        Assert-CleanRuntimeLog $auditLogPath
        $summary = [ordered]@{
            schema_version = 1
            status = "passed"
            run_id = $runId
            variant = $Variant
            engine = "$($engineVersion.MajorVersion).$($engineVersion.MinorVersion).$($engineVersion.PatchVersion)"
            project = $projectPath
            build_log = $buildLog
            audit_log = $auditLogPath
            audit = $auditReport
        }
        $summaryPath = Join-Path $resultRoot "summary.json"
        $summary | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryPath -Encoding utf8
        Write-Host "UEP Third Person template audit passed."
        Write-Host "Summary: $summaryPath"
    }
    elseif ($Mode -eq "Smoke") {
        $smokeResultPath = Join-Path $resultRoot "smoke.json"
        $smokeLogPath = Join-Path $resultRoot "smoke.log"
        $gameUrl = if ($Variant -eq "PythonFirst") {
            "/Game/ThirdPerson/Lvl_ThirdPerson?game=/Engine/Transient.UEPThirdPersonGameMode"
        }
        else {
            "/Game/ThirdPerson/Lvl_ThirdPerson"
        }
        $smokeResultArgument = switch ($Variant) {
            "PythonFirst" { "-UEPPythonThirdPersonSmokeResult=$smokeResultPath" }
            "Mixin" { "-UEPMixinThirdPersonSmokeResult=$smokeResultPath" }
            default { "-UEPDemoSmokeResult=$smokeResultPath" }
        }
        $smokeArguments = @(
            $projectPath,
            $gameUrl,
            "-game",
            "-unattended",
            "-nop4",
            "-NullRHI",
            "-NoSound",
            "-NoSplash",
            "-UTF8Output",
            "-DisablePython",
            $disableNetworkPluginsArgument,
            $disableTraceServerArgument,
            $smokeResultArgument,
            "-abslog=$smokeLogPath"
        )
        Invoke-CheckedProcess -FilePath $editorPath -ArgumentList $smokeArguments -Label "Run demo smoke test" -WorkingDirectory $stageRoot -TimeoutSeconds 300

        if (!(Test-Path -LiteralPath $smokeResultPath -PathType Leaf)) {
            throw "Demo smoke result was not created: $smokeResultPath"
        }
        if (!(Test-Path -LiteralPath $smokeLogPath -PathType Leaf)) {
            throw "Demo smoke log was not created: $smokeLogPath"
        }
        $smokeReport = Get-Content -LiteralPath $smokeResultPath -Raw | ConvertFrom-Json
        if ($Variant -eq "PythonFirst") {
            Assert-PythonFirstReport `
                -Report $smokeReport `
                -ResultPath $smokeResultPath `
                -Label "smoke"
        }
        elseif ($Variant -eq "Mixin") {
            Assert-MixinReport `
                -Report $smokeReport `
                -ResultPath $smokeResultPath `
                -Label "smoke"
        }
        elseif ($smokeReport.status -ne "passed" -or
            !$smokeReport.companion_valid -or
            $smokeReport.pickup_count -ne 6 -or
            $smokeReport.python_version -notlike "3.11.*") {
            throw "Overlay demo smoke report failed its contract: $smokeResultPath"
        }
        $smokeLog = Get-Content -LiteralPath $smokeLogPath -Raw
        $requiredMarkers = if ($Variant -eq "PythonFirst") {
            @(
                "Initialized engine CPython at",
                "UEP_PYTHON_THIRD_PERSON_SCRIPT_LOADED",
                "UEP_PYTHON_THIRD_PERSON_CLASSES_READY",
                "UEP_PYTHON_THIRD_PERSON_WORLD_READY",
                "UEP_PYTHON_THIRD_PERSON_GAMEPLAY_READY",
                "UEP_PYTHON_THIRD_PERSON_HUD_READY",
                "UEP_PYTHON_THIRD_PERSON_ROUND_COMPLETE",
                "UEP_PYTHON_THIRD_PERSON_HUD_RELEASED",
                "UEP_PYTHON_THIRD_PERSON_SMOKE_PASSED"
            )
        }
        elseif ($Variant -eq "Mixin") {
            @(
                "Initialized engine CPython at",
                "UEP_MIXIN_THIRD_PERSON_SCRIPT_LOADED",
                "UEP_MIXIN_THIRD_PERSON_PROFILE_CLASSES_LOADED",
                "UEP_MIXIN_THIRD_PERSON_INTERFACE_REGISTERED",
                "UEP_MIXIN_THIRD_PERSON_CHARACTER_READY",
                "UEP_MIXIN_THIRD_PERSON_WORLD_READY",
                "UEP_PYTHON_THIRD_PERSON_GAMEPLAY_READY",
                "UEP_PYTHON_THIRD_PERSON_HUD_READY",
                "UEP_PYTHON_THIRD_PERSON_ROUND_COMPLETE",
                "UEP_PYTHON_THIRD_PERSON_HUD_RELEASED",
                "UEP_MIXIN_THIRD_PERSON_SMOKE_PASSED"
            )
        }
        else {
            @(
                "Initialized engine CPython at",
                "UEP_DEMO_SCRIPT_LOADED",
                "UEP_DEMO_WORLD_READY",
                "UEP_DEMO_SMOKE_PASSED"
            )
        }
        foreach ($marker in $requiredMarkers) {
            if (!$smokeLog.Contains($marker)) {
                throw "Demo log does not contain '$marker': $smokeLogPath"
            }
        }
        $variantFailureMarker = switch ($Variant) {
            "PythonFirst" { "UEP_PYTHON_THIRD_PERSON_SMOKE_FAILED" }
            "Mixin" { "UEP_MIXIN_THIRD_PERSON_SMOKE_FAILED" }
            default { "UEP_DEMO_SMOKE_FAILED" }
        }
        foreach ($failureMarker in @(
            "Fatal error:",
            "Assertion failed:",
            "Attaching UnrealEnginePython to the existing CPython interpreter",
            $variantFailureMarker
        )) {
            if ($smokeLog.Contains($failureMarker)) {
                throw "Demo log contains '$failureMarker': $smokeLogPath"
            }
        }
        Assert-CleanRuntimeLog $smokeLogPath

        $summary = [ordered]@{
            schema_version = 1
            status = "passed"
            run_id = $runId
            variant = $Variant
            engine = "$($engineVersion.MajorVersion).$($engineVersion.MinorVersion).$($engineVersion.PatchVersion)"
            project = $projectPath
            build_log = $buildLog
            smoke_log = $smokeLogPath
            smoke = $smokeReport
        }
        $summaryPath = Join-Path $resultRoot "summary.json"
        $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding utf8
        Write-Host "UEP Third Person $Variant demo smoke test passed."
        Write-Host "Summary: $summaryPath"
    }
    elseif ($Mode -eq "Package") {
        $packageRoot = Join-Path $resultRoot "Package"
        $packageLogRoot = Join-Path $resultRoot "package-uat"
        $packageLog = Join-Path $packageLogRoot "Log.txt"
        $gameBuildLog = Join-Path $resultRoot "build-game.log"
        $gameBuildArguments = @(
            $ubtPath,
            "UEPPythonThirdPerson",
            "Win64",
            "Development",
            "-Project=$projectPath",
            "-NoHotReload",
            "-NoMutex",
            "-NoUBA",
            "-MaxParallelActions=$MaxParallelActions",
            "-Log=$gameBuildLog"
        )
        Invoke-CheckedProcess -FilePath $dotnetPath -ArgumentList $gameBuildArguments -Label "Build packaged demo target" -WorkingDirectory $repoRoot -TimeoutSeconds 7200
        Assert-BuildLog $gameBuildLog

        $packageArguments = @(
            $automationToolPath,
            "BuildCookRun",
            "-project=$projectPath",
            "-noP4",
            "-utf8output",
            "-WaitForUATMutex",
            "-unattended",
            "-platform=Win64",
            "-clientconfig=Development",
            "-target=UEPPythonThirdPerson",
            "-skipbuild",
            "-SkipBuildEditor",
            "-cook",
            "-stage",
            "-pak",
            "-archive",
            "-archivedirectory=$packageRoot",
            "-map=/Game/ThirdPerson/Lvl_ThirdPerson",
            "-AdditionalCookerOptions=$disableNetworkPluginsArgument -SkipZenStore",
            "-nodebuginfo"
        )
        $packageEnvironment = @{
            uebp_LogFolder = $packageLogRoot
            uebp_FinalLogFolder = $packageLogRoot
        }
        Invoke-CheckedProcess -FilePath $dotnetPath -ArgumentList $packageArguments -Label "Cook and package $Variant demo" -WorkingDirectory $engineRootPath -TimeoutSeconds 3600 -EnvironmentVariables $packageEnvironment
        Assert-AutomationLog $packageLog
        $cookLog = Get-ChildItem -LiteralPath $packageLogRoot -Filter "Cook-*.txt" -File |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1 -ExpandProperty FullName
        if (!$cookLog) {
            throw "Cook log was not found under $packageLogRoot"
        }
        if ($Variant -eq "Mixin") {
            $cookLogContents = Get-Content -LiteralPath $cookLog -Raw
            if (!$cookLogContents.Contains("UEP_MIXIN_COMMANDLET_BOOTSTRAP_SKIPPED") -or
                $cookLogContents.Contains("Registered Python mixin")) {
                throw "Mixin Cook executed runtime router registration: $cookLog"
            }
        }

        $packagedExecutable = Get-ChildItem -LiteralPath $packageRoot -Filter "$demoName.exe" -File -Recurse |
            Where-Object { $_.FullName -match '[\\/]Binaries[\\/]Win64[\\/]' } |
            Select-Object -First 1 -ExpandProperty FullName
        if (!$packagedExecutable) {
            throw "Packaged executable was not found under $packageRoot"
        }

        $packagedResultPath = Join-Path $resultRoot "packaged-smoke.json"
        $packagedLogPath = Join-Path $resultRoot "packaged-smoke.log"
        $packagedGameUrl = if ($Variant -eq "PythonFirst") {
            "/Game/ThirdPerson/Lvl_ThirdPerson?game=/Engine/Transient.UEPThirdPersonGameMode"
        }
        else {
            "/Game/ThirdPerson/Lvl_ThirdPerson"
        }
        $packagedSmokeArgument = if ($Variant -eq "PythonFirst") {
            "-UEPPythonThirdPersonSmokeResult=$packagedResultPath"
        }
        else {
            "-UEPMixinThirdPersonSmokeResult=$packagedResultPath"
        }
        $packagedArguments = @(
            $packagedGameUrl,
            "-unattended",
            "-nop4",
            "-NullRHI",
            "-NoSound",
            "-NoSplash",
            "-UTF8Output",
            "-DisablePython",
            $disableNetworkPluginsArgument,
            $disableTraceServerArgument,
            $packagedSmokeArgument,
            "-abslog=$packagedLogPath"
        )
        Invoke-CheckedProcess -FilePath $packagedExecutable -ArgumentList $packagedArguments -Label "Run packaged $Variant demo" -WorkingDirectory (Split-Path -Parent $packagedExecutable) -TimeoutSeconds 300

        if (!(Test-Path -LiteralPath $packagedResultPath -PathType Leaf) -or
            !(Test-Path -LiteralPath $packagedLogPath -PathType Leaf)) {
            throw "Packaged demo did not create its smoke result and log"
        }
        $packagedReport = Get-Content -LiteralPath $packagedResultPath -Raw | ConvertFrom-Json
        if ($Variant -eq "PythonFirst") {
            Assert-PythonFirstReport `
                -Report $packagedReport `
                -ResultPath $packagedResultPath `
                -Label "packaged smoke"
        }
        else {
            Assert-MixinReport `
                -Report $packagedReport `
                -ResultPath $packagedResultPath `
                -Label "packaged smoke"
        }
        $packagedLogContents = Get-Content -LiteralPath $packagedLogPath -Raw
        $packagedMarkers = if ($Variant -eq "PythonFirst") {
            @(
                "Initialized engine CPython at",
                "UEP_PYTHON_THIRD_PERSON_SCRIPT_LOADED",
                "UEP_PYTHON_THIRD_PERSON_CLASSES_READY",
                "UEP_PYTHON_THIRD_PERSON_WORLD_READY",
                "UEP_PYTHON_THIRD_PERSON_GAMEPLAY_READY",
                "UEP_PYTHON_THIRD_PERSON_HUD_READY",
                "UEP_PYTHON_THIRD_PERSON_ROUND_COMPLETE",
                "UEP_PYTHON_THIRD_PERSON_HUD_RELEASED",
                "UEP_PYTHON_THIRD_PERSON_SMOKE_PASSED"
            )
        }
        else {
            @(
                "Initialized engine CPython at",
                "UEP_MIXIN_THIRD_PERSON_SCRIPT_LOADED",
                "UEP_MIXIN_THIRD_PERSON_PROFILE_CLASSES_LOADED",
                "UEP_MIXIN_THIRD_PERSON_INTERFACE_REGISTERED",
                "UEP_MIXIN_THIRD_PERSON_CHARACTER_READY",
                "UEP_MIXIN_THIRD_PERSON_WORLD_READY",
                "UEP_PYTHON_THIRD_PERSON_GAMEPLAY_READY",
                "UEP_PYTHON_THIRD_PERSON_HUD_READY",
                "UEP_PYTHON_THIRD_PERSON_ROUND_COMPLETE",
                "UEP_PYTHON_THIRD_PERSON_HUD_RELEASED",
                "UEP_MIXIN_THIRD_PERSON_SMOKE_PASSED"
            )
        }
        foreach ($marker in $packagedMarkers) {
            if (!$packagedLogContents.Contains($marker)) {
                throw "Packaged demo log does not contain '$marker': $packagedLogPath"
            }
        }
        $packagedFailureMarker = if ($Variant -eq "PythonFirst") {
            "UEP_PYTHON_THIRD_PERSON_SMOKE_FAILED"
        }
        else {
            "UEP_MIXIN_THIRD_PERSON_SMOKE_FAILED"
        }
        foreach ($failureMarker in @(
            "Fatal error:",
            "Assertion failed:",
            $packagedFailureMarker
        )) {
            if ($packagedLogContents.Contains($failureMarker)) {
                throw "Packaged demo log contains '$failureMarker': $packagedLogPath"
            }
        }
        Assert-CleanRuntimeLog $packagedLogPath

        $summary = [ordered]@{
            schema_version = 1
            status = "passed"
            run_id = $runId
            variant = $Variant
            engine = "$($engineVersion.MajorVersion).$($engineVersion.MinorVersion).$($engineVersion.PatchVersion)"
            project = $projectPath
            build_log = $buildLog
            game_build_log = $gameBuildLog
            package_log = $packageLog
            cook_log = $cookLog
            packaged_executable = $packagedExecutable
            packaged_smoke_log = $packagedLogPath
            packaged_smoke = $packagedReport
        }
        $summaryPath = Join-Path $resultRoot "summary.json"
        $summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryPath -Encoding utf8
        Write-Host "UEP Third Person $Variant packaged smoke test passed."
        Write-Host "Summary: $summaryPath"
    }
    elseif ($Mode -eq "Play") {
        $gameUrl = if ($Variant -eq "PythonFirst") {
            "/Game/ThirdPerson/Lvl_ThirdPerson?game=/Engine/Transient.UEPThirdPersonGameMode"
        }
        else {
            "/Game/ThirdPerson/Lvl_ThirdPerson"
        }
        $playArguments = @(
            $projectPath,
            $gameUrl,
            "-game",
            "-windowed",
            "-ResX=1280",
            "-ResY=720",
            "-DisablePython",
            $disableNetworkPluginsArgument,
            $disableTraceServerArgument,
            "-log"
        )
        $process = Start-Process -FilePath $editorPath -ArgumentList $playArguments -WorkingDirectory $stageRoot -PassThru
        Write-Host "Demo game launched (PID $($process.Id))."
    }
    elseif ($Mode -eq "Editor") {
        $process = Start-Process -FilePath $editorPath -ArgumentList @(
            $projectPath,
            "-DisablePython",
            $disableNetworkPluginsArgument,
            $disableTraceServerArgument
        ) -WorkingDirectory $stageRoot -PassThru
        Write-Host "Demo editor launched (PID $($process.Id)) for asset inspection."
        Write-Host "Use -Mode Play to launch the selected variant in Standalone."
    }
    else {
        Write-Host "UEP Third Person demo is ready."
    }

    Write-Host "Project: $projectPath"
}
catch {
    $failurePath = Join-Path $resultRoot "failure.txt"
    $_ | Out-String | Set-Content -LiteralPath $failurePath -Encoding utf8
    Write-Error "UEP Third Person demo failed. Details: $failurePath`n$($_.Exception.Message)"
    exit 1
}
