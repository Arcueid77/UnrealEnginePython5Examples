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

## Native stack capture baseline (batch235)

`20261023-native-construction-stack/Native01` adds the explicit
`-UEPReplicaNativeConstructionStacks` option to the existing lazy diagnostic.
It captures at most96 native current-thread frames per construction/EndPlay/
destruction event. Symbol resolution happens after Unreal exits,in separate
per-PID offline contexts,using existing matching local PDBs. Module fingerprints,
PE SizeOfImage,address arithmetic and PDB match/GUID/age are checked. No debugger,
target DLL execution,symbol download or native gameplay mutation is involved.

All three processes exit0 and the original20-authority/40-viewer melee gate
passes. The65 stacks contain39 construction calls and26 EndPlay calls. Authority
construction reaches `SpawnDefaultPawnFor`/`RestartPlayer`;client construction
reaches `UWorld::SpawnActor` through ActorChannel processing. EndPlay reaches
native destruction. No Blueprint reinstancing,construction rerun or duplication
was observed in this healthy capture. This does not rule out those mechanisms
in a failing run. No canonical empty-binding/takeover row was reproduced,so the
original issue remains **open,not fixed**. The capture is available for a future
affected reproduction;no repeated full build or broad regression is required.
See [ledger235](Acceptance/235-native-pawn-construction-and-retirement-stack-provenance.json).

## Historical SDK counterfactual and separate bootstrap repair (batch236)

An archived DLL exactly matches the failing historical capture's ED133E... hash;
its local PDB matches. The old DLL passes the current20-authority/40-viewer
matrix in a short isolated stage path and captures native lifecycle stacks with
zero canonical empty-binding rows. This successful counterfactual does not
exclude a timing/load-order cause or prove any Pawn/ASC repair.

The first long isolated stage crashes in interpreter path setup before any
Pawn observation. Its exact source retains TCHAR_TO_UTF8 temporary pointers and
reaches null Py_DECREF. The current217 DLL independently loses a configured long
Unicode ScriptsPath. Fix the conversion lifetime and Python error handling in
the SDK startup function,keeping search order and327 exports unchanged. One
plugin compile plus two links suffices;Engine stays unchanged. The exact failed
Unicode fixture then passes,as do normal/long-ASCII/shared-interpreter modes and
real native reflection. The fixed SDK's melee group also passes with all three
exits0. This fixes startup paths,not the original **open,not fixed** binding issue.
Earlier candidate census evidence remains historical pending SDK provenance
refresh;neither this bounded check nor a healthy retry closes full migration.
See [ledger236](Acceptance/236-python-bootstrap-path-conversion-lifetime-and-sdk-counterfactual.json).

## Current delayed-client reproduction and retired-Pawn identity (batch240)

`20261025-reset-boundary/Native01DelayedB` reproduces the original four canonical
empty-binding rows with the current fixed-bootstrap SDK. Only B0's process
launch is delayed8s;gameplay timers,Health and ASC bindings are not written.
The melee group fails while arming case4 and all processes are terminated.
The256-record diagnostic limit is unchanged;those256 snapshots differ only in
moving clocks and replay as one stable binding after the diagnostic correction.
No successful gameplay matrix or race repair is claimed.

The47 resolved native stacks include five `ULyraGameplayAbility_Reset` calls.
For B0,the late local objects C5/C6/C7/C8 have Legacy actor GUIDs100/50/78/24,
matching the server's reset and retired Pawns. The already-live canonical
client Pawns have GUIDs200/198/196/202,also confirmed as healthy current Pawns
on the authority with the same PlayerState GUIDs104/54/82/4. Actor names are
never used across peers for identity. Each late retired Pawn initializes the
persistent ASC,displacing the healthy current Pawn,then receives native
ActorChannel cleanup in the same clock tick. Its EndPlay clears the ASC avatar;
the canonical current Pawn remains unbound with a healthy PlayerState HealthSet.
Creation/retirement stacks reach ActorChannel/UWorld spawn and destruction.
This is concrete provenance for the current reproduced failure. The historical
C5/C6/C7/C8 labels alone did not establish which server generation they were.

The late retired Pawn already has an ASC at BeginPlay while its PlayerState
still names the healthy current Pawn. Native Hero initialization does not wait
for canonical simulated-Pawn selection. A proposed8-line `CanChangeInitState`
guard adds that wait;the existing native OnRep callback rechecks initialization. The
candidate is not applied or compiled. Game-project C++ is reserved for a later
phase by the current migration scope,so isolated validation of this repair is
pending the user's scope decision. No manual ASC/Health repair is introduced.
See [ledger240](Acceptance/240-delayed-client-retired-pawn-guid-takeover-reproduction.json).
