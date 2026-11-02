# Native gameplay migration

The first approved scope is CPP-001 through CPP-015 in `../cpp_batches.json`.
The earlier Blueprint acceptance remains a separate completed scope.

CPP-016 through CPP-018 now have a separate read-only
[entry and asset preflight](CPP16-18-preflight.json) and
[proposed batch plan](../CPP16_18_PREFLIGHT_REVIEW.md). No business replacement or
runtime acceptance is claimed there; the first-stage counts remain unchanged.
The user subsequently selected these three groups; their execution and separate
production/capability counts live in [the extended tracker](../cpp_extended_batches.json).

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

## CPP08: native interaction orchestration

[CPP08 acceptance](CPP08-acceptance.json) covers CPP-014. Two native events route
indicator removal/addition, default/specified soft widget selection, option order,
and first-option triggering to C++ or Python. Six accepted Blueprint Python
methods remain fixed in the C++ comparison; the existing Blueprint fallback
profile and Explorer regression also pass. The retained GA_Interact bytes,
class defaults, graph semantics, native scan/grant/input tasks, and inheritance
are unchanged. Only its Set asset gains the native policy profiles.

Native adapters keep the interface opaque, preserve unloaded soft class paths,
customize the payload, assemble ActorInfo, and trigger GAS. UE5.8.1 currently
ignores the supplied ActorInfo argument in TriggerAbilityFromGameplayEvent and
uses the ASC owner/avatar. Both routes preserve that behavior and verify the
customized payload target separately; this batch does not change the engine.

The isolated native fixtures record actual interface/GAS results. Their input
adapter performs Lyra's virtual spec-input dispatch once; the generic PressInputID
path also emits an event and duplicates that dispatch in Lyra. These fixture
sources are versioned outside the distributable overlay and compiled only into
the disposable validation stage. SDK/bridge and engine binaries are reused.

Native/Python boundary cases, existing Explorer activation/scan/press/rearm/end,
and two actual client owners in both profiles pass. Each owner sends three native
inputs, including one with no options; local prediction and authority each record
two customized interactions and no foreign target activation. New specs, tasks,
actors, selectors, and roots are cleaned up. LyraGame units 1/2 are rebuilt and
unit 3 is reused. The body-only witness repair rebuilt unit 2 alone. No new cook,
package, physical keyboard, rendering, or platform acceptance is claimed here.

## CPP09: Escape request policy (actual input pending)

`CPP09-escape-rules.patch` exposes the native HUD's Escape request as one
`BlueprintNativeEvent`. The retained C++ body and Python policy use the original
soft menu class and native `UI.Layer.Menu` streamed push. CommonUI's action
binding, asynchronous loading, player ownership, input router, and device/lifetime
delegates remain native. All four original HUD configuration shells keep their
defaults, graphs, visual trees, and inheritance; they share one new Mixin Set.

[CPP09 progress](CPP09-progress.json) records the implementation checkpoint;
its `accepted` value is false. Seven headless open/close cycles across both
profiles and two native level travels passed menu class/layer/owner, activation,
deactivation, desired Menu configuration, observed input-state equivalence,
HUD destruction/rebuild, and restoration checks.

The local build compiles LyraGame units 1/3 and reuses unit 2, SDK, bridge,
ShooterCore, and engine binaries. The review patch includes the original source's
missing-EOF-newline marker and reproduces the compiled source byte for byte when
applied with `core.autocrlf=false`. Its format-only repair retains the initial
build patch in the evidence archive.

`Validation/Run-UEP58NativeEscapeValidation.ps1 -Headless` runs a separate policy
lane in two disposable CommonUI worlds. It calls the selected native/Python
event and native widget deactivation directly. Only this headless fixture sets
the runtime Game/Menu stack transitions to zero duration, restoring them or
verifying that their worlds released them on exit. Authored resources are not
changed. Its contract cannot satisfy the actual-window input gate.
The offscreen action router stayed in `All` despite the Menu's desired `Menu`
configuration. Menu-mode input takeover remains pending; the actual-window gate
still requires it and cannot accept a headless report.

Run the same entry point without `-Headless` for the actual-window lane, using
fresh evidence and the existing Build01, Assets01, and Fixtures01 summaries.
That lane preserves the original transition durations and requires fourteen
real Escape key presses, visible Menu observations, two travels, native input
restoration, and HUD destruction/rebuild. It remains pending while the desktop
is locked. CPP09 is not accepted and the accepted count remains 14/15.

```powershell
$root = 'F:/UnrealEnginePython5/.build/LyraValidation/CppGameplay/20261101-CPP09'
& Validation/Run-UEP58NativeEscapeValidation.ps1 -Headless `
  -BuildEvidenceDirectory "$root/Build01" -AssetEvidenceDirectory "$root/Assets01" `
  -FixtureEvidenceDirectory "$root/Fixtures01" `
  -OutputDirectory 'F:/UnrealEnginePython5/.build/LyraValidation/CppGameplay/20261102-CPP09/HeadlessNew'
```

The full uncooked shooter scene previously failed before Python initialization
inside the unchanged original rifle Niagara asset. UI-only worlds isolate this
batch's behavior; they do not establish full shooter rendering or repair that
asset. No new cook, package, engine compilation, or platform acceptance is made.

## CPP10: native initial item-stat application

[CPP10 acceptance](CPP10-acceptance.json) covers CPP-016. The original inventory
creation callback selects the native loop or two Const item-definition events
before applying any stats. Python reads a typed Tag/Count array in native map
iteration order, avoiding unsupported mutable struct keys in Python dictionaries.
The original instanced fragments, their order, defaults, graphs, and parent
classes are preserved. Five item definitions use a constant profile selector.

Twenty definition/repeat creations, ten staged empty/zero/negative/duplicate/max
cases, two missing-definition native callbacks, and a handled-callback no-replay
guard pass. The three production weapons and two retained unused/prototype
definitions are distinguished; the latter do not claim natural gameplay coverage.
The disposable boundary fixture is versioned outside Overlay. No exception
injection acceptance is claimed.

The dedicated server and two actual clients pass both initialization profiles.
Four server pickup creations per profile each enter the selected callback once;
the clients receive equal native replicated tag stacks without running local
initialization. Twelve native quickbar cycles per profile retain owner isolation,
OnRep/equipment behavior, and inventory restoration. The previously accepted
inventory and quickbar policies stay fixed in Python during this comparison.

An independent stage preserves CPP09 for its pending window acceptance. Compiler
dependencies require the three LyraGame units for the two shared declaration
headers. Adding the staged fixture rebuilds units 1/2; its body repair rebuilds
unit 2 alone, reusing UHT and units 1/3. SDK, bridge, ShooterCore, and engine
binaries are reused. Use the main repository's NativeStats Build, Authoring,
FixtureBuild/FixtureRepair, Validation, and NetworkValidation entry points.

## CPP11/CPP12: native tag-stack costs

[The shared seven-file patch](CPP11-12-tag-stack-costs.patch) retains native cost
objects and routes numeric decisions through the owning Blueprint ability. The
context contains typed values, with no ActorInfo/spec pointer crossing into
Python. Native code still evaluates quantity curves/levels, truncates quantities,
resolves the item or PlayerState, writes failure tags, and removes stacks on the
authority. The original AdditionalCosts caller controls ordering, fail-fast
checks and OnlyApplyOnHit. A handled Python apply returns without native replay.

Three existing mixin sets retain their previously accepted Python behavior and
add `NativeCostFallback` for cost-only comparisons. The legacy `BlueprintFallback`
and five configured original item-cost subobjects remain intact. Three actual
weapon types have network coverage; HealthPickup_Unused and NetShooter_PROTO have
direct native-cost configuration coverage, without natural-play claims.

The matrix has 18 scenarios per kind in two profiles, including missing targets,
native curve/truncation, failure output, non-authority, hit filtering and multiple
costs. The server and two clients then exercise real predicted firing, native
damage, single authority deductions, stack replication and owner isolation while
the prior weapon Python implementation stays fixed.

CPP12 has no configured original player consumer. Its acceptance covers staged
cost-only abilities and temporary player costs attached to actual owned weapons.
An additional lane observes lethal GAS death, native respawn, forced Avatar
EndPlay, a second Pawn replacement, preserved PlayerState/stacks, and the native
ASC Avatar binding. It repeats the cost comparison on the new Pawn. The known
forced-Avatar equipment gap uses native quickbar empty/back selection, retaining
slot membership. Inventory restoration uses the actual post-lifecycle baseline;
no original respawn/inventory repair is claimed.

Native compiler dependencies select all three LyraGame units once. The fixture
body repair completes units 2/3; the standalone USTRUCT registration include then
requires unit 1 alone, reusing UHT and units 2/3. Both batches share that binary.
Later Python-only repairs reuse it. Diagnostic history has a 128-entry limit,
checked by 320 native callbacks; previous matrices are reused after verifying
that their only policy-file difference is this exact diagnostic-bound line.

Use the main repository's NativeCost Build, Authoring, Validation,
ProductionValidation, DiagnosticsValidation and NetworkValidation entry points.
`-Weapons pistol -Respawn` selects the extra lifecycle lane. FixtureRepair and
RegistrationRepair preserve failed build evidence and reuse successful outputs.
The native fixtures and generated disposable assets stay outside Overlay.
CPP09's exact actual-window stage remains preserved. No exception-injection,
new platform, full engine build, cook/package or physical input claim is added.

[CPP11 acceptance](CPP11-acceptance.json) records production item-cost replacement.
[CPP12 capability acceptance](CPP12-acceptance.json) records zero original player
consumers and successful independent/native-network lifecycle fixtures.

## Remaining approved groups and CPP13 checkpoint

The user explicitly requested continued work until all confirmed replacements are
complete. CPP-019 through CPP-030 are selected in `../cpp_remaining_batches.json`.
CPP09 actual-window input is deferred by the user; other groups continue.

[CPP13 progress](CPP13-progress.json) records 28 actual network input Jump trials
and 12 native null/valid ActorInfo/Avatar admission probes. The previous Blueprint
Python policy stays fixed while new native Jump rules switch. The Character
observer augments and restores existing production profiles. Explicit native
teardown guards avoid reentering the stopped Python router during profile cleanup.
The private body repair reuses UHT and units 2/3, compiling unit 1 alone.

This is an implemented checkpoint, not final CPP-019 acceptance: the next death
batch must verify cancellation and operation after respawn. The six-file shared
patch also provides disabled-by-default death/reset seams for the next batches.
The interface prototype confirms the current mixin API rejects native UClasses;
remaining native-only owners require a Blueprint policy carrier. SDK/bridge,
engine, ShooterCore and the preserved CPP09 stage remain unchanged.

## CPP13-15 accepted lifecycle replacements

[CPP13 acceptance](CPP13-acceptance.json) closes the four real death-cancellation
and new-Avatar Jump crosschecks after its 28 input/physics trials.
[CPP14 acceptance](CPP14-acceptance.json) records 20 lethal network trials, four
native self-destruct trials with active ordinary/protected witnesses, and both
native/Python original Arena two-second death tasks. Previous BP Python rules
stay fixed, and native GAS contexts, waits, prediction and replication remain.
[CPP15 acceptance](CPP15-acceptance.json) records 12 original native Reset requests,
owning/foreign client isolation, typed original Reset payloads, repeat/pending
requests, inactive Reset on completion, and protected witnesses across respawn.

The supported adapter is a world-owned Blueprint policy object. Direct native
UClass mixin registration remains rejected by the SDK; the earlier interface
probe is retained as failed evidence. Four typed context boundary cases and the
actual network Reset path validate the replacement. Only LyraGame units 1/2 and
UHT were rebuilt for this adapter; unit 3, SDK, bridge and engine were reused.
CPP16-24 continue. CPP09 actual desktop input remains user-deferred.

## CPP16-18 accepted world policies

[CPP16](CPP16-acceptance.json) records 70 frontend context cases, actual offline
startup in native/Python/default profiles, and native initialization success/
failure callbacks supplied by the fixture. Online session results are untested;
join-result and cancellation choices are bounded typed-context checks. Native
flow handles, async widget pushes, weak callbacks and delegate removal remain.

[CPP17](CPP17-acceptance.json) records 28 part-selection cases, natural/developer/
cheat suppression, first-equivalent removal, actual Reset/possession, duplicate
notifications and cleanup. Four network Reset trials provide eight independent
client observations of actual cosmetic actors and meshes. Templates are restored
inside the authority acknowledgement barrier, before either client is released.
The failed temporary-PlayerState cleanup and observer-race attempts remain.

[CPP18](CPP18-acceptance.json) records eight class/null boundary cases, original
PawnData defaults, actual ability camera priority, foreign handle protection and
restoration on native GAS ability end. Camera blend/collision implementation stays
native. Default frontend and camera smokes pass after promoting the tested policy
classes. The shared build compiles LyraGame units 1/3 and reuses unit 2. SDK, bridge
and engine are unchanged. Startup selection passes 48 focused tests.
CPP19-24 remain in progress; CPP09 desktop input remains user-deferred.

## CPP19-24 accepted remaining policies

The last six approved groups are accepted and enabled by the default `Python`
profile (`rule_policies.PawnPython`). The previous world policies, Reset and
Blueprint replacements remain enabled. All 600 typed boundaries pass, including
exact int64 replay timestamps, unknown-operation native routing and bounded traces.

| Ledger | Native lifecycle evidence | Explicit limits |
| --- | --- | --- |
| [CPP19](CPP19-acceptance.json) | Actual connection/pairing callbacks, own/foreign users, coalesced native ticker and restored traits | Callback inputs supplied by fixture; no physical controller disconnect |
| [CPP20](CPP20-acceptance.json) | Temporary native memory streams at retention 0/1/2/5, delete/requery, genuine failure-stop callback and cleanup | Keep/live markers use typed contexts; no existing recordings or gameplay playback |
| [CPP21](CPP21-acceptance.json) | Actual HDR/LDR and loading-mix methods, native readonly resource and state guards | No audible-output acceptance |
| [CPP22](CPP22-acceptance.json) | Friendly damage blocked, enemy damage 10; four authority trials and eight independent client health views | Native GAS/transport retained; default pistol separately proves real prediction and replicated damage |
| [CPP23](CPP23-acceptance.json) | Two real local players, 16 native GAS clamps per profile, original bomb input/cost/repeat/refund | Fixture attribute writes are restored before the unchanged input phase; no OS input |
| [CPP24](CPP24-acceptance.json) | Actual PlayerState/Experience data and human/bot permissions; four native Reset trials, eight independent spawn-class views | Native spawning, loading, ownership and initialization retained |

Default frontend, Pawn selection, two-player attributes/input and four original
pistol prediction/damage trials pass together. Startup selection passes 51 tests.
The private attribute fixture records Slate's reply and verifies unchanged bombs/
attributes: a zero-extent headless SceneViewport can return Handled for its neutral
character setup. It then enters the original Enhanced Input action independently.
The legacy input harness itself is unchanged. Python replay policy explicitly
rejects invalid negative retention instead of attempting deletion.

The shared native build changes all three LyraGame units, one TopDownArena unit
and LyraGame UHT output. The body repair reuses UHT and successful Lyra units 1/2.
The optional memory streamer left in the engine directory is an unregistered
5.8.0 binary; it is never loaded or registered. Its current 5.8.1 source is compiled
as one private test module and registered only in the advancing stage. An initial
link failure reuses the compiled object after adding the required native imports.
Engine manifest/binaries, SDK, bridge and the old CPP09 stage remain unchanged;
972 protected inputs are verified. No full-engine build, cook/package, new
platform, physical device or audible-output claim is added.

All 30 selected candidates are implemented. Twenty-nine are accepted within
their recorded scope; CPP-018 remains capability-only with zero original consumers.
Only CPP09's actual desktop Escape/Menu gate remains user-deferred. The remaining
scope tracker is accepted independently of that earlier pending gate.
