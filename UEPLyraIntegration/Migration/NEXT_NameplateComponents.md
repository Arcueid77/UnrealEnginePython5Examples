# Next bounded nameplate group: Source and Manager

Historical batch plan/checkpoint. Source/Manager follow-up is now separately
recorded in PROGRESS.md and Acceptance/10-nameplates.json. Preserve the earlier
limitations below; this is not the current next task or a fresh native run.

The Widget is accepted only in `20261015-ue581-acceptance/NameplateDifferential06`:
14 native/BP comparisons, scopes 23/23, team proxies 13/13 and init delegates
10/10 explicitly removed. This is NOT Source/Manager or multiplayer acceptance.
The latest source-matching Lyra UEP DLL is A37911F9... (full hash in PROGRESS).
Do not replace it with a preceding DLL or force module BuildIds.

## Verified native boundaries

- `CompareTeams` is reflected as `(ReturnValue, TeamIdA, TeamIdB)`, not a scalar.
- Use `world.get_world_type()` and nullable GameplayStatics.GetPlayerController.
- WidgetBlueprintLibrary.GetAllWidgetsOfClass has one out-array; there is no
  `ue.get_objects` API. Retain the return handle from `ue.add_ticker`.
- The existing `object.broadcast` now uses the property-value address; native
  empty/bound/rejection/recovery/unsubscribe proof is in CallMatrix02. Do not
  invent `broadcast_event` or suppress access-detector errors.
- Native Actor.AddComponentByClass / FinishAddComponent implement the BP Add
  Component node. For a test-owned BP baseline, defer finish, choose its
  per-instance Profile, then finish so the actual native lifecycle runs. Do not
  call ReceiveBeginPlay/ReceiveEndPlay manually to manufacture coverage.
- LyraIndicatorManagerComponent.Indicators is a reflected array usable for
  read-only native membership evidence. Its C++ GetIndicators convenience
  method and IndicatorDescriptor.GetIndicatorManagerComponent are NOT reflected
  UFunctions; do not invoke those names through ProcessEvent.
- IndicatorDescriptor's reflected getters expose DataObject, SceneComponent,
  IndicatorClass, projection/anchor/offset/alignment, clamp/auto-remove and
  desired visibility. Descriptor UnregisterIndicator is reflected too.

## Execution order and gates

1. Finish/check the existing Network03 process and its final report before
   touching frozen script/asset inputs or starting another Editor process.
2. Run `Run-UEP58NameplateComponentsAssetAuthoring.ps1` into a fresh directory
   against the marked Lyra stage. Require both retained component BP classes,
   serialized Interface/CDO, 19 typed VM functions / 59 nodes, and unchanged
   semantic digests for all 15 previous functions. Only accepted outputs may
   be copied to Examples; official Lyra must retain its hashes.
3. Build a bounded component differential using the actual production local
   manager and a same-class original-BP baseline selected before native finish.
   Read native Indicators and compare descriptor configuration and Pawn maps,
   not just Python counters or mock-generated expected values.
4. Exercise typed Discover/Add/Remove through the compiled VM adapter, native
   Source component destruction, per-instance Profile/resume and exact cleanup.
   Test-owned Character/Pawn/component objects must be identified and cleaned;
   do not write native Health/team/inventory state or replay lifecycle events.
5. Confirm the audited repeated-Pawn behavior against real original BP:
   replacing a Map value can leave the former descriptor registered. Record
   native membership on both sides and fixture-only cleanup explicitly. Do not
   silently deduplicate the production policy or mislabel the mock as proof.
6. Rerun Widget differential and old typed-transport cases after extension.
   Existing authoring reports freeze asset SHA-256 values: extending the shared
   transport invalidates an older report's transport hash. Preserve old reports;
   create a fresh accepted capability/asset-chain report instead of rewriting
   hashes, weakening the driver, or claiming the old 15-function report covers 19.
7. Add nameplate-specific evidence to the two-client travel/respawn/rejoin lane:
   local-manager eligibility, per-Pawn discovery/removal, native indicators,
   Widget/Source/Manager final scopes/proxies/helper roots and no late delivery.
   Passing the older HUD network switches alone does not certify nameplates.

The current 397 host checks are policy/negative/entry-point tests, not these
native cases. Keep native damage production, team reassignment and projection
parity separate unless actually exercised. Do not cook/package, rebuild Engine,
commit, push, tag or release an unfinished version. Preserve mixed worktrees,
animation/editor/test tools, official Engine/Lyra and the `.nepy` boundary.
