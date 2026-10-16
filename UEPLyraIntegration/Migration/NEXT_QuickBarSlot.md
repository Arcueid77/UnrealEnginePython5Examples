# 0.10-2K Quickbar slot

Historical batch plan/checkpoint. Current accepted work and remaining gaps are
recorded in PROGRESS.md and Acceptance/09-quickbar-slot.json; the dated
observations below are retained, not a new current-DLL result or next task.

Status: bounded display/native-network/lifecycle evidence is accepted on the
former query-retaining version. Named-output core dispatch now passes its
ten-lane matrix, and QuickBarDifferential03 passes twelve cases on the new
DLL/query (nine Python query calls, scopes12/12). QuickBarRespawnNetwork03
passes nineteen phases/two travels/rejoin/four normal exits; A/B0/B1 query
counts 15/8/2, scopes12/12,12/12,6/6 and inspected selected screenshots.
Affected standalone/native lifecycle regressions are still open, now held by
a shared Engine binary/BuildId change from another build. Do not relabel old
manifests to bypass compatibility. Keep 0.10.0 open.

`IsThisTheActiveQuickbarSlot` now opts in with `uep_named_outputs=True` and
returns `{"IsActive": bool}`. Internal entries use the routed UFunction too;
BlueprintFallback deliberately omits that method and really uses preserved BP
bytecode/output propagation. No class replacement or Engine source edit.

Retain `/ShooterCore/UserInterface/HUD/W_QuickBarSlot.W_QuickBarSlot_C`, its
native LyraTaggedWidget parent, designer widgets/animations, input actions and
the enclosing quickbar layout. The captured official audit contains 106 nodes.
Compiled original-BP comparisons, not graph-shape inference, decide parity.

Python business entries:

- OnInitialized: empty slot and two scoped typed message subscriptions.
- Tick: native owning-controller QuickBar component refresh and ammo total.
- UpdateSlot: inventory quickbar fragment, native material icon parameters,
  empty/populated animation state; preserve failed texture-cast continuation.
- UpdateComponentRef: equality/validity/index branching and selection refresh.
- UpdateIsSelected / IsThisTheActiveQuickbarSlot: native active index reads and
  existing animations; respect the named-bool output shape.
- UpdateTotalAmmoLeft: native magazine + spare stat-tag counts, CommonNumeric.
- Mouse entry: native Enhanced Input action value, injection and FEventReply.

Add only owned proxy storage, explicit listener resume and typed VM transports
for LyraQuickBarSlotsChangedMessage / LyraQuickBarActiveIndexChangedMessage.
The array payload must be copied during delivery and tested after cancellation;
do not send the wildcard CustomThunk through an untyped ProcessEvent call.
Existing ten transport graphs need unchanged semantic digests and regressions.

Acceptance: actual production slots and hidden original BP counterparts;
native input weapon switching, original inventory messages, empty/populated /
same-ref / invalid-index / cast-failure comparisons, numeric/material/animation
checks; native Destruct/remount, typed owner/foreign messages, Profile roundtrip;
two clients, travel/rejoin and zero final scopes/watchers. Screenshot hashes and
actual inspection accompany data. Do not mutate native Slots/ActiveSlotIndex,
ammo, equipment or replication to manufacture these outcomes. Pending package
or acoustic/physical-input gates stay explicit.
