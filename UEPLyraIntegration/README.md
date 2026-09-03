# UEP Lyra integration

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

The source-only smoke lane disables Lyra's content-backed startup systems in
the disposable stage so it can prove UE5.8 compilation, module loading,
CPython 3.11 ownership and bridge lifecycle without pretending that gameplay
works. The complete external project at
`F:\LyraStarterGame\LyraStarterGame.uproject` passes strict readiness, real
Experience gameplay, synchronized multiplayer, cook/package and packaged
CPython validation without modifying the reference tree.

To repeat every 0.8.0 gate against a complete project outside the engine tree:

```powershell
.\Validation\Run-UEP58LyraValidation.ps1 `
    -EngineRoot F:\UnrealEngine `
    -LyraProject F:\LyraStarterGame\LyraStarterGame.uproject `
    -Mode All
```

`All` performs a full cook/package. During iteration, use `Standalone` or
`Network`. Audit the relevant official/staged assets without runtime gameplay:

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

Every driver mode first runs the seven host-side tests in `Tests`. They use fake
reflected objects to prove source-only asset absence, exact callback identity,
event-only updates, old-Pawn detachment, Blueprint fallback, Destruct and
registry teardown without starting Unreal. Runtime lanes then prove the same
contracts against real Lyra objects.

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
balanced active presenter. The server participates in the authority/
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
former result remains package evidence and the latter two are current-source
runtime evidence.

The current 0.8 implementation is covered by HUD audit result
`20260903-032632`, clean-base generation results `20260903-033001` and
`20260903-033049`, and formal `All` result `20260903-033426`. The latter passes
Standalone, synchronized server/client, BuildCookRun and packaged runtime with
`full_acceptance: true`, CPython 3.11.8, `100 -> 90 -> 100` on every UI role,
3 Constructs / 2 Destructs after two Experience lifecycles, and zero dedicated-
server HUD state.
