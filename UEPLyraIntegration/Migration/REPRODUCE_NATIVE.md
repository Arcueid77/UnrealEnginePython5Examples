[English](REPRODUCE_NATIVE.md) | [简体中文](REPRODUCE_NATIVE.zh-CN.md)

# Reproduce the current native migration

Use the checked-out main repository and its matching `Demos` revision on Windows,
the reviewed UE5.8.1 engine with working Development binaries, its CPython3.11,
Visual Studio C++ tools, and the original Lyra reference project. This workflow
does not install an engine or change the original project. The accepted target
is Win64 Development; other platforms, Shipping and physical input are separate.

From the main repository, select unused stage and evidence paths under `.build`:

```powershell
./Validation/Run-UEP58NativeReproduction.ps1 `
  -EngineRoot F:/UnrealEngine `
  -ReferenceProject F:/LyraStarterGame `
  -StageRoot F:/UnrealEnginePython5/.build/LyraValidation/CppGameplayExtended/FreshRun/Lyra `
  -OutputDirectory F:/UnrealEnginePython5/.build/LyraValidation/Hardening/FreshRun `
  -UsePrecompiledEngine `
  -MaxParallelActions 3
```

The entry point makes independent source/content copies, composes all 63 current
production C++ outputs from fifteen versioned recipes, and stages the current
SDK, bridge, Python, Blueprint assets and native validation fixtures. It compares
the final staged files with the ordered original/overlay/patch composition.
Previous `Binaries`, `Intermediate`, caches and compiled results are excluded.
The owned descriptor enables SDK/bridge and disables AndroidFileServer plus the
reference-only RuntimeTests/ShooterTests plugins, matching the accepted production
stage. This avoids enabling unrelated, unavailable Engine test modules. It
reviews compile/link actions for the project's 23 production modules, rejecting any
output outside the stage, builds those modules against the existing engine, and
writes loader manifests only beside their new DLLs using the unchanged Engine
BuildId. Full-target metadata refresh would also touch existing Engine manifests;
explicit project module selection keeps the engine protected. The entry point runs
thirteen real native exception/recovery cases in the new stage. Protected Engine
fingerprints and all frozen build inputs are checked before acceptance. No OS
desktop or keyboard control is performed.

`-PrepareOnly` stops before compilation and runtime. Its `prepare.json` can be
passed to a later invocation with `-PreparedStageReport`. If sources change before
the first build, `Tools/prepare_native_reproduction.py --refresh-unbuilt` creates
a new preparation report while retaining its parent proof. It refuses a stage
that already contains compiler outputs.

A failed build keeps its stage and logs. When those source and Engine fingerprints
are unchanged, pass the failed attempt's `summary.json` with `-ResumeBuildFrom`
and use a new evidence directory to continue that same fresh stage incrementally.
This does not import results from another stage. `-UsePrecompiledEngine` is an
explicit option for an installed/precompiled engine workflow; `-NoEngineChanges`
remains enabled.

For a preparation created before the test-plugin configuration was included,
`--configure-production` derives a new report, saves the previous descriptor and
changes only those two enabled flags. The resume gate accepts that exact documented
configuration derivation while still rejecting other staged/source changes.

Game delivery uses the same resulting stage through the following separate gates:

1. `Run-UEP58PackagedNativeFixtureAuthoring.ps1` creates three stage-only typed
   message observers and verifies production assets are unchanged.
2. `Run-UEP58CurrentLyraGameBuild.ps1` builds the Game target, which uses different
   compilation settings from the Editor target.
3. `Tools/plan_native_hardening_package.py` pins the complete original 246-asset
   migration inventory, current overlay/scripts/maps, and the three observers.
4. `Run-UEP58MigrationCookPackage.ps1` cooks and archives those exact inputs and
   compares the actual container listing with the inventory.
5. `Run-UEP58PackagedNativeValidation.ps1` directly executes the package's inner
   `LyraGame.exe` for exception/recovery and normal offline frontend flows.
6. `Run-UEP58PackagedNativeNetwork.ps1` executes that same package as an authority
   and two real clients for each of the Damage and Pawn policy families.

After the fresh Editor stage passes, the following prepares the observers and
Game build, then runs the package-delivery entry point. Use unused evidence paths;
the entry point refuses to replace closed evidence.

```powershell
$nativeStage = 'F:/UnrealEnginePython5/.build/LyraValidation/CppGameplayExtended/FreshRun/Lyra/LyraStarterGame.uproject'
$nativeEvidence = 'F:/UnrealEnginePython5/.build/LyraValidation/Hardening/FreshRun'
./Validation/Run-UEP58PackagedNativeFixtureAuthoring.ps1 `
  -StageProject $nativeStage -OutputDirectory "$nativeEvidence/H04-Fixtures01"
./Validation/Run-UEP58CurrentLyraGameBuild.ps1 `
  -StageProject $nativeStage -OutputDirectory "$nativeEvidence/H04-GameBuild01" `
  -MaxParallelActions 3
./Validation/Run-UEP58NativePackageDelivery.ps1 `
  -StageProject $nativeStage -OutputDirectory $nativeEvidence
```

The first Game configuration compiles its runtime libraries inside the project,
separately from Editor modules. Subsequent package/runtime checks reuse that build.
The cook selects the reviewed `UnrealEditor-Cmd.exe` explicitly, rather than requiring
an Editor target receipt from the module-only reproduction build. A failed cook
can keep its frozen plan and use a fresh `-CookAttempt` with `-ReusePackagePlan`;
successful native runtime leaves are not repeated to repair only a pure gate.

The packaged Game executable supports a listen authority via `?listen`; its
`-server` switch does not provide an Editor dedicated process. The driver removes
the host LocalPlayer with the native Development command and keeps two real remote
clients. A separate pure checker expects preserved listen UI/local cosmetic
completion while retaining every other Reset, RPC, ownership, restoration and
independent client-view assertion. These results make no Dedicated Server target
claim. Gameplay transport uses native RPCs; files only schedule trials and ACKs.

The packaged checks compare current Python payloads, the Game executable and
containers. They also inspect the actual loaded CPython DLL, its configured home
and staged runtime receipt files to reject a source-engine runtime fallback.
Every dependency hash is strict except exact UTF-8 BOM/CRLF equivalence for staged
INI text. Original failed summaries and raw native reports remain intact when
only a pure contract needs a separate review; no peer report is rewritten.
Cooked presence alone does not prove the behavior of every original candidate.
CPP09's separate actual desktop Escape/Menu acceptance passed on 2026-11-05;
these headless/package gates retain their own scope.
