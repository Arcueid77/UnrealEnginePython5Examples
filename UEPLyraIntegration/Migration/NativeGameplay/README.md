# Native gameplay migration

The approved scope is CPP-001 through CPP-015 in `../cpp_batches.json`.
The earlier Blueprint acceptance remains a separate completed scope.

CPP01 replaces elimination streak, elimination chain, and assist rules. Native
Gameplay Message subscriptions and their shutdown remain in C++. Four native
callbacks enter reflected `BlueprintNativeEvent` functions; persistent classes
select the `Python` implementation or the retained `NativeFallback` body.

`CPP01-message-rules.patch` is the exact source change. The transformation checks
the original source census hashes and only writes to a marked, independently
copied validation project. The official Lyra project is the read-only reference.
The original streak and chain Blueprint classes, defaults, and graphs remain;
assist uses one thin Blueprint subclass. The shared accolade ActionSet changes
only that assist component reference, preserving its server/client roles.

Run the main repository's validation entry points in order:

1. `Validation/Run-UEP58NativeMessageBuild.ps1` generates only ShooterCoreRuntime
   headers and compiles/links that module using the accepted native dependencies.
2. `Validation/Run-UEP58NativeMessageAuthoring.ps1` generates and checks the three
   declarations, retaining the original class defaults and graph semantics.
3. `Validation/Run-UEP58NativeMessageValidation.ps1` compares real native callback
   dispatch for synthetic messages. It checks float accumulation, broadcast order,
   reentrant assist clearing, exact native clock boundaries, and listener teardown.
4. `Validation/Run-UEP58NativeMessageNetworkValidation.ps1` uses a dedicated server
   and two actual clients. Native GAS damage and HealthSet deaths must produce the
   assists, five-kill streak, rapid chains, scores, and owner notifications. It does
   not fabricate Verb messages, health, damage immunity, or score statistics.

Each run requires a fresh evidence directory. Inputs are frozen while processes
run, with archived scripts and controls. Failed attempts are retained. Live JSON
must be read through `uep_lyra_network_io.read_json` so observation cannot prevent
Windows atomic replacement. No test in this batch establishes another platform,
configuration, package, or the remaining C++ candidates.

## CPP02: team selection

[CPP02 acceptance](CPP02-acceptance.json) covers choosing a player's team and the
least-populated team calculation. Two native policy events and one thin reflected
setter are in `CPP02-team-rules.patch`. The setter calls the original native
`SetGenericTeamId`, preserving its notifications. Team creation, experience
callbacks, authority rules, and the two/four-team configuration Blueprints remain.

The team validation entry points are `Run-UEP58NativeTeamBuild.ps1`,
`Run-UEP58NativeTeamAuthoring.ps1`, and `Run-UEP58NativeTeamValidation.ps1` in the
main repository's `Validation` directory. Only the two affected LyraGame unity
units are compiled; the unchanged unit is reused. `-Families Four` reruns only
the four-team family after the two-team family has passed.

Six native/Python cases cover equal population, unequal population, inactive
players, spectators, the original four-team IDs, and no configured teams. Native
team notifications and fixture restoration are checked. The four-team map has one
natural local owner; three temporary native PlayerState actors provide the
population fixture and are destroyed afterward. This does not claim a four-owner
network test. The actual dedicated-server/two-client run uses
`Run-UEP58NativeMessageNetworkValidation.ps1 -ValidateTeam` with the team asset
evidence. It verifies eleven natural bot/owner assignments, balanced populations,
and the affected CPP01 damage, score replication, and notification pipeline.

## CPP03: bot count, names, and removal choice

[CPP03 acceptance](CPP03-acceptance.json) covers the normal and control-point bot
spawners. Python handles effective count, remaining name selection, fallback
names, and the random removal index. Native code still creates controllers,
initializes players, restarts Pawns, applies self-destruct damage, and destroys
controllers. Random selection calls the native RNG. The performance test spawner
retains its custom Blueprint creation graph and native fallback, as in the
original Blueprint test-tooling exclusion.

Use the main repository's `Run-UEP58NativeBotBuild.ps1`,
`Run-UEP58NativeBotAuthoring.ps1`, and `Run-UEP58NativeBotValidation.ps1` entry
points. The compile rebuilds LyraGame units 1/2 and reuses the accepted CPP02 team
object in unit 3. Native/Python runs for both production families verify missing
controller configuration, default and URL count precedence, zero/negative counts,
name exhaustion, nine native removals/deaths, and nonempty Python state teardown.
No exact RNG sequence or separate PIE editor-override acceptance is claimed.

The actual three-peer run adds `-ValidateBots` and the bot asset evidence to
`Run-UEP58NativeMessageNetworkValidation.ps1`. It verifies nine naturally created
and named bots, plus the affected CPP01 and CPP02 damage/notification/team gates.

## CPP04: player start selection

[CPP04 acceptance](CPP04-acceptance.json) covers TDM distance selection and the
general spectator/fallback selection rules. Two policy events preserve native
start discovery, weak-cache pruning, Play From Here preference, collision queries,
and TryClaim/expiration timers. The retained TDM maximum-distance behavior and tie
order are preserved. Python calls native physics and the native RNG.

The main repository entry points are `Run-UEP58NativeSpawnBuild.ps1`,
`Run-UEP58NativeSpawnAuthoring.ps1`, and `Run-UEP58NativeSpawnValidation.ps1`.
The build compiles the two affected LyraGame units and the derived ShooterCore
unit, using the new base import library. Eleven native/Python cases exercise real
empty/partial/full collision fits, distance/ties, claimed fallback, spectators,
candidate exhaustion, and ordinary native RestartPlayer. Fixture actors and state
are restored without writing the private start cache. Const-reference array calls
use the existing native output ABI helper to extract ReturnValue explicitly.

The actual peer run adds `-ValidateSpawning` and spawning asset evidence to the
shared network entry point. Both profiles enter native start-selection callbacks
22 times; the CPP01–CPP03 damage/notification/team/bot gates remain enabled.

## CPP05: quickbar selection and pickup grants

[CPP05 acceptance](CPP05-acceptance.json) covers forward/backward cycling, first
free slot, and template/instance grant ordering. Four policy events retain the
native server slot RPC, equipment ownership, OnRep broadcasts, inventory fast
array, and replicated subobjects. The existing quickbar Blueprint keeps its
graphs/defaults. A thin inventory Blueprint replaces one ShooterCore component
reference, preserving its role flags and other component data.

Use `Run-UEP58NativeInventoryBuild.ps1`, `Run-UEP58NativeInventoryAuthoring.ps1`,
`Run-UEP58NativeInventoryValidation.ps1`, and
`Run-UEP58NativeInventoryNetworkValidation.ps1`. Shared header dependencies require
all three LyraGame unity units; engine and ShooterCore binaries are reused.
Fourteen native/Python boundary cases preserve the original unset-backward index
behavior. Actual static pickup/interface calls preserve template order and stack
counts. Both profiles pass twelve native GAS event cycles across two actual
owning clients, matching authority equipment, native OnRep notifications, fast
array counts, owner isolation, rollback, and real client exit barriers.

The official `FLyraInventoryList::AddEntry(ULyraInventoryItemInstance*)` remains
`unimplemented()`. Nonempty existing-instance grants retain this original native
limitation; their forwarding order has a host check, not runtime acceptance.
The null-inventory guard is exercised natively. The null-interface guard is
unchanged and source-audited because the current UEP interface converter cannot
marshal `None` as a script interface. No new package or platform is claimed.

## CPP06: native spawner orchestration

[CPP06 acceptance](CPP06-acceptance.json) covers pickup conditions, availability
and effect order, cooldown reset/completion, and the scheduled overlap retry.
Native code retains both timer handles, timer scheduling/clearing, replicated
availability and OnRep, overlap detection, mesh updates, and EndPlay cleanup.
The original weapon/ability Blueprint assets remain byte-for-byte unchanged;
their existing Set gains the native policy handlers. Explicit aliases keep all
eight previously accepted Blueprint Python entrypoints registered.

Use the main repository's `Run-UEP58NativeSpawnerBuild.ps1`,
`Run-UEP58NativeSpawnerAuthoring.ps1`, `Run-UEP58NativeSpawnerValidation.ps1`, and
`Run-UEP58NativeSpawnerNetworkValidation.ps1`. Only LyraGame units 1/3 are compiled;
unit 2, ShooterCore, SDK, and engine binaries are reused. Five guard cases, real
timer completion, cooldown reentry, a stationary Pawn's scheduled overlap retry,
and pending-timer destruction pass in both C++ and Python implementations.

Both profiles retain the accepted Blueprint Python layer so this comparison
isolates the three C++ rules. The C++ Set offers `Python` and `NativeFallback`.
The earlier full-Blueprint fallback combination is not accepted in the mixed
C++ stage; its failed runs and recompiled asset snapshot are retained in the
ledger. The earlier Full-stage Blueprint acceptance remains separate.

A dedicated server and two actual owners pass 36 physical pickup scenarios on
the original level actors. These cover default ten-second cooldown, full slots,
duplicate refill/full ammo, reload guards, new duplicate instances, healing,
failure messages, inventory/equipment replication, native timer dispatch,
owner isolation, and HUD/observer cleanup. Clients use NullRHI; visible rendering
and a new package are not claimed by this batch.

## CPP07: accolade notification and queue policy

[CPP07 acceptance](CPP07-acceptance.json) covers CPP-012/013: channel/player
filtering, registry sequence allocation, completed-load ordering, location and
cancellation tags, display/pop order, and teardown queue reset. Seven typed
native events select the original C++ or Python policy. Both retain the three
accepted Blueprint Python presentation methods. Registry acquisition, native
asset streaming, listener ownership, and timer scheduling stay native.

The isolated source patch also clears the display timer at destruction and
rejects registry/asset callbacks from an earlier widget construction generation.
Eleven paired cases pass, including actual pending asset and registry requests
cancelled before a widget rebuild. Original FText, icon, Blueprint graphs,
defaults, and inheritance are preserved. Only the existing Set asset changes.

The native damage network lane passes both profiles with a dedicated server and
two actual owners: six GAS damage specs, five deaths, one assist, four awards for
A and none for B0. Both implementation groups have equal queue and presentation
counts. Each NullRHI client creates one original host widget owned by its actual
player; this verifies real production notifications and does not claim natural
HUD construction or visible rendering. All widget/class roots and listeners are
released. Only the ShooterCore unity unit is rebuilt; all LyraGame, SDK, and
engine objects are reused. Use the main repository's NativeAccolade Build,
Authoring, Validation, and NetworkValidation entry points. Failed fixture and
network attempts remain recorded in the acceptance ledger.
