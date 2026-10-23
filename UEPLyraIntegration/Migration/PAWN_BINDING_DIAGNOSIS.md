# Pawn binding investigation and Spawn Cue cleanup

The original intermittent canonical-Pawn empty-ASC/Health0 issue remains
**open, not fixed**. Batch233 fixes a separate Spawn Cue lifetime error found
while running the current melee matrix. See
[the evidence ledger](Acceptance/233-spawning-cached-target-cleanup-and-current-melee-diagnosis.json).

## Historical binding evidence

In `20261018-melee-replica-readiness/FullPythonTimeline02`, four B0 simulated
proxies were previously healthy, remained their PlayerState's canonical Pawn
and reported GameplayReady, then lost their extension/Health/actor ASC binding.
Their PlayerState HealthSet still contained100. Native verbose logs show local
replacement Pawns C5/C6/C7/C8 initializing the same ASCs with those old C2/C3/C1/
C0 Pawns as existing avatars. This is a join within one peer's own captured
log/history, not proof of cross-peer wire identity.

The unchanged official native source explains this boundary:
`ULyraPawnExtensionComponent::InitializeAbilitySystem` uninitializes an existing
avatar's extension;the uninitialized delegate calls
`ALyraCharacter::OnAbilitySystemUninitialized`,which clears the Health component
binding. `ULyraHealthComponent::GetHealth` returns0 for a null HealthSet even
though the PlayerState attribute still contains100. This narrows the failure
from a missing Health replication value to a Pawn/ASC ownership transition.
It does not prove why replacement Pawns were created/retired or identify the
production repair. Further diagnosis must capture that creation/retirement
provenance,not write Health or initialize an ASC manually.

## Separate Spawn Cue error fixed

Current `Native04ExitIdentity` completed all20 authority/40 viewer melee rows
and all three processes exited0,but the strict log gate rejected a real
`spawning_cue_mixin.OnRemoval` TargetActor conversion error. A cached target
could already be invalid,so material-parameter dispatch raised before effect
deactivation,cache clearing and subscription cancellation.

The fix passes null to native mesh helpers for an invalid cached target.
Those native helpers explicitly do no work for null. Live-target ordering and
the retained TargetActor/Timeline fields remain unchanged. Removal continues
to deactivate effects,clear both caches,cancel the team watcher and unbind
parts. The same cached-target boundary is covered for color updates,Timeline
updates and mesh queries. Forced-invalid-target host regressions verify this
cleanup;they are not claimed as an additional native destroyed-target pair.

## Current bounded verification

`Native05DestroyedTarget` uses current SDK217,one dedicated Editor server and
two real clients. All20 original/Python authority cases,40 viewer rows and four
native hostile100-damage hits pass,including the original native prediction
Cue filter. All three processes and the independent semantic gate exit0 with
strict clean logs. Lazy construction/BeginPlay/EndPlay observation does not
preload the Character or write its CDO,and restores the original class. Cue
observation forwards and restores both existing production profile handlers.
The accepted current capture has no canonical healthy-attribute/empty-binding
rows. This single successful run is not a stability or original-race repair
claim.

Preserve all four earlier failed groups:an obsolete Cue-observer precondition,
an outer transient sharing violation,a missing exit-token run_id,and the real
Spawn Cue error. Exact reader tests exercise replacement gaps,exclusive file
access,released JSON,bad JSON,unrelated I/O errors and owned exit identity.
No C++,Engine/Blueprint edits,compile,cook/package or full-version acceptance.
