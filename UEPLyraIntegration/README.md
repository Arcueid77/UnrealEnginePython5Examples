# UEP Lyra integration

Current development covers bounded 0.9–0.11 BP-business batches on upstream
UE 5.8.1/CPython 3.11; the latest release tag remains 0.7.0. See
[PROGRESS](Migration/PROGRESS.md), the static [inventory](Migration/batches.json)
and [per-batch acceptance ledgers](Migration/Acceptance/) for current scope.
Earlier milestone sections below preserve their original qualification and
must not be read as a fresh current-DLL result. Accepted batches receive an
isolated staged-tree check and local commit; unfinished drafts remain out.

This integration is staged into a disposable Lyra copy; neither Lyra nor
Unreal Engine source is edited. `UEPLyraBridge` translates the few native Lyra
lifecycle observations and the one bounded write operation that Python cannot
bind safely into reflected, game-thread-only APIs:

- Experience readiness becomes a dynamic multicast event;
- Game Feature state, Enhanced Input readiness, Ability System/Health readiness,
  damage immunity, authority, net mode, local/remote controllers, PlayerState
  and pawn roles are exposed as a read-only snapshot;
- the subsystem and its listeners follow `UWorld` lifetime, and the Python
  probe explicitly unbinds its callback before shutdown or reload; late client
  `GameState` assignment is observed before binding the Experience manager;
- `ApplyAuthorityHealthDelta` accepts only game-thread server authority, one
  unambiguous local/remote player target, a short safe command ID, a finite
  non-zero delta no larger than 25, non-lethal damage and non-overhealing
  restoration;
- accepted commands dispatch Lyra's existing SetByCaller Damage/Heal Gameplay
  Effects through the target ASC. The bridge never writes the Health attribute
  directly and respects Lyra's `Gameplay.DamageImmunity`; and
- command IDs are consumed once, clients receive `RejectedNotAuthority`, and no
  bridge API silently forwards a client call as an RPC.

The 0.8 overlay additionally configures Lyra's existing `W_Healthbar_C` for a
declared UEP Mixin Set. CommonUI and the ShooterCore `Add Widgets` action retain
widget ownership. Python replaces only presentation behavior: it handles the
widget lifecycle, follows the possessed Pawn, subscribes to Health Component
delegates, calculates normalized health and invokes the Blueprint's retained
visual helpers. Dedicated servers must record zero HUD objects or subscriptions.

0.8 is an unreleased candidate. Health data updates, damage/heal/death/respawn
animation selection and numeric interpolation pass a real-UMG isolated fixture.
Exactly-one active presenter and post-shutdown zero owned
callbacks have host-tested checks and a current-script Unreal Standalone pass;
current-source combined network/package acceptance remains open. Existing cleanup
paths/logs do not establish an observed leak.

## 0.9 first runtime BP batch (in development)

The inventory at [`Migration/batches.json`](Migration/batches.json) assigns
246 runtime business candidates to 0.9–0.14, separately retaining animation,
editor/test tools and 182 configuration/layout shells. These are static
candidates, not a migrated or reachable-asset count. Batch 1A is the health bar
plus four weapon widgets. Its bounded UI/native-network evidence is recorded
in the batch ledgers; full-version release/package gates remain separate.

`Overlay/Content/Scripts/uep_lyra_hud/ammo_mixin.py` implements the weapon panel
Tick and touch-reload input event, and the three ammo counters' Tick,
OnWeaponInitialized and SetWeaponSpecificImages. `Overlay/Plugins/GameFeatures/
ShooterCore/Content` contains the four example-owned BP copies. Their Interface
and `PythonMixinProfile` CDO default reference the four Mixin Sets under
`Overlay/Content/UEPMixins`. Lyra/CommonUI still instantiate the original
`W_*_C` classes; no Python subclass replaces them. The official project is never
saved by the authoring tool, which requires both a marked stage and a matching
current Unreal project before mutation.

Python reads the owning controller's native QuickBar/inventory tag counts and
calls native UMG, material, FText and Enhanced Input functions. Inventory,
equipment, firing/reload abilities, GAS and replication remain native. UMG
layouts/materials are retained. The weapon name setter is disconnected in the
original BP; its placeholder is intentionally preserved instead of introducing
a behavior change during migration. The current port also preserves the BP's
Tick polling; the roadmap's event-driven ammo subscription work is still open.

For repeatable first-batch UI comparisons without any compilation or asset save,
run this core-checkout entry against an already matching full-content stage:
Use PowerShell 7.

```powershell
.\Validation\Run-UEP58FocusedWeaponHUDValidation.ps1 `
    -StageProject F:\UnrealEnginePython5\.build\LyraValidation\Full\Stage\Lyra\LyraStarterGame.uproject `
    -OutputDirectory F:\UnrealEnginePython5\.build\LyraValidation\WeaponHUD-NewRun `
    -CheckPlayableStartup
```

The 2026-10-13 run passes 42 real-UMG original-BP/Python comparisons using the
persisted Interface/CDO default, plus strict logs, unchanged classes, four router
restorations, input/reference hashes and a rendered two-column frame (BP left,
Python right). The reload-button case checks native input dispatch, **not** a
successful GAS reload. The isolated Entry-map inventory is deterministic fixture
input, not evidence that real equipment/firing or replication works.
`-CheckPlayableStartup` launches normal Lyra with no UEP probe flags, observes
it alive for 20 seconds after native Experience load, then intentionally stops
only that owned process. It is NullRHI and does not test graceful shutdown or
interactive controls. Normal `ue_site.py` no longer imports the auto-exit probe;
validation remains explicit and opt-in.

First-batch acceptance still needs real weapon fire/reload, two-client ammo/UI
ownership, Pawn/weapon replacement and event-driven subscription cleanup. The
separate passing Health network lane does not certify these new ammo scenarios.
The focused weapon summary always leaves full/network acceptance false.

## Existing validation lanes

The source-only smoke lane disables Lyra's content-backed startup systems in
the disposable stage so it can prove UE5.8 compilation, module loading,
CPython 3.11 ownership and bridge lifecycle without pretending that gameplay
works. The complete external project at
`F:\LyraStarterGame\LyraStarterGame.uproject` passes strict readiness, real
Experience gameplay, synchronized multiplayer, cook/package and packaged
CPython validation without modifying the reference tree.

From the core checkout, run the existing combined runtime/package lane against
a complete project outside the engine tree:

```powershell
.\Validation\Run-UEP58LyraValidation.ps1 `
    -EngineRoot F:\UnrealEngine `
    -LyraProject F:\LyraStarterGame\LyraStarterGame.uproject `
    -Mode All
```

`All` performs a full cook/package and now invokes `HUDAudit` when the HUD slice
is enabled, and requires the precompiled cross-Actor and rendered UMG checks.
Current-source combined release acceptance is still pending. Use `Standalone` or
`Network` for iteration. Audit the relevant official/staged assets separately without runtime
gameplay:

```powershell
.\Validation\Run-UEP58LyraValidation.ps1 `
    -EngineRoot F:\UnrealEngine `
    -LyraProject F:\LyraStarterGame\LyraStarterGame.uproject `
    -Mode HUDAudit
```

Regenerate the example-owned health-bar and Mixin Set assets only after their
declaration changes:

```powershell
.\Validation\Run-UEP58LyraValidation.ps1 `
    -EngineRoot F:\UnrealEngine `
    -LyraProject F:\LyraStarterGame\LyraStarterGame.uproject `
    -Mode GenerateHUDAssets `
    -Incremental
```

Generation occurs in the disposable stage and SHA-256 checks prove the
reference `W_Healthbar.uasset` was not changed.

Every full-driver mode first runs the host-side Python tests in `Tests` and
core-side PowerShell contract checks. They use fake
reflected objects to prove source-only asset absence, exact callback identity,
event-only updates, old-Pawn detachment, Blueprint fallback, Destruct and
registry teardown without starting Unreal. Runtime lanes exercise real Lyra
objects. The strengthened exact-one-presenter and final post-exit checks have
host coverage, including actual CPython-only subprocess finalization, and a
current-script Unreal Standalone pass. Repeat full current-source acceptance;
host fakes alone cannot certify it.

For focused self-acceptance without a build, run from the core checkout:

```powershell
.\Validation\Run-UEP58FocusedHUDValidation.ps1 `
    -StageProject F:\UnrealEnginePython5\.build\LyraValidation\Full\Stage\Lyra\LyraStarterGame.uproject `
    -OutputDirectory F:\UnrealEnginePython5\.build\LyraValidation\Focused-NewRun
```

The script requires a fresh output directory, verifies the marked stage's
native source/module parity and syncs current example scripts. It does not
compile C++, cook/package, save BPs or repair module BuildIds. `Callsite` mode
compiles two temporary in-memory BPs before Mixin registration and verifies
two same-class Actor targets through another BP's bytecode. `Visual` opens an
isolated real-UMG test window and records eight frames plus post-exit cleanup.
The test-only health reader is never attached to a Lyra Pawn/ASC; death coverage
does not expand bridge authority. Shader caches may be populated. Focused
`All` runs both checks and always leaves `full_acceptance: false`.

For real two-client loopback networking, use the core checkout's no-build
`Validation/Run-UEP58FocusedNetworkValidation.ps1` with `-StageProject`, a fresh
`-OutputDirectory`, and `-ClientCount 2`. It runs a dedicated server, A and B0;
B0 then exits and B1 rejoins. `uep_lyra_network.py` is opt-in and does not run
in normal gameplay or commandlets. The original single-client probe remains
available through the core driver's `NetworkPrecheck`; `Network/All` now use
the two-client gate.

`CapturePlayerSnapshots` exposes WorldToken, PlayerToken, PlayerState identity
and Controller/Pawn/HealthComponent paths. `ApplyAuthorityHealthDeltaToPlayer`
and `RequestPlayerRestart` resolve only current same-World weak Controller
references; expired/foreign tokens never fall back to another player. Existing
role-only targeting retains `RejectedAmbiguousTarget`, and authority, bounded
non-lethal GAS writes and command deduplication are unchanged. Tokens are
process/World-local test targeting handles, not an authentication or RPC API.

The 20-phase probe cross-checks independently read native snapshots and fresh
owned Health delegate events. Files coordinate ACKs only; Health still reaches
clients through Lyra's native replication. Three native bots satisfy Warmup,
with their AI brain logic stopped only in this opt-in test mode to avoid random
gunfire. Each process must exit with no presenter-owned callbacks/references.
NullRHI does not establish visual network acceptance or packaged networking.
It also repeats the rendered case with `-SwitchDuringAnimation`, proving that
switching to `BlueprintFallback` immediately after a new damage animation
closes the Python presenter without completion reentry. Native UMG owns its
paused animation state. The core plugin's zero-sized native-event fallback fix
is required for the subsequent original `Destruct` call.

The Python probe owns the gameplay sequence. In Standalone and the packaged
game it waits for Lyra damage immunity to end, applies 10 damage, proves the
same command ID cannot apply twice, observes 90 health, heals 10 and observes
the original 100 health. In the network lane:

1. the client calls the same reflected API and proves `RejectedNotAuthority`
   without a health change;
2. the dedicated-server Python process applies the damage to the real remote
   player's ASC and proves duplicate rejection;
3. the client Python process observes replicated health at 90 before
   acknowledging the server; and
4. server Python restores health only after that acknowledgement, then waits
   until client Python observes the replicated value at 100.

Both peers then publish a readiness marker and wait behind one driver-owned
release signal. Only after both markers exist can either process shut down.

After the health sequence, the 0.8 lifecycle phase replaces the authoritative
Pawn and verifies that the client presenter drops the old Health Component
before binding the new one. It then performs one same-map Experience
replacement to exercise the real `LAS_ShooterGame_StandardHUD` `Add Widgets`
action teardown/recreation, followed by a second independent same-map travel.
The client must finish with at least three Constructs, two Destructs and one
balanced active presenter. The updated validator rejects multiple active
presenters even if counts balance. Schema 5 writes `awaiting_shutdown`, retains
the active snapshot in `hud`, and finalizes `shutdown.hud` from Python `atexit`
after Mixin cleanup. The driver requires zero owned callbacks/references and
ordered final markers after process exit. This path has host tests and a
current-script Unreal Standalone pass; the new network/package exit gates
remain unverified. The server participates in the authority/
synchronization path but never creates a HUD.

Each process latches the snapshot that produced its readiness marker while it
waits on the release signal. A client that exits one tick earlier therefore
cannot erase the server's already-proven remote Pawn/PlayerState/ASC state.

The gameplay contract requires `ShooterCore` to be Active and the content-only
`ShooterMaps` plugin to be at least Registered, matching its
`ExplicitlyLoaded`/`BuiltInInitialFeatureState=Registered` descriptor. It does
not force feature activation from Python. Runtime URLs request three Lyra AI
bots to advance the real Warmup phase; bots use `AModularAIController` and are
not candidates for the remote `APlayerController` target selector.

See [`docs/Lyra_Gameplay_Slice_0.5.0.md`](https://github.com/AvaloNero/UnrealEnginePython5/blob/dev/release-0.6.0/docs/Lyra_Gameplay_Slice_0.5.0.md)
for the ownership table, rejection contract and machine-readable evidence.
Formal result `20260812-234501` passed the complete `All` lane, including the
packaged game, and reported `full_acceptance: true`. After the selector was
hardened to reject ambiguous human targets, exact-source result
`20260813-005436` passed the Network lane and `20260813-005835` passed
Standalone. No package was rebuilt after that small hardening change; the
former result remains historical package evidence and the latter two are
exact-source runtime evidence for that 0.5 selector change, not today's tree.

Historical 0.8 supporting records include HUD audit result
`20260903-032632`, clean-base generation results `20260903-033001` and
`20260903-033049`, and formal `All` result `20260903-033426`. The latter passes
Standalone, synchronized server/client, BuildCookRun and packaged runtime with
`full_acceptance: true`, CPython 3.11.8, `100 -> 90 -> 100` on every UI role,
3 Constructs / 2 Destructs after two Experience lifecycles, and zero dedicated-
server HUD state. It is a Win64 Development, NullRHI run with `hud_audit: null`:
the audit/generation above are separate invocations, not steps in `All`.
It predates the final bootstrap fix/seventh host test and is neither current-
source release approval nor rendered animation, DebugGame or Shipping evidence.

The first 2026-09-07 Editor attempt failed on mismatched module BuildIds.
Official UBT then repaired the generated records in two metadata-only actions,
without a manual GUID override, C++ compile, cook or asset save. The fresh strict
HUD audit and current-script NullRHI Standalone passed: exactly one active
presenter/reference, then zero of both after actual Python exit, controller
bindings 3/3 and health bindings 6/6. The core validation history retains
`20260907-hud-closeout/standalone-shutdown-summary.json` with script/native
hashes and explicit `full_acceptance: false`. Integrated `All`, synchronized
network and package checks remain outstanding. On 2026-09-10, the
`20260910-hud-closeout-integrated` focused run passed cross-Actor routing,
damage/heal/death/respawn rendering, real numeric interpolation and final
zero owned widget/callback state. This is presentation/routing evidence,
not a native GAS, synchronized multiplayer or packaged-runtime replacement.

0.8 closeout stays on the health bar. 0.9 focuses on Mixin engineering plus one
weapon/ammo HUD chain and a bounded message subscription surface. The remaining
runtime BP business is assigned to 0.10–0.14 in the core roadmap, normally in
five-to-ten-BP batches with original-BP/Python differential acceptance.
The initial inventory and version assignments are in `Migration/batches.json`.
Animation, editor/test utilities and data/layout shells remain; game-project
C++ business migration is a separate later scope. Death validation must use native Lyra gameplay or an
isolated fixture without expanding the bridge's non-lethal authority contract.

The 2026-10-13 Batch 1A runtime follow-up now verifies the four weapon/ammo
widgets through 42 BP/Python UMG comparisons, four live Profile round trips,
native message cancellation and three controlled reload/native-GC cycles.
`WeaponNetwork08` runs 19 real-input phases with one dedicated Editor server and
two rendered clients: native firing/GAS reload, depletion, existing pickup
entry/slot switch, Pawn restart, two travels and client exit/rejoin. Ammo and
HUD stay with each local owner; the probe does not write inventory/ammo.
Physical overlap pickup is a separate untested scenario.

`weapon_observer.py` owns one read-only frame sampler plus native QuickBar/Pawn
signals and shared subscription scopes. StatTags has no public ammo delegate;
the source is explicitly `read-only-frame-sampler`. Presentation updates only
when values/ownership change. Generic scope support lives in UEP, not in the
Lyra bridge. The actual packaged presentation/lifetime fixture also passes
after the runtime plugin-script import fix.

`Migration/batches.json` distinguishes bounded runtime verification from
publication. Dedicated packaged networking remains open: native LyraGame
cannot act as LyraServer, and mixed Editor/cooked World Partition peers were
rejected. The full Server build is a separate 1,235-action cold plan. CC review
timed out twice. These are retained limitations, not green release evidence.

0.10's next two pilots keep `W_Reticle_AmmoBar_C` and `W_FireButton_C`, with
persisted Interface/Mixin Set/CDO configuration in example-owned copies.
`fire_button_mixin.py` replaces the authored CommonButton bound-click entry,
injecting the original Fire/Fire_Auto actions with FVector(1,1,1). Its original
BP Profile remains available. The test invokes that entry programmatically;
physical touchscreen/input-widget gesture behavior is not certified.

`CombatHUDNetwork04` passes 19 native weapon phases, two rendered clients,
two travels, Pawn/weapon replacement and B0 exit/B1 rejoin. All four processes
exit 0; A/B0/B1 subscriptions balance 17/17, 13/13 and 3/3, with zero final
scopes/ticker. Eight screenshots and native UI/weapon comparisons are retained.
The original three weapon definitions do **not** use `W_Reticle_AmmoBar`:
its explicit test-owned overlay initializes from the actual production ammo
counter's WeaponInstance. No definition is changed to manufacture reachability.
Package/physical-touch and the other 30 candidates remain open.

Visual review found and repaired two issues despite an earlier protocol pass:
the fixture used UEP's Roll-first FRotator constructor as though it were
Pitch-first; native Pitch/Roll are now reported and asserted. A pre-ASC 0/0
health read followed by an identical 100/100 attribute notification left the
UI eliminated. The presenter now recognizes the previously displayed zero
state; `HealthBootstrapRegression01` covers recovery, normal health animations
and live Profile cleanup. Examples host tests pass 111. No C++ compile or
cook/package was performed for this follow-up; older artifacts remain historical.

The world-interaction pilot is `uep_lyra_world.effect_pad_mixin` on the retained
`BP_GameplayEffectPad_C` and unchanged child class. Eight deferred-spawn
BP/Python construction cases pass. `PhysicalGAS03` passes eight cases / sixteen
real overlap rounds on a native Lyra Pawn, with matching damage/healing and
complete source-effect removal. Pawn teleports, not manual input, drive collision.
The parent construction retains a two-node virtual `UEPConstructEffectPad`
forwarder; the saved original BP business is the fallback helper body. Child
explicit Parent calls therefore reach Python using just the parent router.
The related-class router guard and general cached-pointer bypass boundary stay.
Editor-only incremental builds, inherited selector and seven call fixtures
pass; host tests pass 126 at this gate. `PadNetwork02` passes sixteen
server-physical/native-GAS cases with two clients, per-owner Health/HUD and
three clean exits. It does not certify client effect prediction, forced pad
replication, manual pad input, production reachability or packaging. 0.10
remains in development.

`debug_spread_mixin.py` migrates the authored debug spread Tick while retaining
native ComputeSpreadAngle and exact Kismet double-to-text formatting defaults.
`DebugSpreadNetwork01` passes the 19-phase weapon/CombatHUD lane with `-DebugSpread`:
automatic native widget Tick, nonzero spread, BP/Python/native text, ownership,
travel/Pawn/weapon changes and rejoin. Four exits are clean. The debug overlay
is test-owned, not claimed as a production widget. Eight PNGs are retained;
native NoSound EarlyReflections and EditorDataStorage widget-purpose warnings
remain visible/logged. This is not warning-free or packaged acceptance.
Examples host tests pass 135; no new C++ build/cook/package was needed here.

`weapon_reticle_mixin.py` now owns the three retained production reticle
layouts' geometry Tick and typed ADS/elimination subscriptions. The original
ADS animation chain is disconnected, so that animation remains a no-op.
Elimination uses LyraPlayerState ownership and excludes suicide; native UMG
animation/projection/spread execution is retained. The shared twelve-node
`BP_UEPGameplayMessages` is only a typed VM transport adapter (native wildcard
GetPayload/Broadcast), not copied gameplay business. `transport01` and
`ReticleDifferential04` pass native typed delivery, three layouts on the same
equipped pistol, BP/Python geometry and animation time, owner/suicide filtering
and five final closed scopes. Host tests pass 141; core subscription tests 13.
`ProductionReticleNetwork01` passes nineteen native weapon/lifetime phases with
actual production Pistol/Rifle widgets and zero post-exit scopes. Real IA_ADS
press/release succeeds in `ReticleNativeADS05`. `ReticleNativeShotgun06` uses
native pickup/equip/fire (8->5 ammo) and compares every layout on that native
shotgun. Physical pickup, real kill input, network shotgun and packages remain
pending; reference assets are untouched. Host tests now pass 148.

`open_menu_mixin.py` migrates the original menu-button bound click. The same
native CommonUI async action receives UI.Layer.Menu, input suspension and a
lazy soft-class path; Python does not load the class first. `MenuDifferential04`
passes three Python/BP/Python native open/close cycles with retained button
type, an initially unloaded class, clean exit and inspected menu PNG. Core
soft-class conversion and eight current-DLL call fixtures pass after module-
only builds. Physical touch, input-token cancellation/resumption, production
reachability, network menus and packages remain separate acceptance work.

`reticle_host_mixin.py` migrates the actual production host's creation/clear,
health observation and visibility. Native LyraWeaponUserInterface Tick still
detects equipment changes; the original inventory fragments and UMG classes
remain. `HostDifferential02` passes eight original-BP comparisons, live Profile
child preservation, native Pistol/Rifle/Shotgun equip and one-shot native death
event handling. The injected event is not a real lethal-damage/kill proof.
The four-node VM helper only removes the old BP death delegate during cleanup.
`ReticleHostNetwork01` passes nineteen phases with two clients, travel/rejoin,
native child/owner/configuration checkpoints and final host scopes 7/7, 5/5,
1/1 (server 0/0). Screenshots and known native warnings are retained. Host tests
pass 170; physical pickup, network shotgun, packages and full 0.10 stay open.
