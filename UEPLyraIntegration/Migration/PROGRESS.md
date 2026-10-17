# Runtime BP migration work checkpoint

Current branch in core and Examples: `dev/lyra-blueprint-python`. Version work
includes **0.10.0 closeout and 0.11.0 hero-ability pilots**, neither a
completed/published release. Preserve
the dirty changes. Do not modify official Lyra, read/copy `.nepy`, or
commit/push/tag incomplete work. Engine implementation changes remain out of
scope except for the explicitly approved upstream source update below.

User workflow update (2026-10-16): implement, verify and commit each bounded
batch separately, backfilling prior completed batches too. Completed accepted
batches may now receive local commits; unfinished batches remain unstaged.
No push, tag or release publication is implied. Shared binary assets that
contain multiple related Profiles must stay together with their implementations.

**Latest accepted bounded batch 49 (2026-10-17):** batch 48 is locally committed as
Examples 750715c / core 7f221dd. Migrate only five original generated QuickSlot
EnhancedInput receivers, aliasing twelve accepted Character methods. Preserve
four opaque dynamic-delegate parameters and original slot/tag constants,
including cycle nodes' default index zero and its empty-zero-slot noop.
Planned native acceptance is actual InjectInputVectorForAction -> retained
receiver -> virtual helper -> GAS payload -> native equipment/server RPC,
not direct BP/Python receiver calls or physical keyboard certification.
Original native input dynamic binding table, class/CDO/nineteen signatures and
every graph must survive authoring. Eight BP/Python pairs cover five actions,
repeated selection and empty slots; two real input owners/foreign isolation,
closed observer tasks/scopes and exact original item/slot identities are required.
Forty-four focused / 1,495 host models PASS. Assets01 FAILS because UClass property
access targets instance fields, not the class object's DynamicBindingObjects;
typed native UObject iteration restricted to the target outer fixes the probe.
Assets02 FAILS on a real compile-time behavior: EnhancedInput generated receiver
suffixes are renumbered when the Interface is compiled. Native binding semantics
and per-action logical signatures are now compared independently of those
compiler symbols. Callable descriptors resolve `.override` from the current
native binding table at every registration, without module-reload assumptions.
Assets03 PASSes the earlier 17/17 prototype but is not final native acceptance:
Differential01 FAILS because FInputActionValue is flattened to Python bool/vector
and the generic inverse conversion is unsupported. BlueprintFallback now
intentionally omits the five input overrides; existing UEP native Original
dispatch preserves/copies the original parameter frame without Python conversion.
Final Assets04 PASSes seventeen routed methods, Python17/BlueprintFallback12,
nineteen unchanged logical signatures, same five action/Triggered bindings,
type/full CDO/every original graph. Prototype assets are recoverably moved into
the evidence directory, not overwritten or included as final proof. Differential02
PASSes sixteen native EnhancedInput trials/eight original-Python pairs, twelve
independently observed GAS events, exact native equipment, raw cycle magnitude
zero, empty-zero-slot cycle noop, no repeated/release receiver, sixteen closed
scopes/tasks and exact original item/slot/Profile/CDO restore. Native method sets
are seventeen Python vs twelve fallback methods, with all seventeen class routes;
BP input parameters stay wholly native through automatic Original dispatch.
Network01 PASSes two real input-owner clients/sixteen trials each, thirty-two
authority RPC/equipment comparisons and twenty-four actual owner GAS events.
Each client has actual role2/Client, sixteen closed observer scopes and unchanged
foreign Actor input/helper/Profile; the other authority owner's inventory stays
unchanged. Server input receivers/helpers never execute, inventory identities
restore and cleanup is frozen before release; server-last three zero exits PASS.
Both final runs have 1,710 frozen inputs and PASS independent semantic gates and
strict closed logs. Ledger 49 contains exactly Assets04/Differential02/Network01,
with thirteen scoped sources/assets all matched to actual native frozen inputs.
All 1,495 isolated Git-index models and 602-file all-index syntax/local-import
closure PASS; five driver-safety and 56 PowerShell parse checks PASS. This bounded
local batch does not close the whole Character, parent/sibling families or version.
Manual Python-to-BP FInputActionValue roundtrip remains unsupported; no C++
change/build is used to conceal or claim a general fix for that limitation.
No Engine/general native input changes, original Lyra/animation changes, C++
build/cook/package, push/tag/release or whole-Character/version completion claim.

**Earlier accepted bounded batch 48 (2026-10-17):** batch 47 is locally committed as
Examples 74deb06 / core 9adf035. Next is only the original HealthComponent
OnHealthChanged generated receiver, retaining the eleven accepted Character
aliases. Python preserves authority, PlayerState cast, self-Pawn and native AI
Controller guards, raw Old-New damage, original zero HitLocation and default Tag.
Real GAS -> native health delegate -> actual AI damage-sense multicast/memory
and dedicated-server/two-client Health replication are the planned native gates.
Fifty-two focused / 1,451 total host models and five driver-safety checks PASS.
Assets01 PASSes native registration of twelve functions on both Profiles,
fourteen preserved signatures, original type/full CDO/every business graph.
Differential01 fails on a fixture-only C++-only SetPlayerName call; the reflected
GameMode.ChangeName replaces it with an executable constructor regression.
Differential02 fails on an unassigned fixture bot's TDM spawn ensure and invalid
negative-Damage restoration; official Healing GE and explicit native spawning
are introduced, with real Controller destruction instead of K2's deliberate noop.
Differential03 fails because the unassigned source cannot cause cross-team
damage. These remain failures, not accepted partial gameplay. Final fixture uses
an unregistered, test-owned concrete BotCreation component's native SpawnOneBot:
normal GenericPlayerInitialization assigns its team, and actual opposing-team
sources obey native damage rules. Original bot producer/list remain untouched.
Differential04 PASSes ten actual GAS primary trials, twenty-two independent
primary/prime/restore health delegates and four actual AI Damage stimuli/memory
including original negative healing strength. Original player Health/Profile/
inventory/CDO restore, one scope/three bindings close, owned Pawn/Controller/
PlayerState/producer destruction and original bot-list preservation PASS.
Network01 PASSes fourteen real authority GAS primary trials, twenty-eight client
primary observations and thirty primary/prime/restore native health delegates
per world. Actual native NetModes are DedicatedServer/Client/Client; client local
role2 and foreign role1, authority-only Damage sensing (4/0/0) and native null
replica instigators PASS. One scope/four server bindings and one scope/three
bindings per client close; health/inventory/Profile/CDO restore, original bot
list preservation and owned Pawn/Controller/PlayerState/producer cleanup PASS.
Cleanup freezes before release, server exits last, all three actual exit codes
are zero. Final standalone/network runs each freeze 1,684 inputs and PASS strict
closed logs and independent semantic gates. Ledger 48 lists exactly Assets01/
Differential04/Network01 and thirteen scoped sources/assets, all matched to actual
native frozen inputs. All 1,451 isolated Git-index models and 593-file all-index
syntax/local-import closure PASS; five driver-safety and 56 PowerShell parse
checks PASS. This bounded local batch is not whole-Character/version acceptance.
Valid non-PlayerState instigators remain host-only; naturally
emitted null-instigator startup is recorded separately, without callback replay.
No Engine/general plugin C++ migration, original Lyra/animation changes, C++
build/cook/package, push/tag/release. A missing instigating Pawn preserves BP's
zero-vector/null-source behavior without its null-receiver warning; this
intentional safety difference has host coverage, not live native certification.

**Earlier verified checkpoint (2026-10-17):** Character parts-changed component
receiver adds six real part cycles/eighteen operations/twelve independent native
delegates and actual two-client FastArray acceptance; ledger 47 below. Eleven
Character methods are routed through the retained-type Mixin. Two same-type
Pawns use opposing and swapped Profiles; eighteen native authority operations,
thirty-six client Actor observations/twenty-four native delegates pass. Dedicated
server has zero rendered-part callbacks, clients have actual local role2/foreign
role1. Original part/Actor identities/visual/camera/Profile/CDO/inventory,
observer scope/bindings and roots 44/44 standalone + 0/0,36/36,36/36 network restore.
Strict independent gates/closed logs/server-last zero exits pass, 1,665 inputs
per final run. All 1,399 host models PASS in the isolated Git-index archive;
all-index syntax/local-import closure PASSes 584 Python files. Driver safety/56
PowerShell parses pass. Remaining Character
business, parent/sibling families and whole-version acceptance remain open.
Pixels, rendered outlines, hardware output, replicated team changes and
material replication are not certified by these software tests.
Nullable native probes, hardware/travel/loss/packages and whole-version gates
remain open. No push/tag/release or C++ build/cook/package.

**Earlier checkpoint (2026-10-17):** AutoRespawn activation/reset/UI/End-removal
business has bounded native acceptance. Final ResetDifferential02 passes eight
real native requests; ResetNetwork02 passes sixteen authority/owner trials,
sixteen passive foreign observations, strict logs, independent gates, 1,525
frozen inputs and server-last three zero exits. Lifecycle03 separately passes
six real End/observe/Clear/Give trials. Both original startup variants and the
existing natural-death/Avatar/two-client matrix pass. All 1,096 host models
pass, including the isolated Git-index archive. Ledger 38 records nine passed
native runs and 23 scoped source/assets, all matched to at least one actual
native input. Full-index syntax/local-import closure passes 498 Python files.
The bounded activation batch is locally committed as Examples 73ede53 / core
41f9369. Candidate-status reconciliation now fixes three stale rows only:
device-color regressions were already complete, and the held/pressed ability
roots already had native acceptance. Existing ledgers 29/32/34 remain the
authority; no new runtime pass is claimed. Widget business/hardware/full-version
gates and static candidate totals remain unchanged. Five new consistency
checks PASS with all 1,101 models in the isolated Git-index archive. This is a
separate documentation/test-only local batch, not new native acceptance;
no push/tag/release. Original runtime business is Python-owned, but active
Clear without preceding End, travel/rejoin, loss, physical input, packages and
whole-version acceptance remain open. Earlier failures below are preserved
history, not current pass claims.

**Accepted Character inventory-helper batch:** status reconciliation is locally
committed as Examples c8ef0ac / core f11819f; no native run was added for it.
Next implement only B_Hero_ShooterMannequin.ClearInventory, called by the
unchanged original BP K2_OnDeathFinished/K2_OnReset entries from native C++.
Python retains HasAuthority, the QuickBar-valid guard, all slots before a copied
GetAllItems removal list and native RemoveItemFromSlot/RemoveItemInstance calls.
No FastArray, ability-spec, slot, inventory or animation properties are written.
Controller/missing-inventory safety is an intentional no-warning improvement,
not original BP null-receiver warning parity. Per-Actor mutable POD evidence has
no global Actor registry or UObject retention; the fixture can hold that dict
after old Actor GC without dereferencing the dead Actor. Source and twelve
models are prepared; assets/native lifetime/two-owner acceptance are not done.

Character Assets01 PASSes retained type/full CDO/six public signatures/every
complete original graph, adding only the two Interface declarations. Twelve
policy models and 1,113 full host models PASS. Differential01 records all four
real BP/Python death pairs with one selected helper call, original native slot/
item sequence, an independently observed empty-inventory window and restored
definition model with new item identities. It nevertheless FAILS final gate:
bare Avatar destruction bypasses ClearInventory, and AddInitialInventory on the
new Pawn adds exactly one new un-slotted pistol while retaining original slot/
item identities, in both BP and Python. Earlier Avatar proofs covered QuickBar
slot identities/specs, not the complete InventoryManager item set. Do not claim
those older runs proved the absence of un-slotted duplicates. Preserve the raw
delta; the new fixture removes only the newly observed un-slotted native pistol
through RemoveItemInstance, then requires exact original items/slots. This is
fixture recovery, not a production fix. Differential01 remains failed.

Character Differential02 PASSes four actual original/Python death pairs plus
both bare Avatar trials, 10/10 observation scopes, exact raw orphan delta and
native removal of only that newly added unslotted item. Original slot/item
identities are retained; normal deaths really remove/recreate native items.
Strict logs, independent gate, 1,540 frozen inputs and zero exit PASS.
Network01 completes all twelve authority/owner trials, exact foreign inventory
state and 12/12 + 6/6 + 6/6 scopes with three normal exits, but FAILS the report
gate's fixed role=2 client assumption. Actual helper callback roles are 3 on
server and 1 (SimulatedProxy) on clients, while initial owner Pawn roles are
3/2 (one B0 callback also remains role 2). Native Actor::HasAuthority is
role==Authority; both legal client roles
must remain no-op. The new gate checks real HasAuthority and valid role 1/2,
rejects client authority/removal and records the observed role rather than
relabeling it. Network01 stays failed; fresh Network02 is required. The
foreign-inventory invariant now reports failures through normal fixture finish.

Character Network02 PASSes twelve authority/owner trials and twelve passive
foreign observations. Original/Python helper enters exactly once per death;
only role-3 authority performs removal. Real client callback roles 1/2 stay
non-authority with zero removal. Native item-definition model and re-created
identities replicate, and other-owner inventory stays identical through each
trial. Native inventory scopes close 12/12 + 6/6 + 6/6. Strict logs, independent
gate, 1,544 frozen inputs and three normal exits server last PASS. All 28 focused
and 1,129 full host models PASS at this point. Standalone real Reset ingress
gets its own five report models and final native lane; not yet accepted.

Character Reset01 now PASSes four genuine native Reset BP/Python pairs through
the original Character BP event, exact selected ClearInventory ingress, native
empty-inventory observation and native re-grant with explicitly new item
identities. Inventory scopes close 8/8; strict logs, independent gate, 1,551
frozen inputs and normal zero exit PASS. All 33 focused and 1,134 full host
models PASS. Ledger 39 records four passed native runs and sixteen scoped
inputs, all matched to actual frozen native source/assets. The final isolated
Git-index archive PASSes all 1,134 models, and all-index syntax/import closure
PASSes 510 files. The initial index check correctly failed because the manifest
count was incremented before the new ledger was staged; that failed snapshot is
preserved and the final complete snapshot is independently re-tested. Five
driver-safety checks and 56 PowerShell parses PASS. The helper-only batch is
ready for its paired local commits; no native process remains.
Earlier failed runs stay failed. Other Character methods and native multi-item,
nullable-controller, Character Profile-switch, Character Reset network,
travel/rejoin, packages and whole-version gates remain open. Native warnings
remain; no Engine/official project changes or C++ build/cook/package.

**Active Character Emote-audio Interface batch:** clear-helper local commits are
Examples 70bd747 / core 47a5f1f. Extend the same retained Character with only
GetEmoteAudioComponent and SetEmoteAudioComponent; explicitly alias the accepted
ClearInventory method because Mixin collection is local-class-dictionary based.
The named object out pin is AudioComponent; Python getter uses existing explicit
named-output opt-in, setter writes only original Emote_AudioComponent state.
Original ANS_EmoteSound animation-notify BP sends these Interface messages and
is retained byte-identically; audio/animation engines are not reimplemented.
A stage-only second BP caller will contain just typed Read/Write Interface
messages. No native audio, live Interface round-trip or lifetime acceptance yet.

Character-audio Assets01 PASSes the same original class/full CDO/eight public
signatures/all original graphs. New profiles explicitly route ClearInventory
plus the two audio Interface accessors. The original animation-notify hash is
unchanged. Stage-only BP_CharacterAudioInterfaceProbe Read/Write each contain
three nodes and a true K2Node_Message copied by native FunctionReference, not
Python handler replay. The previous accepted Character root is recoverably
archived under 20261017-character-audio/AcceptedInventory01, then only the
disposable staged root was restored from official before fresh authoring. Old
accepted Mixin data remains. Eleven policy and ten report/selection models
are implemented. Native Software01 is the next bounded lane: nullable/object/
repeat/replace/cross-Profile messages, two actual same-class actors with mixed
Profiles, held-reference native GC, non-interface targets and owned component/
field/Profile/CDO/inventory restoration. No playback/hardware sound claim.

Character-audio Software01 PASSes all twelve original/Python/cross-Profile BP
Interface round trips with exact native nullable/object references, two actual
same-class Actors holding opposite Profiles/components, a real native GC while
fields own both components, native non-interface/default handling and actual
destruction of both owned components. Original fields, Profiles, CDO and
inventory restore; strict logs, independent gate and normal exit PASS. All
1,155 host models PASS. Native playback/animation-notify producer and hardware
audio are not certified by this software test. Seven new network gate models
precede a server/two-client software-only lane; local property calls must never
be described as network replication or remote audio playback.

Character-audio Network01 PASSes all 36 round trips in three actual native worlds,
two mixed-instance cases and real GC per world, with native owner/foreign replica
roles 2/1 on both clients and role 3 on the server. Fields, Profiles, CDO and
inventory restore; two owned components are actually destroyed per world.
The server waits for both actual client process exits; all three exit zero.
Independent gate and strict closed logs PASS with 1,562 frozen inputs.
These are local cosmetic references, not replicated audio payloads or playback.
Software02 re-runs the final shared fixture and PASSes all twelve cases and
cleanup with the same 1,562-input freeze. All 1,162 host models PASS.
Ledger 40 records four passed authoring/software/network runs and fourteen
scoped sources/assets, all matched to actual native frozen inputs. The isolated
Git-index archive PASSes all 1,162 models; full-index syntax/import closure
PASSes 519 Python files. Five driver-safety checks and 56 PowerShell parses PASS.
The bounded batch is ready for local commits. No hardware, actual animation-
notify producer, travel, package or whole-Character acceptance is implied.

**Active Character quickbar-input helper batch:** audio Interface helpers are
locally committed as Examples 0415f06 / core 9715524. Only ChangeQuickbarSlot is
new business; all three accepted Character helpers are explicit local aliases.
Original policy checks an occupied native slot, then forwards the supplied
GameplayTag and double-converted integer magnitude through SendGameplayEventToActor.
Default payload object fields remain null; GAS supplies MatchingTag in the
native observer callback. Inventory/equipment/GAS/native QuickBar RPC stay native.
Python deliberately handles missing Controller/QuickBar and negative/out-of-range
indices safely; original null/array-warning parity is not claimed. Twelve policy
and ten report models PASS (83 Character models total). Planned native scope is
six real BP/Python actor-reference call pairs plus two Python-only invalid-index
trials, real native event observation, empty/repeated/unrelated-tag checks and
exact owned observer task/inventory/field/Profile/CDO restoration. A stage-only
second BP owns the typed Character reference and calls its original virtual
function; no fixture calls the Python handler directly. Current asset-authoring
lane is not runtime acceptance. Prior accepted audio roots are recoverably
archived in 20261017-character-quickbar/AcceptedAudio01. No C++ build/cook/package.

Quickbar Assets01 PASSes retained class/full CDO/nine original signatures/every
complete graph, adding only Mixin Interface declarations and a stage-only typed
three-node BP caller. Differential01 PASSes all six BP/Python pairs plus two
Python-only invalid-index cases: real native local GAS payloads retain supplied
tag/exact magnitude/null object defaults; native equipment matches exact expected
definitions. All fourteen owned observer tasks/scopes close, original three
Quickslot tasks stay active, and inventory/field/Profile/CDO restore. Independent
gate, strict closed log, 1,568 frozen inputs and normal exit PASS. All 1,184 host
models PASS. The next lane adds two actual owning clients; the server observes
original QuickBar RPC equipment results and verifies foreign-owner isolation.
This does not certify the original physical keyboard producer or replicated
GameplayEvent delivery. No network pass or whole-Character acceptance yet.

Quickbar Network01 now PASSes twenty-eight real owner BP calls and twenty-eight
authority equipment observations through original native QuickBar Server RPC.
Both owners run the full six-pair/two-safety-case matrix; native local payloads
preserve exact tag/magnitude/null objects, original three GAS tasks stay active,
and each fourteen-observer scope ledger balances 14/14. The other authority
owner's inventory/equipment remains exact through every trial; server Character
helpers are not called by the fixture. Native item/slot identities and original
equipment restore. Strict closed logs, independent gate, 1,572 frozen inputs and
three zero exits server last PASS. All 1,192 host models PASS. Ledger 41 records
three passed native runs and fourteen scoped sources/assets, all matched to
actual native frozen inputs. The isolated Git-index archive PASSes all 1,192
models; all-index syntax/local-import closure PASSes 528 Python files. Five
driver-safety checks and 56 PowerShell parses PASS. This is a bounded local
input-helper batch, not whole-version acceptance or publication.
Original physical keyboard production, nullable-controller native probes,
travel/rejoin, loss, packages and whole-Character/version acceptance stay open.

**Active Character initial-inventory batch:** quickbar-input helpers are locally
committed as Examples f7a9675 / core c6e63a1. Only AddInitialInventory is new
business; four accepted helpers remain explicit aliases. Preserve Authority ->
valid Controller -> valid InventoryManager, original array order and interleaved
native AddItemDefinition(stack=1)/AddItemToSlot(index), then SetActiveSlotIndex(0)
only for nonempty configuration. Native QuickBar retains occupied/out-of-range
insertion semantics: original BP still creates the unslotted extras. Missing
QuickBar is a deliberate safe no-op, not original null-receiver warning parity.
Fifteen policy, eleven manual-report and five natural-replacement report models
PASS (122 Character models total). Planned native scopes: six original/Python
configuration pairs (empty/one/three/duplicate/overflow/occupied first), natural
first/new-Pawn grants plus original ClearInventory/death/Avatar regression, then
two-client authority-only native grants with owner replica/non-authority checks.
The fixture retains original inventory objects and undoes only newly created
items through native APIs; configuration overrides are explicit and restored.
Original inventory/slot identities, configuration/Profile/CDO are required;
recreated native equipment instances are not claimed as the old instance IDs.
Accepted quickbar roots are recoverably archived under
20261017-character-loadout/AcceptedQuickbar01. Asset authoring is active, not
runtime acceptance. No Engine/official project edits or C++ build/cook/package.

Loadout Assets01 PASSes retained type/full CDO/nine signatures/every graph and
the stage-only typed three-node caller. Differential01 PASSes all six real
original/Python pairs, including actual native stack count one, repeated item
definitions, overflow and occupied-slot unslotted extras. The original first
Pawn naturally executes Python AddInitialInventory exactly once: empty native
inventory -> one new pistol -> slot zero. Each trial/final state restores exact
original inventory/slot identities and configuration/Profile/CDO. Strict closed
log, independent gate, 1,584 frozen inputs and normal zero exit PASS.

Natural01 completes four death pairs/two bare Avatar trials and its final
semantic gate, but the driver FAILS strict logs: the new wrapper emits an Error
marker when its parent's finish only transitions from death cases to Avatar
cases. Preserve that failed lane; do not accept it based on exit zero or the
internal gate. The wrapper now requires the actual finished transition before
logging a final marker. Two explicit executable wrapper models cover the
transition and true finish. Natural02 is the fresh complete native rerun.
All 1,234 host models PASS; network authority/replica/no-op gates are prepared,
not native passes yet. Natural client entry is recorded as observed (including
zero entry), never invented; explicit real client calls must prove remote no-op.

Loadout Natural02 now PASSes four death pairs/two bare Avatar cases, natural
first/ten replacement-Pawn Python grants, unchanged original ClearInventory
ordering and 10/10 inventory observers. Strict closed log/independent gate,
1,588 frozen inputs and normal zero exit PASS. Natural01 remains failed.
Network01 completes all 24 business trials but FAILS when its server rereads a
PlayerController after publishing release and client disconnect destroys it.
The fix freezes exact restored native state once, before release; subsequent
ticks consume process-exit POD records only. An executable regression destroys
native access after release and proves no post-release read. No actor rooting
or weakened lifetime/semantic/log gate is used.

Fresh Network02 PASSes 24 actual authority grants/owner replica observations and
24 client BP remote-noop calls, exact native stack/slot/equipment models and
other-owner isolation. Original inventory/slot identities and configuration/
Profile/CDO restore. Both client inventory observers close 1/1; actual native
inventory notifications are recorded without a signal-payload-owner claim.
Restore is frozen before release, both actual client exits are awaited and the
server exits last, all zero. Strict closed logs/independent gate PASS with 1,588
frozen inputs. Both clients actually record zero natural startup helper calls;
the explicit native BP calls, not invented startup execution, prove remote
authority protection. All 1,236 host models PASS. Ledger 42 records the four
passed authoring/manual/natural/network runs; prior failed lanes remain failed.
Travel/rejoin, loss, nullable native probes, packages and whole-version gates
remain open. Missing QuickBar's safe behavior has model coverage only.
Ledger 42 contains four passed runs and sixteen scoped sources/assets, all
matched to actual frozen native inputs. Isolated-index models PASS 1,236 and
all-index syntax/local-import closure PASSes 540 files. Five driver-safety checks
and 56 PowerShell parses PASS. No native process remains; this coherent bounded
batch is ready for local commits, not push/tag/release.

**Accepted bounded Character outline-helper batch:** loadout orchestration is locally
committed as Examples a100698 / core b6e654e. Only
CreateOrUpdateOutlineIfNeeded is new business, with five accepted helper aliases.
Keep original IsLocallyControlled guard, native material-parent creation only
when missing, one camera IBlendableInterface add only on creation, scalar TeamID
then vector TeamColor updates. A valid but detached MID stays detached; repeated
calls reuse it. Material/rendering/GC implementation remains native. Existing
UEP FInterfaceProperty conversion is used, no new C++ transport/build.
Thirteen policy and ten report/cleanup checks PASS (158 Character models total).
The native fixture will use a real typed second BP caller, original/Python new/
attached/detached/repeat/negative/HDR cases, a true unpossessed same-class Actor,
held-reference GC and exact full camera-setting/field/Profile/CDO/inventory undo.
Only original ordinary material references may be temporarily rooted by the
fixture; production roots nothing. This is software state, not pixels/rendered
outline or material replication. Assets/native acceptance are not yet passed.

Outline Assets01 now PASSes retained type/full CDO/ten signatures/all original
graphs, six routed methods, a stage-only typed three-node BP caller and actual
native camera TScriptInterface signature. Software01 FAILS after one completed
original-BP trial: explicit native GC collects the fixture's unowned generated
BP caller class/CDO. Original material/camera settings and temporary Actor still
restore/clean up. The fixture now owns that test BP class across GC and releases
its added root once; two executable regressions cover preexisting-root ownership
and release. Production material/Actor/ability code is not rooted or changed.

Software02 PASSes all eight original/Python pairs, actual scalar/vector/parent/
camera interface state, valid-but-detached behavior, repeated MID identity,
signed/HDR values, real unpossessed nonlocal Actor and held-reference GC.
Software03 re-runs the final shared fixture and additionally proves the original
startup BP naturally enters Python three times, creating one MID/one blendable
and updating three scalar/vector pairs (zero original fallback entries).
Complete original camera settings/field/Profile/CDO/inventory restore; material
and test-caller roots balance and the fixture Actor is actually destroyed.
Strict logs/independent gates/normal exits PASS. All 1,270 host models PASS.
The active Network01 lane performs local software checks in three actual native
worlds, not replicated material or pixel tests. Each test-only Character has
replication disabled. Client release occurs only after local cleanup/semantic
checks, then the server waits for POD process exits without rereading Actors.
The original/staged parent material is now hash-checked and frozen by the driver.
The previous failed lane remains failed; this batch is not committed yet.

Outline Network01 now PASSes three actual native worlds, 48 case trials/54 BP
invocations and local-control differences: DedicatedServer own-player no-ops,
two owning clients create/update, unpossessed test Actors no-op. Natural startup
enters Python twice per world: server creates zero materials, each client creates
one. Actual material/interface/GC state, complete original camera settings,
field/Profile/CDO/inventory restore and all owned fixture Actor destruction PASS.
Material roots balance 0/0 + 1/1 + 1/1; caller-class roots balance 1/1 per world.
All local cleanup/semantic checks freeze before one-way release. Three normal
zero exits server last, strict closed logs and independent gate PASS with 1,602
frozen inputs. Software03 has 1,600 frozen inputs; earlier Software02 has 1,596.
All 1,270 models PASS. Ledger 43 records the three final authoring/standalone/
network runs; Software02 remains an earlier-revision pass and Software01 failed.
This is software-local material state, not pixels/rendered effects, replication
of materials, eventual reclamation of every transient MID, travel/loss/packages
or whole-Character/version acceptance. Next independent business is the existing
OnTeamOrCosmeticsChanged orchestration; current original BP still calls Python
outline from its original native/team/cosmetic entry chain.
Ledger 43 contains three final passed runs and fourteen scoped sources/assets,
all matched to actual frozen native inputs. Isolated-index models PASS 1,270;
all-index syntax/import closure PASSes 549 files, five driver-safety checks and
56 PowerShell parses PASS. No native process remains; the bounded helper batch
is ready for local commits, not publication.

**Active Character team/cosmetic orchestration batch:** outline software is
locally committed as Examples 6a1da28 / core 36dfae2. Implement only
OnTeamOrCosmeticsChanged, explicitly aliasing six accepted helpers. Source
inspection verifies two actual function parameters (TeamID, TeamDisplayAsset),
not Actor properties: original VariableGet scope is the function. Preserve the
three-way Sequence: native GetTeamColorWithFallback -> routed outline -> existing
parent BP stencil helper; optional display ApplyToActor including children;
then opaque platform-user validity and native device-property activation. Native
ActivateDevicePropertyParams defaults are retained and the native scheduler's
handle is discarded just like BP; no global handle/Actor registry. The inherited
UpdateCustomStencilFromTeamID business remains original BP for a later batch.
Assets01 PASSes the retained class/full CDO/eleven signatures/every original
graph, with seven routed helpers and a stage-only three-node typed caller.
Differential01 fails: converting native TSet<FActiveDeviceProperty> into a Python
set raises an unhashable-UScriptStruct error. No business acceptance follows
from its normal exit. The observation fixture now brackets each synchronous
call with actual native, disabled-color marker handles. It queries only the
bounded intervening handle IDs through IsPropertyActive/GetActiveDeviceProperty,
using cloned POD handles, never changing native handle allocation/active sets
or production handles. Only fixture markers may receive explicit cleanup.
Differential02 PASSes eight BP/Python pairs (sixteen trials/twenty real BP calls),
sixteen naturally evaluated/removed production device properties, thirty-two
naturally removed marker properties and 48/48 owned roots. Actual visual,
camera, Profile, CDO and inventory restore, strict closed logs, independent
gate and zero exit PASS. Callback replay/global device cleanup/hardware/pixels
and whole-Character acceptance remain false. Network01 fails because the
fixture assumes InputDeviceSubsystem exists on a dedicated server. Native
ShouldCreateSubsystem explicitly excludes dedicated servers. The corrected
fixture records that absence, requires invalid platform users/no activations
there, and keeps the real native scheduler requirements on clients. A regression
executes that absent-subsystem branch. All 1,307 host models and 206 Character
models PASS. Network02 PASSes 48 trials/60 real BP calls in three actual worlds;
natural Python team callbacks occur twice per world. Server devices/roots are
0/0, each client's sixteen production properties naturally evaluate/remove,
and 48/48 marker+production roots release per client. Each test Actor is
nonreplicated and destroyed; full original visual/camera/Profile/CDO/inventory
restore freezes before release. Strict closed logs/independent gate, 1,618
frozen inputs and three zero exits server last PASS. This is local software
per network world, not replicated team changes or replicated material state.
Differential03 PASSes the final fixture revision: sixteen trials/twenty BP
calls, three natural Python team callbacks, sixteen naturally evaluated/removed
production properties and 48/48 marker+production roots. Full original state,
strict closed logs/independent gate, 1,618 inputs and zero exit PASS. Ledger 44
records exactly Assets01, Differential03 and Network02, with all thirteen scoped
sources/assets matching at least one actual frozen native input. Differential02
is an earlier-revision pass, not final standalone proof. Final isolated-index
models PASS 1,307; all-index syntax/local-import closure PASSes 558 files, with
five driver-safety checks and 56 PowerShell parses. The bounded batch is ready
for local commits; no push/tag/release.
Official assets/Engine sources remain untouched; no C++ build/cook/package.

**Accepted bounded inherited-stencil batch:** team orchestration is locally
committed as Examples c47dec6 / core fb92eb3. The original parent graph's
StencilValue is a function local. Python preserves local AND player control ->
zero, otherwise forwards TeamId unchanged; native Lyra primitive discovery
retains recursive ChildActor traversal and the native setter owns 0..255
clamping/render state. Seven prior helpers are explicit aliases. The parent BP
stays byte-identical; only this retained Shooter Character's router shadows the
inherited function. Parent/sibling-family migration is not claimed.
Assets01 PASSes retained class/full CDO/twelve signatures/all original graphs,
with a three-node typed stencil caller and unchanged prior typed team caller.
Earlier Differential01 PASSes 40 trials/52 BP calls/24 real GC calls; inspection
shows both original and Python team calls really traverse the selected stencil
entry. The final gate therefore requires exact nested fallback/Python counts,
not a permissive zero-count baseline. Differential02 PASSes that final gate and
all original/Python direct cases: real native ChildActor with a BoxComponent,
extra fixture primitive, local/nonlocal, zero/team/max/negative/overflow/repeat,
native clamp, unchanged bRenderCustomDepth and actual GC-held references.
Natural startup has three Python stencil calls/queries and sixteen real
component writes. All original visual/camera/Profile/CDO/inventory state restores.
Network01 PASSes 120 trials/156 BP calls/72 actual GC calls in three real worlds.
Natural Python stencil enters twice/world. Server/clients keep native roles,
control and absent/present device subsystem boundaries. Test parent/child Actors
remain nonreplicated and are destroyed; both caller-class root scopes close
1/1 each/world, device roots close 0/0 + 48/48 + 48/48. Cleanup freezes before
release; all closed strict logs, independent gates and server-last three zero
exits PASS. Each final run freezes 1,636 inputs; 1,336 host models PASS. Ledger
45 contains exactly Assets01/Differential02/Network01 and thirteen scoped files,
all matched to actual frozen native inputs. Earlier Differential01 is a
historical earlier-gate pass, not final standalone proof. Isolated-index models
PASS 1,336 and all-index syntax/local-import closure PASSes 567 files; bounded
local commits are next. No pixels/stencil/team/material replication,
hardware/travel/loss/package/whole-Character/family/version claim or publication.

**Accepted bounded Character native death/Reset event batch:** inherited stencil is locally
committed as Examples ff9ffca / core 96cd025. Add only K2_OnDeathFinished and
K2_OnReset, explicitly aliasing eight accepted methods. Each Python event calls
the selected ClearInventory once; fallback invokes only its saved original
event. Native authority checks remain inside ClearInventory, and native Actor
destruction, GAS, respawn and replication remain unchanged. Evidence is one POD
dict per Actor; old-Actor GC never requires an Actor/GAS root or dead-wrapper
access. Assets01 PASSes unchanged class/full CDO/twelve signatures/all graphs,
ten routed methods and read-only validation/reuse of the prior typed stencil
caller. Eight policy, eleven natural/Reset/report/lifetime and eight network
models PASS (262 Character checks). Explicit lifecycle result flags disarm the
legacy imported fixture footers; only one native lane/ticker is launched.
Natural01 PASSes all four real lethal-damage BP/Python pairs plus two bare Avatar
trials. Each real death enters only its selected event/clear helper once; bare
Avatar enters neither event and preserves the original raw unslotted-pistol
delta, followed by native removal only of that new fixture-observed orphan.
Independent empty-inventory windows, native definition restoration with new item
identities and 10/10 closed inventory scopes PASS. Reset01 PASSes eight real
existing native Reset requests, exact Reset-not-death event/selected forward and
8/8 scopes, without manual callback or Reset-message replay. Network01 PASSes
twelve authority plus twelve owner event trials and twelve passive foreign
observations. Native owner inventory replicates; actual client callbacks are role
1 (the non-authority gate permits role 1/2), with
zero native removals, foreign inventory AND per-Actor event POD stay unchanged.
Inventory scopes close 12/12 + 6/6 + 6/6. Old Actor evidence reads only a retained
dict after destruction, never an Actor/GAS root/dead wrapper. All strict closed
logs/independent gates/normal zero exits PASS; server exits last. Frozen inputs
are 1,648 / 1,652 / 1,648 for natural/Reset/network. All 1,363 host models PASS.
Ledger 46 records exactly Assets01/Natural01/Reset01/Network01 and thirteen scoped
sources/assets, all matching actual frozen native inputs. Isolated-index models
PASS 1,363 and all-index syntax/local-import closure PASSes 575 files; bounded
local commits are next, not whole-Character/version release.
Original Engine/Lyra/animation/editor assets remain unchanged; no C++ build,
cook/package, push/tag/release.

**Accepted bounded Character parts-changed component callback batch:** native death/Reset
events are locally committed as Examples ce9cff6 / core 47f9e0a. Add only the
original generated PawnCosmeticsComponent OnCharacterPartsChanged receiver,
explicitly aliasing ten accepted methods. Python keeps original FindTeamFromObject
on Self with bLogIfNotSet=false, then calls the virtual team helper only when
the native result says assigned. The component payload is deliberately unused,
matching original BP. No new authority/local-control guard is invented.
Assets01 PASSes class/full CDO/thirteen signatures/all graphs and an actual native
register/unregister cycle: both Profiles really route eleven functions, including
the component-bound receiver, then restore original signatures. The authoring
helper's mode table replaces repeated profile-name ternaries without changing
prior mode names or runtime business. Eleven policy checks PASS.
Differential01 PASSes six native Add/Remove/repeated-remove cycles/eighteen
operations/twelve receiver entries, assigned/unassigned team branches, real
temporary part Actor creation/destruction, add/remove Profile switch and exact
original native parts/Actor identities/player visual/camera/Profile/CDO/inventory
restore. Differential02 adds an independent native multicast observer and PASSes
twelve actual component/Owner-matched deliveries with one scope/two closed
bindings, natural Python startup and all software/device/cleanup comparisons.
The observer now supports inline capture of actual one-shot native device
properties during the real replicated multicast, before later tick expiry;
errors are retained and fail the gate. Differential03 below is the final
standalone rerun after this observational revision.
Network01 runs real authority FastArray Add/Remove on both actual Pawns,
two clients observing spawned/removed part Actors and independent native
delegates. Both same-type actors use opposing Profiles and then swap them.
Native C++ deliberately does not spawn render parts/broadcast these changes on
dedicated servers; that world must have zero such callbacks, not fake success.
Files carry only IDs/readiness/Profile/test-phase metadata, never part state.
It completes all nine coordinated operations, but FAILS client final cleanup:
the new fixture omitted its `valid` import while checking destroyed temporary
Actor references. The run remains failed, not accepted because gameplay rows
exist. The import is repaired; an executable AST regression performs cleanup,
checks the live validity import and proves cached cleanup never re-reads dead
native objects after one-way release. Reporting now reads actual native bridge
NetMode and explicitly sets the scoped network-acceptance flag, rather than
retaining the base standalone default. Fresh Network02 PASSes all nine coordinated
steps/eighteen actual authority part operations/thirty-six client Actor
observations and twenty-four independently observed native delegates. Both
same-type Pawns use opposing Profiles and swap them; original/Python software
visual/device results match. Authority really has zero rendered part callbacks;
clients each observe twelve, including local role-2 and foreign role-1 actors.
Native FastArray entries and actual part Actor lifetimes, original entry/Actor
identities/visual/Profile/CDO/inventory restore and three server-last zero exits
PASS. Each world closes one observer scope/two bindings; native device roots
balance 0/0 + 36/36 + 36/36. The six one-shot properties/client are captured
inside the actual multicast before later engine-tick expiry, never replayed.
All 1,399 host/thirty-six focused models PASS. Differential03 PASSes final
standalone sources/observer schema: natural Python callback once, six native
cycles/eighteen operations/twelve independently observed delegates, correct
component/Owner payload, original state/part identities and 44/44 roots. One
scope/two bindings close, with no observer errors. Both final runs freeze 1,665
inputs and pass strict closed logs/independent gates/normal exits. Ledger 47
contains exactly Assets01/Differential03/Network02 and thirteen scoped sources,
all matching at least one actual native frozen input. Earlier Differential01/02
are earlier-observation passes, not final standalone proof. Final isolated-index
archive PASSes all 1,399 models; all-index syntax/local-import closure PASSes
584 Python files. This bounded local batch is not whole-Character/version acceptance;
no C++ build/cook/package, original Engine/Lyra/animation assets, push/tag/release.

**Accepted pressed-widget pilot and nullable-controller fix (2026-10-16, 23:45 Singapore):**
Previous held-widget batch is locally committed as Examples b8b9818 / core
8d03e61. SpawnEffect's nullable-controller repair is separately committed as
Examples fb1b13d / core 225ae72, with its own evidence ledger 33 and 933 passing
isolated-index host checks. Pressed-widget acceptance is a separate local batch;
no push, tag or release is implied by either acceptance.
`20261016-widget-pressed/Context01` passes read-only native defaults/hash audit
for ten original assets and the inventory test map. Original ContextPlay01
fails its incorrect one-instance assumption: the real Experience grants two
instances per toggle class. ContextPlay02 catches an unstable whole-spec
baseline/continuous-trigger fixture assumption. ContextPlay03 passes after
observing the two unchanged grants, waiting for stable native specs and issuing
one real EnhancedInput press. Both inventory/map UI open, survive release and
native-close correctly; specs/layer restore. No original asset is changed.

Assets01 preserves root identity/full CDO/three original signatures/business
graphs and both child files. Its new transport is soft-class path (four nodes),
exact original delegate cleanup (four), pending/widget bookkeeping (three) and
guarded empty-native-End notification (three). PythonSmoke01 then passes four
real native activations/pushes and 8/8 owned scopes, zero original-BP fallback,
zero active/errors, strict logs/independent gate/normal exit. This is bounded
smoke, not batch acceptance. Fourteen policy models passed at that checkpoint.
The original ContextPlay03 report predates the current source_mode report
field; it is historical discovery evidence, not re-certified by today's schema.

Differential01 PASSes fourteen BP/Python pairs, six Python pending-GC
regressions and four same-BP/two-instance mixed-Profile cases in the actual
Inventory Experience. Policy scopes close 74/74, fixture observers 28/28; native
shutdown and independent/strict-log gates pass. Ordinary End preserves the UI-owned panel;
explicit active Profile teardown disarms owned/original callbacks before End
and deactivation. Root defaults stay unconfigured; no fabricated target class.
Network01 completes all 48 owner trials and three zero exits, but FAILS strict
logs: client A's previously migrated SpawnEffect raises when CachedController
is null during startup. The initial commentary calling this a pass was corrected;
native reports alone are not acceptance. The failed run is retained. New pressed
policy/report rejection models pass; full live host suite was 955 before the fix.

The separate SpawnEffect repair makes a missing cached Controller a no-lock
no-op, and keeps EnableInputAgain from consuming a foreign lock that Python
never acquired. Four new policy/report checks and an actual-native existing-
instance cache-null/foreign-lock probe are added. The probe changes only the
instance cache temporarily, preserving real ActorInfo and restoring cache/input;
it does not claim original BP null-receiver warning parity. SpawnEffect
Differential01 passed, but Network01 correctly failed its probe's assumption
that no old native task could remain. The probe now compares before/after
native counts and policy creation deltas; it forbids new effects/tasks without
pretending the pre-existing task is absent. Final Differential02 and Network02
PASS ten original/Python pairs, the immediate handoff, real nullable-cache/
foreign-lock probes and 28 authority trials with two actual owners. All native
reports, strict logs, independent gates, real zero exits and 1,468 frozen inputs
pass. Server/A/B0 scopes close 23/23, 8/8 and 9/9. Failed runs remain preserved.

Pressed Network02 then PASSes all 48 LocalOnly owner trials in the actual
Inventory Experience, with 24 independent foreign-owner observations per
client. Authority abilities remain inactive and the two original grants per
toggle class are unchanged. Policy scopes close 0/0 + 48/48 + 48/48; fixture
observers close 24/24 on each client. Strict logs, independent report gate,
1,469 frozen input records and all three real zero exits pass, server last.
The standalone proof freezes 1,465 inputs. Its own inventory/map Widget BP
business is NOT migrated: only the pressed-ability orchestration is Python.
No log-error allowance, timeout widening, Engine edit or compile was introduced.
The coherent pressed batch receives ledger 34 and a separate local commit.
Its isolated Git-index archive passes 959 host checks; full-index syntax/local
import closure passes 458 Python files. All seventeen scoped runtime, asset,
authoring and driver files match at least one listed native input. Core
45 HUD/16 weapon/six ledger/five driver-safety/three index-isolation checks and
55 PowerShell parses pass. These are supporting evidence, never substitutes
for the completed native runs.
The inventory/map Widgets' own BP PopContent logic remains a later UI batch.
Travel/rejoin, packet loss, physical input, filter-token observation, UI pixel/
text parity and packages are not claimed. Ordinary native warnings remain.
No Engine build/cook/package or official/test-tool/animation/private-binding
source changes. Whole 0.10/0.11 acceptance remains OPEN; next investigate a
separate remaining hero/respawn family rather than declaring the version done.

**Accepted native AutoRespawn helper-only batch (2026-10-17):**
Pressed-widget local commits are Examples 69a46af / core e735b4b. The next
batch implements only GetOwningPlayerState, Is Avatar Dead or Dying
and EndDeathAbilities. Original BP still owns OnAbilityAdded/Removed,
activation/avatar/death/EndPlay listeners, reset messages, UI registration,
two latent delays and server restart. This is not a whole-AutoRespawn migration.
Read-only native Audit01 PASSes original type/hash/default/signature discovery:
five-second delay, per-actor instancing, LocalPredicted/OnSpawn and
ServerOnly security. Twelve helper models PASS, not runtime acceptance.
Assets01 FAILED a graph-set comparison that also counted the two newly required
Interface declaration graphs as old business. The check now permits exactly
GetPythonMixinSet/GetPythonMixinProfile as additions and still requires every
original graph's entire node/link/default digest to be identical. Assets02
PASSes that original authoring proof, but Differential01 FAILS runtime
discovery: Is Avatar Dead or Dying has a non-const bool out pin and the new
method omitted the existing explicit named-output opt-in. Its process exited
normally; it is not acceptance. No Engine/plugin rebuild is used to widen it.
Assets03's attempted two-gate transport FAILS Blueprint return-node signature
validation before saving. Inspection of the existing plugin shows no adapter
is needed: its explicit uep_named_outputs opt-in already supports this exact
non-reference out pin. Both profiles now return the IsDeadOrDying mapping;
the final policy does not introduce any business forwarding graph or node.
The four unaccepted stage/Overlay asset files are recoverably archived under
UnacceptedAssets02, and only the disposable staged root was restored from the
unchanged official file. Final Assets04 PASSes full CDO, twelve public
signatures and every complete original business graph digest, adding only the
two Interface declaration graphs. Differential02 FAILS native return-shape
handling: out-only native calls return tuples, not direct array/bool values.
The exact failed native process was stopped (exit -1); its errors are retained,
not allowed by a relaxed log gate. Native tuple unpacking is corrected in the
production EndDeathAbilities/fallback query and the read-only fixture query;
model stubs now use the observed native shapes. Twenty-two policy/report
models PASS. Differential03 PASSes four BP/Python pairs (eight actual lethal
GAS death/restarts), natural/repeat/Profile-switch/pause behavior, original
delay and logical spec model restore, strict logs/independent gate/normal exit
and 1,475 frozen inputs. Native equipment spec handles legitimately renew on
restart; class multiplicities and both persistent AutoRespawn/Death handles
are independently retained. Real original BP reaches Python EndDeathAbilities;
the fixture never calls that helper, writes health/delay or grants an ability.
The per-owner network fixture additionally has thirty focused policy/report
checks; all live host models PASS 989. A serialized final-input Differential04
then Network01 queue is now running (not duplicate native lanes). New network
gates require twelve authority and twelve owning-client rows, six independent
foreign-owner observations per client, real client/server identities, native
original lifetime, exact ack/report agreement, all owner/spec/Profile restore
and actual client zero exits before server exit. The initial gate incorrectly
assumed that only authority may execute EndDeathAbilities; Network04 below
disproves this assumption for the original BP. Differential04 and Differential05 each
PASS the complete four-pair matrix, strict logs, independent gate, 1,479 frozen
inputs and a real zero exit. Network01 FAILS fixture readiness before any trial:
it queried a client-local phase map populated only by authority OnBeginPhase.
The three exact failed processes were stopped; phase readiness now comes from
the verified server gate, while each client still requires actual native
input/health/ability readiness. Two behavior models prevent recurrence; native
wait-state sidecars expose the current readiness fields.
Network02 then FAILS at the first owner: Client.death phase method collided
with Native.attach's self.death ability field. The two later invalid-controller
errors followed that client's exit, not a newly accepted gameplay failure.
The method is now await_native_death; an AST field/method collision regression
covers the whole shared fixture. All thirty-three focused checks PASS.
Network03 completes all twelve authority/owning rows and six independent
foreign-owner observations per client; both clients pass and exit zero. It
still FAILS server cleanup: restore attempted to read a Controller after its
client process had exited and the native Controller was destroyed. Final
restoration now runs idempotently before signaling client release; only actual
exit-code barriers remain afterward. Two focused models verify ordering and
prove that already-restored server finish never re-reads a disconnected owner.
Thirty-five focused checks PASS. Network04 reruns the unchanged production
policy and complete matrix with that cleanup correction. The earlier twelve
completed rows do not turn Network03 into accepted evidence.
Network04 completes all twelve authority/owner rows, foreign observations and
three normal exits with strict closed logs, but FAILS the independent gate's
incorrect client-EndDeathAbilities-zero assumption. Both original BP and Python
execute that helper once on each owning client. Read-only engine inspection
confirms K2_HasAuthority reads CurrentActivationInfo.ActivationMode, whose
default is Authority, rather than Pawn role. The fixture now records the actual
ability guard, activation mode, Pawn role and GameMode availability before
death, at death and after restart. The gate requires those observations plus
exact final-Profile helper dispatch, original/Python lifetime parity, no local
damage/activation and unchanged foreign owners. Thirty-nine focused models
PASS, including missing/contradictory guard evidence and ack-independent
counter rejections. Fresh Differential06 and Network05 must pass this stronger
measured contract; no prior failed report is relabeled or timeout/log gate relaxed.
Differential06 now PASSes all four BP/Python pairs, eight real lethal death/
restarts, native pause/Profile-switch observations, strict logs, independent
report gate, a real zero exit and 1,479 frozen inputs. The actual standalone
guard is Authority mode 0/Pawn role 3/GameMode present at all three points.
Full live host suite PASSes 998 tests with no failures/errors/skips, supporting
core gates and all 55 PowerShell parses also PASS. Network05 is the sole
native lane at that checkpoint. Final Network05 now PASSes all twelve authority
and owner trials, six foreign observations per client, strict closed logs,
independent semantic gate, 1,479 frozen inputs and three real zero exits with
server last. Actual ability ActivationMode is 0 on all three peers; Pawn roles
are 3/2/2 and GameMode availability true/false/false at all three measured points.
Each original/Python final Profile calls the helper exactly once. Both owners
restore Profile, native spec model, delay and living state before release.
No native process remains. Isolated Git-index archive Index01 PASSes 998 host
checks; full-index syntax/eager-import closure PASSes all 467 Python files.
Ledger 35 records Audit01/Assets04/Differential06/Network05 and fourteen scoped
source hashes, all matching at least one listed native input. The ledger and
documentation are added after runtime/index verification; runtime inputs are
unchanged. This bounded batch now receives separate Examples/core local commits
before listener orchestration starts.
Network pause, loss, travel/rejoin and packaged runtime
remain unclaimed. The whole AutoRespawn business is not done.
No C++ build, cook/package, official-source/private-binding changes or push.

**Accepted native AutoRespawn listener orchestration batch (2026-10-17):**
Helper pilot is locally committed as Examples ea4d49b / core cf9ee97. The next
uncommitted batch adds Python BindDeathListener/ClearDeathListener while keeping
the native named delegate targets OnAvatarEndPlay/OnDeathStarted and all
original BP event/delay/UI/reset/restart business. Four four-node typed native
add/remove-exact graphs are authored only in the marked disposable copy.
Python retains the original clear order and LastBoundAvatarActor cache rule;
it owns no Python callback or ability lifetime. Profile changes keep delivery
on the same native ability object. The fixture observes independent real
death/EndPlay callbacks while probing repeated binding and cross-Profile
clear/rebind, then requires actual original death/avatar events to call the
selected policy after probe counters are snapshotted. Death/restart/pause,
native authority and foreign-owner isolation remain required. Fifty-seven
AutoRespawn helper/listener policy, report rejection and duplicate-entry models
PASS; this is not runtime acceptance. Asset authoring and native tests follow
serially using existing binaries. Accepted helper assets are recoverably
archived before replacing only the disposable stage and example-owned Overlay
root. Official Lyra/Engine source remains unchanged.
Assets01 PASSes exact native targets/signatures/four transports (16 nodes),
original full CDO/twelve signatures/all business graphs and normal commandlet
exit. Full live host suite PASSes 1,016 models. Differential01 completes all
four pairs and 8/8 observer scopes, but FAILS the actual helper counter gate:
new listener Profiles inherited the helper functions without locally declaring
them, while the native collector intentionally reads only __dict__. The three
helpers fell through to original BP. Both Profiles now explicitly alias the
three existing function objects, preserving override/named-output metadata
without implementation duplication. A local-registration/metadata model guards
this integration boundary. The failed normally exited run is preserved; a
fresh Differential02 must verify all five methods together before networking.
Differential02 now PASSes four BP/Python pairs/eight real deaths and restarts,
including repeated binding/cross-Profile exact clear/rebind, native pause and
mid-death Profile handoff. Actual native death/avatar events produce the
listener calls after explicit-probe counters are snapshotted; foreign Death/
EndPlay observers each receive one event, with 8/8 fixture scopes closed.
Helper routing is retained across the explicit local function aliases. Strict
logs, independent gate, normal zero exit and 1,489 frozen inputs PASS. Full
live host suite now PASSes 1,017 tests. Network01 is the only running native
lane; its two owners are in real death/restart trials. No network acceptance or
new local commit was claimed before its final gates.
Final Network01 now PASSes all twelve authority/owner trials and six independent
foreign-owner observations per client. Native repeated/cross-Profile binding,
cache clear/new-Pawn rebind, exact foreign Death/EndPlay delivery and post-probe
original event dispatch pass. Fixture scopes close 12/12 on server and 6/6 on
each client, zero active; production owns no Python delegate scope. Strict logs,
independent gate, complete owner restoration, 1,489 frozen inputs and three
actual server-last zero exits PASS. No native processes remain. Isolated-index
archive Index01 PASSes 1,017 host checks, and all 474 indexed Python files pass
syntax/eager-import closure. Ledger 36 records the three accepted native runs
and seventeen current source hashes, all matching a listed native input. The
ledger/documentation follow the runtime/index checks; runtime inputs remain
unchanged. This bounded batch now receives separate local Examples/core commits.

Next event/restart batch should reuse the two original native Delay nodes,
adding typed entry/continuation gates around the existing original BP baseline.
Python will own OnDeathStarted/OnAvatarEndPlay decisions, duration payload,
ShouldFinishRestart, EndDeathAbilities, next-frame restart and completion
payload/cosmetic decisions; native delays, GameMode restart and GameState RPC
remain. Existing BroadcastDuration/BroadcastVerb typed transport can carry the
script-built native structs. This is scoped source analysis only, not event
implementation or acceptance. Activation/reset-listener/UI/removal business
remains separately tracked until migrated and exercised.

**Accepted native AutoRespawn death/Avatar/restart event batch (2026-10-17):**
Listener pilot is locally committed as Examples 094f3c6 / core 6f75f11. The next
uncommitted batch implements OnDeathStarted, OnAvatarEndPlay and two explicit
continuation gates in Python, reusing all five accepted helper/listener function
objects locally. The original 5-second and 0.1-second native Delay nodes remain
the only latent backends; two added native entries and four dispatch nodes
select Python or unchanged original BP continuation. Python builds native
duration/verb structs through existing typed transport, retains actual ability
ActivationInfo authority semantics, calls native next-frame GameMode restart
and reliable GameState RPC, and suppresses dedicated-server cosmetic completion.
Activation/reset/UI/removal business remains BP and is not claimed migrated.
No production Python callback, timer, scope or teardown lifetime is introduced.

The fixture extends four real death/restart pairs with a separate original/
Python live-Pawn K2_DestroyActor pair to exercise actual OnAvatarEndPlay rather
than replaying it. Native message scopes read real duration/completion payloads,
require exact player/tag/duration/magnitude/empty-tags identity, and reject
duplicates. Two actual clients also independently observe the other owner's
reliable completion payload without changing their own native state. Existing
helper/listener lifetime, game pause and Profile-handoff gates remain required.
Eighty-two focused models PASS. Asset authoring, original/native differential
and network runtime acceptance have not yet passed; this batch stays uncommitted.
Assets01 now PASSes full CDO/twelve original signatures and retained business
digests around exactly four declared continuation endpoints. Both original
native Delay nodes are retained; only two entries/four dispatch/four gate-body
nodes plus prior exact listener transport are added. Host01 PASSes 1,041 models.
Differential01 completes four death pairs and both actual live-Pawn destruction
cases, with real duration/completion payloads and 10/10 closed observer scopes,
but FAILS the final spec-restoration gate. Both original BP and Python lose the
same three pistol equipment-granted abilities after bare K2_DestroyActor;
persistent AutoRespawn/Death handles remain. The fixture now records the raw
post-restart model separately, requires identical BP/Python equipment-only loss,
then uses native QuickBar empty-slot/original-slot RPCs for cleanup. It must
restore the exact logical class model, persistent handles, original slot and
unchanged inventory identities; no ability/health/inventory write or grant is
introduced and production behavior is unchanged. The failed normal-exit run is
retained; fresh Differential02 must pass all original gates before networking.
Final Differential02 now PASSes all four real death/restart pairs and both
actual live-Pawn destruction cases. Real duration/completion native payloads,
pause/mid-delay Profile switch, native two-delay continuation dispatch and
original/Python raw equipment-gap parity all pass. Both native slot round trips
restore slot 0, unchanged inventory identities, all logical ability classes and
the exact persistent handles; no direct grant/property write is used. Both
observer scope ledgers close 10/10. Strict logs, independent gate, 1,499 frozen
inputs and real normal exit PASS.

Network01 PASSes twelve authority/owner rows and six actual foreign reliable
completion payload observations per client. Native owner IDs/payload fields,
ability authority/Pawn role/GameMode distinction, zero dedicated-server local
cosmetic completion, original grants and foreign-owner isolation pass. Listener
scopes close 12/12 + 6/6 + 6/6; message scopes close 12/12 on each peer. Strict
logs, independent report gate, restoration, 1,499 frozen inputs and three real
zero exits PASS, server last. No native processes remain. Isolated Git-index
archive Index01 PASSes 1,042 host tests; all 481 indexed Python files pass
syntax/eager-import closure. All 55 PowerShell parses and five driver-safety
checks PASS. Ledger 37 records three accepted native runs and twenty-two scoped
current source/asset hashes, all matching a listed native input. Only ledger/
documentation is added afterward; runtime inputs remain unchanged. This batch
now receives separate local Examples/core commits.
Activation/Reset/UI/end/removal business and cancellation regressions remain
open; this is not whole-AutoRespawn or version acceptance.

**AutoRespawn activation/reset/UI/lifecycle batch work log (2026-10-17):**
The accepted event batch is locally committed as Examples eb90edb / core
0f59f6a. The new uncommitted activation policy completes source implementation
of the remaining four original entry methods and three gates: native Reset
subscription completion, typed Reset owner filtering and End cleanup. All
sixteen reflected methods are explicitly local, retaining the accepted helper/
listener/death/latent implementation. Activation and AvatarSet register the
single native reset listener idempotently, then dispatch existing live/dead
logic. Added registers the original respawn Widget class/reticle slot/PS/-1
priority; End and removal unregister UI and cancel the stored native listener.
The End gate's Python branch must forward only to the retained native parent.
Profile switches preserve ability-owned resources. Native End/removal disarms
both pending latent business continuations; this and listener cancellation are
intentional lifetime improvements, not exact original stale-callback parity.

Sixteen new policy models PASS (99 AutoRespawn focused models total). The asset
generator is written but not yet accepted: reuse the original native Reset
async/typed payload node, add one native entry/proxy capture, three gates/six
dispatch nodes, preserve parent End and all original business around exactly
ten declared transport endpoints. Two new default reflected fields hold the
native proxy and ended flag; original full CDO otherwise stays unchanged.
No activation assets or native runtime tests are accepted yet. Authoring can
select Python or BlueprintFallback startup variants explicitly, so actual
OnAbilityAdded/AvatarSet/activation can be compared from natural native grants
without mutating a live CDO or manufacturing lifecycle callbacks.

Required next verification: actual native Reset producer (the already granted
LyraGameplayAbility_Reset, triggered by GameplayEvent.RequestReset), own and
foreign Reset payloads, pending long/short delay cancellation on real native
End/removal, UI/async proxy restoration, re-grant/re-activation lifecycle and
the existing natural death/Avatar/pause/Profile/two-client reliable-payload
matrix. Native ASC exposes K2_GiveAbility and ClearAbility; any separate
test-owned lifecycle re-grant proof must explicitly record new spec handles,
level/input/source assumptions instead of claiming the old handle was restored.
Keep original and Python startup variants in fresh marked-stage evidence
directories, archive/restore only the exact two owned asset leaves, and leave
canonical Python assets selected afterward. Do not weaken existing natural-
grant/spec restoration gates to fit a lifecycle re-grant fixture. No Engine/
plugin C++ build, cook/package, official-source edits or private binding reads.
AssetsPython01 now PASSes original class/full CDO/twelve signatures, exact
native listener, parent End forwarding and all original business around ten
declared transport endpoints. Default Profile is explicitly Python. No live
CDO mutation is used. The full policy adds sixteen reflected methods; the only
extra CDO defaults are the empty native proxy reference and false ended flag.
Eight new natural-report/entry-isolation models bring focused AutoRespawn
checks to 107, all passing. Differential01 is currently the sole native lane,
running the existing four natural death pairs plus live-Pawn destruction pair
against the full policy. Its new bounded gate observes actual startup Added/
AvatarSet/OnSpawn activation and the live native reset proxy at every natural
phase; it explicitly cannot certify full Reset/end/removal lifecycle. The
separate lifecycle producer, startup BP variant and two-client full-policy
regression are still required. This activation batch remains uncommitted.
Differential01 now PASSes the full natural four-pair/eight-lethal-death matrix
and both live-Pawn destruction cases under the full policy, including native
QuickBar cleanup. Actual startup records Added 1/UI register 1/Activate 1/
AvatarSet 2/native reset starts 1; native Warmup also delivers four Reset
messages (one owner handled, three foreign ignored). Both reset ownership
branches have actual dispatch, but explicit producer/payload/cancellation
lifecycle evidence is still required. Strict logs, independent gate, a real
normal exit and 1,509 frozen inputs PASS. Host01 PASSes 1,066 models.

Next generate a BlueprintFallback startup variant with a distinct Set asset
name, archiving only the exact accepted-candidate Python root/Set leaves under
Variants/Python. Keep the canonical Python Set present; only root is swapped.
Run the same full natural matrix from actual original-BP startup, then archive
the two BF outputs and restore the byte-identical Python root before networking
and lifecycle work. This is asset-authoring configuration in the marked copy,
never a live CDO edit. Variant evidence/archives stay preserved independently.
AssetsBlueprint01 PASSes BlueprintFallback startup configuration with a
distinct DA_AutoRespawnActivationMixinBlueprintFallbackStartup Set, preserving
the canonical Python Set in both Stage/Overlay. Canonical Python root/Set bytes
are archived in Variants/Python (including stage/overlay copies). The sole
native lane is DifferentialBlueprint01, same full natural matrix using actual
original-BP startup; its final gate is pending. Current Stage/Overlay root is
the BF startup variant until it finishes and canonical Python root is restored.

Lifecycle fixture design to implement after source freeze ends: use reflected
native ASC ClearAbility/K2_GiveAbility in a separate test-owned proof, capture
old handle/Level/InputID/SourceObject assumptions, keep root count exactly 1/0/1
and never claim a replacement handle equals the old one. Observe real native
End/removal, native proxy cancellation and empty UI handle. Test both pending
native long and short continuations; hold only the exact old ability/proxy as
balanced fixture roots if needed to observe late callbacks, then release them.
Short-delay removal can leave the native Pawn absent, so explicit native
GameMode restart is fixture recovery only, before granting a fresh root to a
living ready Pawn; do not claim that recovery as production restart behavior.
Pending-short cleanup may expose stale cached Avatar/Health wrappers in the
accepted listener helper; inspect actual failure before repairing optional
reference handling, preserving original bookkeeping and all existing gates.
Use the already granted native Reset ability's GameplayEvent.RequestReset
producer for owned Reset tests, and actual two-owner network delivery for
foreign filtering. Keep any Clear/Give lifecycle acceptance separate from the
natural lane's no-grant/exact-persistent-handle restoration contract.
Full-policy Network01 now PASSes the twelve authority/owner natural trials,
six real foreign completion observations per client, actual inactive-client
AvatarSet startup and retained native reset proxy. Strict logs/independent gate,
1,509 frozen inputs and all three real zero exits pass, server last. Startup
BF natural DifferentialBlueprint01 also PASSes four pairs/two Avatar cases and
actual fallback Added 1/Activate 1/AvatarSet 2/subscribed 1/reset messages 4,
with 1,511 frozen inputs and normal exit. Its assets are archived under
Variants/BlueprintFallback; byte-identical canonical Python root and Set are
restored and hash-checked. These remain bounded natural regressions, not full
lifecycle or complete asset acceptance.

Lifecycle01 FAILS a fixture-rooting error: native ASC ClearAbility calls
MarkAbilityAsGarbage, which asserts !IsRooted. Exit 3 and the original crash log
are preserved. The exact process had already exited before the attempted owned
stop; no unrelated process was stopped. The revised fixture never roots GAS
instances/proxies: actual K2_EndAbility leaves the per-actor instance in its
native spec while the original long/short deadlines are observed. It then calls
ClearAbility on the inactive instance, observes removal through module counters
and ASC state, and never dereferences the garbage-marked old instance. Native
K2_GiveAbility creates an explicitly new handle with the captured null-source/
level/input assumptions, and final test-owned root is removed before exit.
Lifecycle02 completes all six native End/Clear/Give trials and exits 0, but
FAILS its independent UI assertion: IsValid(FUIExtensionHandle&) returns a
(bool, reference) tuple; the fixture incorrectly used tuple truthiness. Its
native reports/log remain failed evidence. The fixture now decodes exactly two
values with a strict bool return and records the observed return/reference
shape. GameplayAbility.cpp EndAbility explicitly removes latent actions, so
the fresh gate requires the same still-valid inactive native instance/spec at
the original deadline, zero late callbacks/restart/completion, then real removal
and new-handle Give. It does not require or replay a cancelled callback.
All 117 focused models PASS; no End/Clear/Give/cancellation native gate has
passed yet. This activation batch remains uncommitted; separate native Reset
producer/payload verification remains.

Lifecycle03 PASSes six actual native End/observation/Clear/Give cases, including
both original delayed windows in both Profiles. Its typed UI return is observed
as (bool, UScriptStruct); registration is false after End. The same inactive
native spec/instance survives through each original deadline with no late
callback, restart or completion. Clear removes exactly one instance, Give
executes real Added/OnSpawn with a new handle, and the final test-owned grant is
removed before exit. Independent gate, strict error/fatal/ensure log check,
1,513 frozen inputs and real zero exit PASS. Native Hero ClearInventory warnings
remain in forced fixture recovery; there is no warning-free claim. All 1,076
host models PASS. Full AutoRespawn acceptance remains open pending a genuine
native Reset producer and two-owner filtering/duplicate regression. A four-node
stage-only typed ReadReset probe is being authored for independent payload
observation; it contains no broadcast or gameplay logic and is not copied into
the production Overlay.

ResetProbeAssets01 passes its four-node BP generation but FAILS the driver's
wrong marker-order assertion (authoring logs its marker before Python shutdown).
The failed asset is recoverably archived. ResetProbeAssets02 PASSes with the
proper authoring marker -> Goodbye Python -> closed-log sequence. The original
production message adapter is unchanged; only a stage-owned fixture is added.
ResetDifferential01 PASSes four native BP/Python pairs: live, repeat, pending
five-second death and mid-pending Profile switch. Eight actual existing native
LyraGameplayAbility_Reset requests use SendGameplayEventToActor(RequestReset),
not a fixture Reset broadcast. Independent typed Reset/Duration/Verb readers
observe exact owners and one completion, with no second restart through the
old deadline. UI/listener/spec/Profile restore, strict logs, independent gate,
1,521 frozen inputs and normal exit PASS; native timeline warnings remain.
All 1,087 host models passed at this checkpoint. A new two-owner Reset lane is
implemented next, with passive clients and original server-initiated Reset,
explicit server foreign filtering and reliable completion observation; it is
not yet native accepted. No build/cook/package, commit/push/tag/release.

ResetNetwork01 is the sole native lane. One new static safety test FAILS before
launch because its substring check mistakes the report's trigger_entry text for
an actual client call. PowerShell did not stop on that Python exit status, so
the runtime lane did launch; no model-suite pass is claimed. Retain the failure,
freeze native inputs, then replace the static check with an actual AST-call
inspection and require the host exit code before any further launch.

ResetNetwork01 completes 16 authority trials, eight owner and eight passive
foreign observations per client, 16/16 owned message scopes on each peer and
three actual zero exits server last, but FAILS the independent UI check.
Its server reports false UI handles for every BP and Python trial; both clients
report true. No runtime/strict-log failure was observed, but process/report
completion is not acceptance. The revised fixture records the pre-Reset native
UI validity too, requiring exact role-specific before/after preservation, rather
than assuming a dedicated server has a local widget extension. Failed run is
preserved, and a fresh native run is required. The static safety model now
inspects actual AST call nodes, not report text. No production policy changes.

ResetNetwork02 PASSes all 16 authority/owner trials and sixteen passive foreign
client observations. Typed real Reset payloads have exact native PlayerState
owners; the foreign authority ability receives but filters exactly one Reset,
whereas the foreign client receives no replicated Reset router payload and
observes the native reliable completion RPC. Both clients preserve their own
state/Profile/specs. Measured UI baseline stays false/false on dedicated server
and true/true on each owning client, in both BP and Python. Original five-second
deadlines and mid-delay Profile switching produce no duplicate restart or
completion. All three observer ledgers close 16/16, zero active. Strict logs,
independent gate, 1,525 frozen inputs and three real zero exits server last PASS.
All 137 focused and 1,096 full host models PASS. ResetDifferential02 is a fresh
standalone replay of the final shared fixture/schema; it is currently the only
native lane. The batch remains uncommitted until this final gate and isolated
Git-index checks finish. Whole version, travel/rejoin, loss and packages remain
open. Native warnings are retained, never described as warning-free.

ResetDifferential02 now PASSes all eight final-schema requests with the same
1,525 frozen inputs, independent gate, strict log and normal zero exit. No
native process remains. The 45 HUD/16 weapon/six ledger/five driver-safety/
three isolated-index support checks and 56 PowerShell parses PASS. These remain
supporting evidence, not native acceptance substitutes. The isolated staged
archive PASSes all 1,096 models; all-index syntax/import closure PASSes 498
files. Ledger 38 retains the exact nine native runs, report and DLL hashes and
all 23 scoped input matches. Commit the coherent activation batch only,
preserving unrelated user URL edits. Next reconcile earlier candidate status
entries against their already committed ledgers, then take a small Character/
inventory helper batch before broader character events.

**Accepted held-widget pilot (2026-10-16, 22:28 Singapore):**
The held-input root policy is now implemented in
`uep_lyra_abilities/widget_held_mixin.py`; its two original scoreboard children
remain byte-identical. Native authoring `20261016-widget-held/Assets02` passes
the retained type/full-CDO/four-signature/original-graph checks. A four-node
typed soft-class-path adapter avoids treating an unloaded class as None. Four
state-callback guard nodes prevent original-BP teardown from reentering a
mutating router. They suppress dispatch only during explicit teardown.

Differential01 FAILED in the fixture's struct-keyed layer-map conversion;
the fixture now reads the original named GameMenu stack. Differential02
FAILED on original-BP state-task reentry during active Profile handoff; its
exact owned process was terminated after the native error stalled the lane.
Failed runs and the first unaccepted asset outputs remain in `.build`.
Differential03 then exposed fixture-only missing-object lookup/removal API
assumptions and the invalid CP-in-Elimination UI context. The two Experiences
now use their own existing native grants, scoring components and EnhancedInput;
no fixture ability/CDO writes remain. Elimination01 caught a queued True input
reactivating a canceled ability; the fixture no longer adds True in an End
frame, retaining exact single-activation gates. Elimination02 correctly found
that original BP and Python both end on pause. EnhancedPlayerInput invalidates
IA_ShowScoreboard's non-pause input, so the current pause case explicitly
requires native input release/UI removal while game time is frozen, including
continuous held injections and read-only native input-policy evidence.

Final Elimination03 and ControlPoint01 each PASS seven original-BP/Python
pairs in their real native Experience plus three Python pending-cancel/repeat/
Profile-handoff GC regressions. Each leaves 21/21 scopes, zero active/errors,
original player/specs/Profiles/CDO and GameMenu layer restored. No ability is
fixture-granted; both use existing IA_ShowScoreboard bindings. Unconfigured
root defaults remain untouched and are not exercised as a valid UI target.

Network01 PASSes 24 LocalOnly owner trials, then Network02 repeats that full
matrix against the hardened acknowledgement-identity/foreign-owner report
gate and PASSes. A/B0 each independently observe all twelve foreign held
trials; native server abilities/tasks stay inactive. Server/A/B0 scopes are
0/0, 12/12, 12/12. All three actual exits are zero, server last; strict logs,
independent gates and 1,453 frozen input records per final native run pass.
Networking is Elimination only; CP networking, travel/rejoin, packet loss,
physical input, pixel/text scoreboard parity and packaged runtime are not
claimed. Scoreboard UMG/BP content remains for its later UI/scoring batches.
Original BP's canceled Async Action property differs intentionally: Python
clears its reference and precisely disarms its completion before cancellation.

Host05 and the isolated Git-index archive pass all 929 policy/report checks;
full-index syntax/local-import closure passes all 447 Python files. Core
45 HUD/16 weapon/six ledger-format/five driver-safety checks also pass. The
bounded evidence snapshot is `Migration/Acceptance/32-held-widget.json`, with
all twelve scoped runtime/asset/authoring/driver sources matching listed native
input hashes. This coherent batch receives its own local Examples/core commits;
the unrelated owner-URL edits are excluded. Whole 0.11 remains open. No Engine
build/cook/package, push, tag or release.

**Completed accepted-work backfill (2026-10-16):**
All previously accepted runtime work is now split into local Examples commits
with 32 bounded evidence ledgers, numbered 00–31 in `Migration/Acceptance/`.
Latest runtime/audit commit: 72b8e38; historical Third Person fixture/staging
commit: 47878ee. Core native foundations are 6fd3d79, paired world/ability
drivers 34e2138, integrated acceptance gates 0971985 and historical drivers
abaaf5e. No push, tag, release or new compile/cook/package was performed.

Fresh Git-index-only archive tests pass all 893 Examples checks; full-index
syntax/import closure passes 438 Python files with zero missing eager/deferred
local modules. Core checks additionally pass 45 HUD + 16 weapon contracts,
6 historical-ledger format checks, 5 native-driver safety checks and 3 index
isolation checks. These supporting checks are not native runtime acceptance.
The isolated snapshot excludes both held-widget drafts. Source/binary/report
provenance for each batch remains in its ledger, not a whole-version claim.

Current-DLL rifle-Network01 and shotgun-Network02 each PASS 36 authority rows,
native equipment observations for two actual owners, independent gates, strict
logs, frozen inputs and all three real zero exits, with the server last.
Shotgun-Network01 remains FAILED (520-second shutdown timeout), not erased or
converted into a pass. The only retry change is process-scoped NoDDCCleanup;
D3D12, gameplay cases and assertions remain unchanged. The unsuccessful
pre-runtime ledger attempt is preserved under
`.build/CommitVerification/20261016-27-weapon-instances/unaccepted-closeout-attempt.json`.
Final weapon evidence is `27-weapon-instances-current.json`; runtime code is
committed as a9bc181. Spawn/device batches are cfd0d92/a52fa8a. Historical
Third Person variants keep their old engine/binary qualification, not a new
5.8.1 run. Package presentation proof remains historical; packaged networking
was not run. Native warnings remain recorded, not a warning-free claim.

Concurrent repository-owner URL changes are preserved and excluded from this
backfill. No private binding sources were read. Whole 0.10/0.11 acceptance is
still OPEN. At that backfill checkpoint the held-input family remained two
unaccepted Tools drafts; the newer held-widget checkpoint above supersedes
that state. Next separate family is pressed-input Widgets, before remaining
fire/melee/grenade and other hero policies. Original UI/scoring business is not
claimed migrated merely because a Python ability pushes its retained Widget.

**Accepted-batch backfill checkpoint (2026-10-16, 21:24 Singapore):**
Completed local Examples commits now separate shared HUD/test infrastructure,
network orchestration, effect pads, weapon presentation, progress/failure/dash/
respawn/quickbar/nameplate HUD, inventory/effect pads, launchers, spawners,
teleporters, menus/action-touch, unused heal-pickup, the shared Jump/ADS/Emote
family, quickslot, death, cosmetics, auto-reload, hero heal, drop weapon and
reload family. Compact evidence snapshots are in `Migration/Acceptance/`.
Each batch is tested from a Git-index-only Examples archive plus committed core,
not from the mixed live worktree. Latest isolated index checks PASS 851 with
weapon-instance work staged but NOT committed. Initial missing sparse-map and
inventory-helper dependencies were rejected and repaired before their commits.
The archive tool's historical array-process format fix is separately committed
and passes four synthetic ledger-format checks. No push/tag/publication.

Current native CombinedNetwork01 report is rechecked using isolated committed
HUD modules: all ten HUD groups PASS across nineteen phases/two clients/rejoin.
Historical per-feature runs retain their actual older DLL hashes; a later run
that merely freezes a source file is provenance, not re-execution of that case.
Emote/ADS/shared-Widget current-DLL gates and historical Jump network gate all
recheck PASS. Four historical reload-family network gates recheck PASS 36 rows
each. Historical native world/UI/ability gates remain bounded as their ledgers
declare; none is a whole-version or physical-input certification.

Weapon-instance closeout is PAUSED before commit: current network gate rejects
the old RifleNetwork02 report because its older equipment schema lacks the
later `profile` field. Do not fabricate/patch old reports or weaken the gate.
A serialized current-DLL rifle then shotgun network queue is running at
`20261016-batch-backfill/{rifle,shotgun}-Network01`, with original retained
assets and no compile/cook/package. Server and two clients are active for rifle;
no result yet. Freeze runtime Sources/Scripts/assets/Tests/drivers throughout.
Keep the uncommitted `27-weapon-instances.json` snapshot as an unsuccessful
closeout attempt until fresh evidence can receive a distinct snapshot name.
Remaining accepted feature backfill: weapon instances, spawn effect, device
color, read-only audits/producer probes and paired remaining drivers/docs.
The held-widget implementation/generator drafts in Tools remain UNACCEPTED.

Backfill native follow-up (21:36 Singapore): current-DLL rifle-Network01 PASS
all 36 authority rows and two-owner equipment observations, independent gates,
normal exits and unchanged inputs. Shotgun-Network01 completes all gameplay
cases but FAILS the unchanged 520-second total timeout: A exits zero, B0 stalls
during native shutdown and server waits for its real exit. Do not count markers
as acceptance. Retain this failure. Logs include a four-minute scan of 143,726
cache files/110,638 directories and zero deletions, but this alone does not
establish causality. All owned test processes are cleaned up after timeout.
Engine FileSystemCacheStore.cpp:3098 explicitly supports `-NoDDCCleanup`.
Only add that process-scoped switch to the validation driver (no Engine edit,
cache deletion, graphics change, extra build, scenario or gate relaxation).
Five static safety checks pass. Fresh shotgun-Network02 is now running on the
same current DLL/assets; acceptance remains pending. While it runs, source/
runtime inputs stay frozen. Static manifest regeneration still reports
246/182/63 and migration_complete=false; the older Coverage06 entrypoint review
is static/historical, not a fresh native coverage result.

**Batch backfill started; native foundation committed (2026-10-16, 20:54 Singapore):**
Core 6fd3d79 records verified runtime/reflection/editor-authoring foundations,
generic native fixtures, scoped subscriptions and API contracts. Fifteen changed
native source files exactly match listed accepted native inputs; all 406 core
source hashes still match CallMatrix01. Thirteen subscription models and 45+16
PowerShell contract checks pass before commit. Compact native evidence index is
Validation/AcceptedBatches/core-runtime-20261016.json, not a full-version claim.
Emote queue COMPLETES: Differential03 PASS nine pairs/1,439 inputs, SharedWidget01
PASS eight native cases/1,448 inputs, ADSStandalone01 PASS six pairs and
ADSNetwork01 PASS twenty authority rows, Emote Network01 PASS twenty authority
rows/five pairs per actual owner; last three all freeze 1,439 inputs. Independent
gates, strict logs and real normal exits pass. Emote scopes balance 18/18
standalone, 20/20 server, 10/10 each owner. Network movement/crouch interruption,
pause and ordinary movement input remain untested. Widget-input Audit01 PASS
six original assets/signatures/defaults, but held-widget implementation/generator
drafts in Tools are UNACCEPTED and must not be included in completed-batch
commits. Pause new feature implementation while backfilling coherent commits.

**Emote standalone accepted; final-input shared-family/network queue running (2026-10-16, 20:36 Singapore):**
Differential01 completes nine observed pairs but FAILS its independent native
callback gate: AddMovementInput produces zero velocity in BOTH original/Python
montages, so neither side exercises movement interruption. Preserve the failed
report; do not weaken the gate. Differential02 uses declared native external
LaunchCharacter, not a Velocity property write or public-handler replay.
It PASSES all nine pairs: actual motion produces OnInterrupted on both sides,
235.15/234.05 native peak velocity, original BP clears foreign callbacks (0 after
End) while Python preserves them (71 after End), with no late Python movement.
Natural/repeat/crouched-entry, actual crouch, cancellation, native End, Profile
teardown and real game/montage pause pass. 18/18 policy scopes, exact player/
profile/widget restoration, independent gate, strict logs, normal exit and
1,435 frozen inputs pass. Ordinary movement input interruption is NOT certified.
Network transport/hooks/gate models now bring host checks to 893 PASS. The
serial queue on those final inputs is Differential03, SharedWidget01 through
the hash-verified Jump->ADS->Emote revision chain, ADSStandalone01, ADSNetwork01,
then Emote Network01. Stop on the first failure; never run duplicate native
lanes. Network declares five pairs per owner (20 authority rows), native input/
GAS/montage/source/foreign-player/restore/exit checks. It does not claim network
movement/crouch interruption or pause. Current revised-input/shared-family and
network runs remain unaccepted pending real reports. No new C++ build/package.

**Emote shared-parent assets green; actual input differential running (2026-10-16, 20:29 Singapore):**
Emote/Audit01 FAILS its audit tool's overly broad "montage" field selection
(a native delegate map is not an AnimMontage). Audit02 PASSES actual native
type-filtered defaults/signatures/graphs without modifying the original asset.
Original policy is LocalPredicted/per-actor/input-triggered, native montage
5.4499998s and one inherited Emote touch widget. Assets01 PASSES four current
family outputs, full CDO/public signatures/original business graphs and existing
ADS/default Profiles, with 1,242 frozen inputs. One existing shared parent router
owns three typed Emote gates. A four-node native delegate helper removes only
this ability's original CheckForMovement binding; no Engine implementation or
animation asset change, no C++ build/cook/package. Old authoring evidence remains
unchanged; ADS can consume this accepted current family revision explicitly.
Models PASS 889, including ten policy/lifetime and four independent-gate tests.
Differential01 now tests nine actual EnhancedInput/GAS BP/Python pairs, native
movement/crouch/montage interruption, cancellation, Profile teardown, repeat,
native pause and original ClearAll-vs-Python foreign-listener isolation.
It does not directly activate/replay production handlers, callbacks or write
velocity. Current runtime and network acceptance remain pending; source/assets
and fixture inputs are frozen during this run. Whole version remains open.

**New bridge binary combined travel/rejoin regression accepted (2026-10-16, 20:18 Singapore):**
Device-color CombinedNetwork01 PASSES all nineteen ordered phases, two actual
travels, death/respawn, B0 exit and B1 rejoin/fire with one dedicated server and
two concurrent real clients. Independent protocol validation accepts native
fire/reload, HUD comparisons and public healthbar ingress. Four actual normal
exits, strict error/ensure logs, 757 frozen inputs and 410 native-source pairs
pass on DLL 41271D... . This complements the current eleven-call, three-PIE,
six-map and 28-trial SpawnEffect network regressions; no new build is involved.
Earlier unrelated batches retain their historical DLL provenance, not a claim
that all migration scenarios were rerun. Emote/Audit01 now reads unchanged
original asset/defaults/graphs and current native task/public signatures before
implementing the next bounded batch. Whole migration/version remain open.

**New bridge binary passes focused regressions; combined network running (2026-10-16, 20:13 Singapore):**
On DLL 41271D... the device-color CallMatrix01 PASSES all eleven generic lanes,
Lifecycle01 PASSES three native PIE cycles, SparseMap01 PASSES all six native
hole/removal cases, and SpawnNetwork01 PASSES the actual server/two-owner
28-trial SpawnEffect comparison. Independent report gates, strict error/ensure
logs, exact input hashes and normal process exits pass; these are new runs,
not inherited acceptance from the previous DLL. CombinedNetwork01 now runs
the existing nineteen-phase HUD/weapon lane with two travels, respawn,
disconnect/rejoin and public healthbar entries, without another build.
That combined run is not accepted yet. Its source/assets/tests remain frozen.
Next bounded migration: audit original GA_Emote current native signatures,
montage defaults, movement interruption and shared-parent routing. Original BP
clears all CharacterMovementUpdated listeners; Python must own and release
only its own subscription, with the intentional isolation difference tested.
Whole migration/version remain open; no commit, push, package or release.

**Return-before-out bridge fixed; device software green, generic regressions running (2026-10-16, 20:04 Singapore):**
Differential01 FAILS actual BP VM UEPDeviceColorRoute with "Invalid return value
type" and the probe's unreflected ActivateDeviceProperty call. Actual signature
orders ReturnValue before bCallNativeParent. UPythonFunction stepped the return
slot (which has no call argument expression), consumed the out expression and
misclassified the dictionary as a scalar return. Move only the return skip
before Stack.Step in PythonFunction.cpp; preserve all preexisting dirty edits.
PluginPlan01 exports exactly three UEP-only compile/lib/DLL actions and checked
Engine files stay unchanged. PluginBuild01 PASSES that bounded build in 25.151s,
NoEngineChanges; no full Engine/Lyra build, metadata workaround or packaging.
Current UEP DLL is 41271D075921BF076FD4C6BE0B404544150BCC34C5E7E2D2CC2F5F95325E72D5,
BuildId still 2f7b5df8-1c9a-4414-a598-6d3b022aa38d. Old DLL/PDB and original staged
source are recoverable. Exact DLL/PDB plus changed source mirrored to matching
generic UE58Host; no additional build or module metadata rewrite.
Probe now uses only reflected ActivateDevicePropertyOfClass. Repeats create new
native factory objects, NOT same-instance native reactivation; actual looping
same-instance Profile switching remains tested. Models PASS 875 with native-VM
return ordering and unsupported instance-activation regressions.
Differential02 PASSES six real original/Python software pairs and automatic
default native class activation on this NEW DLL: one-shot, repeated factory,
looping, same-instance Profile switch, native pause and public invalid user.
Original type/profile/color/player state, 15/15 temporary roots and only owned
handles restore. Actual default color [246,52,41,255]; original BP agrees.
Independent gate, strict error/ensure logs, normal exit and 1,421 frozen inputs
pass. No hardware or native invalid-user scheduler claim.
CallMatrix01 now runs all generic native/BP/Python/fallback lanes on the exact
new DLL; lifetime, sparse-map and representative real-network regression follow
serially. Earlier 3FF... runtime results are historical, not automatically new-
binary acceptance. Whole migration/version remain open; no commit or release.

**DeviceColor retained transport authored; six native software pairs running (2026-10-16, 19:52 Singapore):**
Audit01 FAILS its attempt to invoke unreflected GetDuration; corrected audit
reads serialized PropertyDuration. Audit02/03 PASS original current 5.8.1
four-input event/parent signature, full CDO and actual pins. DeviceId is
unconnected on the original native-parent call; retain that wiring rather than
silently changing device selection. Assets01 PASSES original class, full CDO,
three public signatures, original business/parent graph semantics and a typed
two-output business route. No native End adapter or C++ change. Python queries
original native team display/color/sRGB conversion; invalid users preserve data
and do not request parent evaluation. Original BP path remains for comparison.
Models PASS 870. Differential01 runs actual InputDeviceSubsystem default class
activation, one-shot/repeated same-instance/cyclic/pause/Profile lifetime plus
six original/Python pairs. Invalid user is explicitly a real public BP entry,
NOT a scheduler test (native scheduler correctly rejects invalid IDs as Error).
Only owned handles/temporary roots are released; original engine device
properties are not cleared. Color data/software transport only, NOT physical
LED output, network behavior, secondary platform users or whole-version proof.
Current native run is unaccepted pending report/gate/strict logs/exits/hashes.

**SpawnEffect current standalone/handoff and two-owner network accepted (2026-10-16, 19:36 Singapore):**
Differential03 PASSES all ten original/Python native pairs on simplified
Assets02 plus actual immediate BP->Python reactivation. Old native End clears
its own latent actions. New Python remains alive beyond the old deadline,
has exactly two EnableInputAgain entries but one owned unlock, unlocks at
2.0644 seconds and ends at 2.7542, with no effects/tasks and original model
restored. Independent gate, strict error/ensure logs, normal exit, 19/19 scopes
and 1,412 frozen inputs pass. No speculative delay gate remains.
Network01 PASSES 28 native authority trials / seven pairs per actual owner,
both real ServerInitiated recipients, native effect replication cleanup,
foreign lock and foreign player isolation, exact native input-stack restoration
(authority A/B0 each 1 -> isolated -> 1), original specs/inventory/fraction and
three server-last normal exits. Independent gate, strict error/ensure logs and
1,412 frozen inputs pass. Authority scopes 24/24, both owners 9/9; each client
has 14 own rows plus 14 unchanged foreign rows. Files carry scheduling tokens,
not GAS activation or effect state; no client directly activates the ability.
Original spawning-Cue active-timeline recycling warnings remain: server 0,
client A 13/B0 12. No warning-free, hardware, packet-loss, travel, network pause,
network fraction-boundary or network-immediate-handoff acceptance.
This bounded batch is accepted, not the whole 0.11. DeviceColor/Audit01 now
reads original current-engine signatures/CDO/event-parent pins before selecting
the next implementation. No Engine/official edits, C++ build, package or release.

**Simplified asset passes; current standalone then two-owner queue running (2026-10-16, 19:30 Singapore):**
Assets02 PASSES original full CDO/class/signatures/graph preservation without
the speculative legacy Delay gates. Native EndAbility alone owns Blueprint
latent-action removal; its actual Engine source file is now frozen as evidence.
Models PASS 860, including passive-client no-activation source check, effect
replication End barrier, actual-role/source/foreign-state/input-stack negatives.
Differential03 runs the ten-pair native matrix and immediate BP->Python
reactivation, then Network01 starts only if it passes. Network uses one real
authority and two actual clients, seven pairs per owner (28 authority rows).
Authority calls native existing-spec activation; clients never activate/replay
events and must observe actual native ServerInitiated RPC ability/effect/
montage before authority interventions. Client cleanup waits actual immunity/
effect replication, with foreign owner state continuously checked on both
clients/authority. Bounded native stack isolation/restoration is explicit on
remote authority controllers. No network pause, fraction-boundary, remote
equipment-viewer or network-immediate-handoff claim. Inputs frozen for queue;
current revised asset/runtime and network remain unaccepted pending results.

**Immediate handoff exposes incorrect test assumption; simplify native ownership (2026-10-16, 19:23 Singapore):**
Differential01 PASSES ten native pairs, exact fractional unlock/own immunity/
foreign movement-lock preservation/pause/restore, independent gate, strict
error logs and normal exit; 18/18 scopes. Differential02 repeats all ten pairs
and immediate BP-to-Python reactivation: old activation cleans, new Python
stays active beyond the old deadline, unlocks at 2.0645 and ends at 2.7526,
with zero tasks/effects and original player restored. It FAILS the gate's
incorrect requirement for two intercepted old BP callbacks (observed zero).
Current Engine GameplayAbility.cpp:827-835 unconditionally removes ability
latent actions in native EndAbility; do not duplicate this native ownership.
Remove the speculative two legacy gates and their Profile methods. Verify
hashes, recoverably move only this batch's four unchanged generated stage/
Overlay files under Assets01/RetiredGeneratedGates, restore the stage BP from
read-only official original, and regenerate Assets02. Nothing is deleted or
changed in official Lyra/Engine. Models PASS 853. Preserve failed evidence.
The corrected handoff gate checks actual two Python EnableInputAgain entries,
one owned unlock, real old-deadline survival, new full duration and cleanup;
no synthetic callbacks or requirement that native-cancelled callbacks execute.
Assets02 authoring is running; revised runtime acceptance still due.

**SpawnEffect authored; ten-pair native differential running (2026-10-16, 19:14 Singapore):**
Audit01 PASSES unchanged original current-5.8.1 GA_SpawnEffect/GE_SpawnIn:
ServerInitiated=2, InstancedPerActor=1, OnSpawn=2, original Pistol spawn montage
2.75 seconds, fractional unlock .75 and Infinite own immunity effect. Original
BP apply-Level pin is 0. Assets01 PASSES retained native class, full CDO text
(only declared Mixin fields/guard excluded), four original public signatures,
original graph semantics and two explicit legacy Delay continuation gates.
Two outputs only; no animation/effect/official assets changed.
Python uses native GAS WaitDelay/Montage tasks, original Level=0/context/effect
handle, owned one-level input unlock, exact original montage interruption rules
and idempotent End/Profile cleanup. No active animation/replication writes.
Legacy original Delay gates cannot fall through into Python after Profile
replacement. Models PASS 852. Differential01 runs ten real native pairs:
natural timer, montage interrupt, cancel, external End, Profile teardown,
repeat, zero/end unlock fractions, foreign input lock and paused world time.
Requires observed automatic default Python OnSpawn on the actual existing spec,
actual immunity/effect count/montage and fractional unlock, original inventory/
ability specs/fraction restore, no late business mutation, scopes, independent
gate, strict logs and normal exit. Not yet runtime/network/version accepted.

**Dead equipment five-pair differential accepted; SpawnEffect audit running (2026-10-16, 19:06 Singapore):**
DeathDifferential01 PASSES all five complete original/Python real lethal GAS
Death/Cue/timer/respawn pairs with native empty-slot equipment unequip while
health is truly dead/dying. Same-frame native animation state is unchanged on
both sides, Python dead-skip increments exactly once without layer/montage
calls, source/type/Profile and respawn inventory models restore. Independent
gate, strict error/ensure logs, normal exit and 1,403 frozen inputs pass.
This tests the explicit live-dead-Pawn Quickbar fixture, NOT natural destroy
unequip, all four weapon families dying, or remote-viewer equipment state.
Death Cue recycled-active-timeline warnings remain separately recorded.
Do not claim warning-free playback. SpawnEffect/Audit01 now reads unchanged
original GA_SpawnEffect and GE_SpawnIn current 5.8.1 signatures/defaults/CDOs.
Next production batch is spawn effect/input-unlock/own-effect cleanup; original
GAS, montage assets, animation and original level-zero effect pin remain.
Whole 0.11 and total migration remain open; no compile/package/commit/release.

**Prototype BP/Python owner integration passed; actual Death running (2026-10-16, 19:04 Singapore):**
NetShooterBlueprintBaseline01 and NetShooterNetwork02 PASS all 36 reload authority
rows, two-owner equipment lifecycle/source/role/local native tag and layer
selection, original CDO/observer/weapon restore, independent gates, strict
error/ensure logs, three server-last normal exits and 1,419 frozen inputs each.
The new native BP control reproduces tag-map invalid weak-owner warnings:
server BP=3, Python=4, both sets of clients=0. This establishes the warning also
occurs with original equipment BP; it does NOT prove equal frequency or
warning-free playback. Preserve warning evidence; no Engine/ABP workaround.
DeathDifferential01 now reuses actual native lethal damage and respawn with
the declared dead empty-slot unequip fixture. No dead-equipment result yet.

**Native female layer gate corrected; BP/Python warning comparison queued (2026-10-16, 18:57 Singapore):**
NetShooterNetwork01 FAILS the independent cross-peer layer gate. Actual owner A
has Feminine native combined tags and native PickBestAnimLayer selects linked
Feminine Rifle/Unarmed classes, while dedicated authority has empty tags and
default classes. Both satisfy their local native selection. Require exact
local tag/native-selected/actual-linked state, equal layer selection only when
tags agree, plus exact common montage/dead-state outcomes. Add negative models;
no policy/animation/replication writes changed. Add explicit temporary CDO
BlueprintFallback baseline selector and exact restore, so the invalid native
tag-map weak-owner warning can be compared, not dismissed speculatively.
Models PASS 840. Serial queue: NetShooterBlueprintBaseline01,
NetShooterNetwork02, DeathDifferential01; stop on a failed lane. Death reuses
the accepted actual lethal GE/Death/Cue/native timer/respawn five-pair harness,
with original/Python equipment instance selection and a declared native empty
Quickbar-slot switch while health is truly dead/dying. Observe same-frame
animation before/after the naturally entered unequip callback, original source,
skip/no-animation-call counts, Profile and native respawn inventory model.
No manual lifecycle/health/death/animation writes; this is NOT natural-destroy
unequip evidence. Native results are not yet accepted. Inputs frozen throughout.

**Rifle/Shotgun owner integration accepted; prototype running (2026-10-16, 18:52 Singapore):**
RifleNetwork02 and ShotgunNetwork01 PASS independent equipment-plus-reload gates,
36 native authority rows each, two actual owning clients, Python native
equip/unequip pairing, exact per-peer native cosmetic tags and cross-peer
animation results. Strict error/ensure logs, three server-last normal exits,
restoration and 1,415 frozen inputs pass. This proves owners/authority, not a
remote-viewer equipment inspection. NetShooterNetwork01 now runs serially with
the original zero AutoReload grants. Its server emits native
GameplayTagBlueprintPropertyMap invalid weak-owner warnings during montage
interruption; sampled prior prototype baseline and accepted Rifle/Shotgun server
logs contain none. Investigate separately, do not claim warning-free playback or
dismiss as baseline without evidence. Native death branch still pending.

**Equipment network gate distinguishes native local cosmetics (2026-10-16, 18:46 Singapore):**
RifleNetwork01 FAILS the independent cross-peer state gate, not a runtime pass.
Only cosmetic tags differ: dedicated authority has none while both owners have
Masculine. Original Lyra CollectCombinedTags reads spawned child actors and
SpawnActorForEntry explicitly excludes NM_DedicatedServer. Animation layer,
montage and lifecycle observations agree. Add read-only per-peer native combined
tag evidence, require exact local tag equality, and retain exact cross-peer
animation-state equality. No gameplay/replication change. Models PASS 833,
including valid native empty-server tags and rejection of wrong local tags.
RifleNetwork02 now reruns all 36 reload rows plus equipment/source/role/restore,
strict logs, exits and frozen inputs. First failed evidence remains unchanged.

**Equipment GC accepted; real owner/authority integration running (2026-10-16, 18:39 Singapore):**
GCLifetime02 PASSES four-family original/Python alive comparison plus actual
native proxy collection with paused animation state unchanged. All original
fixtures/profiles restore; independent gate, strict logs, normal exit and 1,387
frozen inputs pass. No strong proxy/UObject is retained by diagnostic metadata.
Models PASS 832 after updating an old extracted fixture's optional observer
fields. RifleNetwork01 reuses the proven two-client/native Playing/reload RPC
lane, with read-only equipment lifecycle observations before native temporary
grant and through actual replica unequip; native animation/replication is not
written/replayed. Both authored-asset proofs are frozen. Require native owner
and authority role/type/layer/montage/source pairing plus all 36 reload rows,
exact restore and server-last exits. Network/death branch remain unaccepted.

**Equipment GC first run finds collected proxy; optional lookup corrected (2026-10-16, 18:33 Singapore):**
GCLifetime01 FAILS the probe's missing-object lookup: native GC already removes
the paused Pistol proxy, but ue.find_object raises "unable to find object ..."
instead of returning None. No animation difference was yet observed/accepted.
Catch only that exact expected missing-object diagnostic; all other lookup
errors still propagate, with an extracted regression model. Models PASS 828.
GCLifetime02 now retries the full four-family proxy-disappearance/paused-state
matrix and original alive lifecycle comparison. Keep failed report/logs; no
gameplay or animation-state workaround, no source/asset edits during this run.

**Equipment alive differential accepted; native proxy GC lane running (2026-10-16, 18:31 Singapore):**
Differential01 PASSES four actual original/Python family pairs, natural native
equip/unequip, actual linked layer/montage, outer native C++ time update,
same-instance Profile preservation, source/type and exact inventory/CDO/profile
restore. Default native Python equip is observed. Independent gate, strict logs,
normal exit and 1,387 frozen inputs pass. No death/network/GC acceptance yet.
Add bounded proxy path metadata only, never a strong UObject reference. Models
PASS 827. GCLifetime01 runs the same matrix and pauses each Python equip,
requests native GC, waits actual proxy disappearance and compares paused native
animation state before/after. No active montage is invented for prototype
defaults. Death/native network and whole-version acceptance remain due.

**Equipment instance authored; four-family native alive lane running (2026-10-16, 18:21 Singapore):**
Assets01 PASSES retained B_WeaponInstance_Base class, three original public
signatures, all original graphs and full CDO snapshot except the two declared
Mixin config fields. No GAS End adapter is added to this UObject. Models PASS
826. Differential01 now runs four actual inventory-granted weapon families,
original/Python CDO-selected equip/unequip pairs and same-instance Profile
switch. A declared read-only wrapper observes naturally entered lifecycle
handlers before the next weapon overwrites mesh state; it delegates once to
the exact production/original callable, never manually replays an event.
Observe actual tags/linked layer/montage, source item/type and outer native C++
equip-time update; require original inventory, CDO and observer restoration.
Alive standalone only: native death branch, GC stress and network are not yet
tested. No runtime acceptance, C++ compile, official/animation edit or package.

**Reload final regressions accepted; equipment-instance authoring running (2026-10-16, 18:07 Singapore):**
All six PostFamily pistol/Rifle/Shotgun standalone/network regressions PASS
independent gates, strict logs, normal exits and frozen inputs on the final
fixture/absence/capacity hooks. Prototype standalone/network already use that
same final implementation. Reload family is bounded accepted, not full 0.11.
Begin B_WeaponInstance_Base BP business: Python selects original native cosmetic
tags/layer and montage factory; dead/dying unequip retains the original skip.
Original C++ equipment lifecycle/time/device feedback, animation algorithms,
assets/ABPs remain. Original macro callback outputs are all disconnected, so no
new Python listener/proxy ownership is introduced. Models PASS 822. Assets01 is
RUNNING retained Interface/CDO authoring; original public signatures, all graphs
and full native CDO export (excluding only new Mixin selector/Set) must match.
No runtime acceptance yet; no C++ build/official edit/cook/package.

**Four reload families accepted in bounded lanes; final serial regressions running (2026-10-16, 17:54 Singapore):**
NetShooterNetwork01 PASSES 36 authority rows / nine pairs per real owner,
original no-AutoReload grant configuration, actual ammo replication and exact
original pistol inventory/equipment/AutoReload restoration. Independent gate,
strict logs, three server-last exits and 1,391 frozen inputs pass. Together,
pistol/Rifle/Shotgun/prototype each have standalone and two-owner native proof;
no other weapon business or whole-version acceptance is implied.
Final unchanged-input regressions now run serially: PostFamily-pistol-, rifle-,
shotgun-Standalone01, then the same three Network01 lanes. No second concurrent
native lane, no source/Overlay/Test edits while that queue runs. Models remain
PASS 816. Next independent runtime business preparation follows afterward.

**NetShooter standalone accepted; prototype two-owner lane running (2026-10-16, 17:49 Singapore):**
NetShooterStandalone01 PASSES ten original/Python pairs on the actual retained
prototype reload subclass and original item definition. Capacity-one cases and
absence of AutoReload are observed, not patched: grant count remains zero,
four native authority notify transfers move four rounds total, all original
pistol inventory/equipment/AutoReload restores after owned temporary removal.
Scopes 8/8, 16 native tasks, active/errors zero; independent gate, strict logs,
normal exit and 1,391 frozen inputs pass. Source item definitions/prototype
ability set now also freeze against official reference hashes. Models PASS
816. NetShooterNetwork01 runs 36 authority rows; post-final-fixture family
regressions and full 0.11 acceptance remain due. No compile/cook/package.

**Rifle/Shotgun network accepted; prototype original absence audited (2026-10-16, 17:45 Singapore):**
RifleNetwork02 and ShotgunNetwork01 each PASS 36 actual authority rows / nine
original-Python pairs per owner, native task/montage/tag barriers, real ammo
replication, unchanged foreign owner, temporary item-only removal and exact
original pistol inventory/AutoReload restore. Independent gates, strict logs,
three server-last normal exits and 1,381 frozen inputs pass for each lane.
FamilyAudit02 also PASSES read-only original ability-set reflection: NetShooter
grants FireAuto and Reload only, no AutoReload; native magazine capacity is 1.
Extend fixture for that real absence and capacity-one refusal/partial cases,
never invent an AutoReload grant. Models PASS 816; NetShooterStandalone01 now
runs ten real inherited-parent original/Python pairs. Prototype network and
post-family regressions remain due; full 0.11 remains open.

**Rifle network first run rejects ambiguous world selection; retry running (2026-10-16, 17:36 Singapore):**
RifleNetwork01 FAILS before gameplay: World Partition exposes multiple matching
subworlds, so the new family's len(all_worlds)==1 fixture assumption is invalid.
No inventory grant/case was accepted. Select the actual owning world from the
stable authority Pawn already proved by native Playing readiness instead of
weakening world/owner isolation. Extracted functional model covers exact Pawn
world selection and both owner-ready grants; models PASS 815. RifleNetwork02
now retries the full 36-row native matrix. All original/runtime gates remain.
Original source/config/plugin cpp/h/ini/descriptor string scan finds no explicit
NetShooter path; this is not an unused/runtime-accepted claim.

**Reload family audit accepted; Rifle two-owner lane running (2026-10-16, 17:33 Singapore):**
FamilyAudit01 PASSES five unchanged original child/item assets, native CDO
exports/defaults/compiled signatures and synchronous referencer closure. Native
prototype magazine capacity is 1; closure stays in its AbilitySet/WID/ID/Pickup
chain, not a default map. Dynamic source audit and prototype runtime remain due;
do not label it unused or alter its data. Add two-stage real-owner family
fixtures: client saves original pistol baseline read-only; authority grants
temporary weapon, waits equipment readiness; clients wait actual replication.
After all cases authority removes only owned temporary items and both clients
wait original pistol/AutoReload replication before normal exit. Models PASS
814. RifleNetwork01 now runs 36 native authority rows; Shotgun network, final
family regressions and version completion remain open. One native lane only.

**ReloadMagazine Shotgun standalone accepted; original family audit running (2026-10-16, 17:29 Singapore):**
ShotgunStandalone01 PASSES all ten actual retained-subclass original/Python
pairs and native source montage/capacity/ammo/refusal/lifetime checks. Exact
original pistol item/equipment/AutoReload restore, 8/8 policy scopes, independent
gate, strict logs, normal exit and 1,381 frozen inputs pass. Rifle/Shotgun now
have standalone proof only; network and post-family pistol regression are due.
FamilyAudit01 is RUNNING read-only original child signatures/defaults plus
NetShooter item CDO export and synchronous native referencer closure. Do not
infer unused status from prototype folder naming; no asset save or gameplay
acceptance is claimed by this audit. No official changes/build/package.

**ReloadMagazine Rifle standalone accepted; Shotgun running (2026-10-16, 17:21 Singapore):**
RifleStandalone01 PASSES ten original/Python pairs on the actual retained Rifle
reload subclass, original native montage and native equipment SourceObject,
including both refusals, cancel/interruption/End/Profile/pause. Scopes balance
8/8, 16 native tasks, four authority notify transfers and active/errors zero.
Actual temporary Rifle removal restores exact original pistol inventory/item
identity, equipment and AutoReload. Independent gate, strict logs, normal exit
and 1,381 frozen inputs pass, including unchanged original child assets.
ShotgunStandalone01 now runs the same ten-pair matrix with its actual native
capacity/montage. Rifle/Shotgun network and pistol fixture-regression remain due.

**ReloadMagazine Rifle family standalone running (2026-10-16, 17:18 Singapore):**
Add native authority-only temporary Rifle/Shotgun equipment fixtures, original
pistol inventory identity/AutoReload baseline, owned-item-only rollback and
foreign-slot/item rejection. Initial partial ammo respects each original
magazine capacity. Extend report gate to exact original reload subclass;
runtime driver freezes all four original weapon child asset hashes in both
reference/stage, without editing them. Models PASS 811. RifleStandalone01 now
runs all ten original/Python native input/montage/ammo/refusal/lifetime pairs.
Remaining family network coverage and post-fixture pistol regression remain
open. No C++ build, extra native lane or official edits.

**ReloadMagazine post-hook standalone accepted; weapon family next (2026-10-16, 17:14 Singapore):**
Differential02 PASSES all ten post-hook/readiness original-Python standalone
pairs, independent gate, strict logs, normal exit and 1,371 frozen inputs.
Pistol reload now has bounded standalone, two-owner network and matching
regression evidence; other weapon-family/version completion is not implied.
Continue actual native Rifle/Shotgun equipment grants and inherited parent
policy with their original classes/montages/capacities. Temporary native fixture
items must restore original pistol identity/equipment and remove only their own
item, never unknown foreign inventory. No new C++ build or official changes.

**ReloadMagazine two-owner network accepted; final standalone running (2026-10-16, 17:12 Singapore):**
Network03 PASSES all 36 authority trials / nine original-Python pairs per real
owner. Server role/task/montage/tag barriers precede early intervention; actual
authority ammo and owner replica match, foreign owner stays exact, all native
fixtures and AutoReload state restore. Python scopes balance authority 14/14,
owners 7/7 each, active/errors zero. Authority executes six actual Python ammo
transfers; clients zero authority transfers and three real non-authority notify
branches each. Independent gate, strict logs, three server-last normal exits
and 1,371 frozen inputs pass. No replicated GameplayEvent bus, network pause,
packet-loss/travel/package, other weapon-family or whole-version completion
claim. Differential02 now runs all ten post-hook/readiness standalone pairs.

**ReloadMagazine second network rejects premature replica snapshot (2026-10-16, 17:09 Singapore):**
Network02 FAILS first BP authority-row acknowledgement, not production ammo
transfer. Diagnostics prove both clients' native Respawn instances inactive and
Quickbar instances active; active same-ASC Quickbar now hosts the read-only
source task. Server actually observes role 3, active reload, two tasks, original
montage, owned NoFiring and correct ammo 12/12, foreign owner unchanged. Owner
ack froze 0/24 at native ability End before inventory FastArray replication;
later true replication was incorrectly counted as a late callback. Keep failure.
Add separate may_capture_end hook: network waits actual expected replicated ammo
before final snapshot/no-late window, standalone remains unchanged. Extracted
barrier model rejects pre-replication snapshots; models PASS 805. Network03 now
runs the same full 36-row matrix. No production-policy/transport bypass change,
no error allowlist; network and standalone post-hook regression remain open.

**ReloadMagazine first network run rejected; readiness diagnostics and retry (2026-10-16, 17:06 Singapore):**
Network01 is FAILED/unaccepted, no business trials: startup strict log contains
the upstream Dataflow FDataflowToolNodeSnapshot::Date default-value check
(official header initializes FDateTime::Now), and both clients wait for the
fixture's active observer-ability requirement. Stop only its three exact owned
processes and retain logs/failed summary; no official edit or error allowlist.
Add bounded change-only readiness diagnostics with actual instance counts and
active flags; select an already-active same-ASC observer owner from native
AutoRespawn or Quickbar, without activating a probe ability. Network02 now
retries the same 36-row native business matrix. No C++ build or extra test lane.
Models remain PASS 804; network and post-helper regression remain open.

**ReloadMagazine ten-pair standalone accepted; two-owner network running (2026-10-16, 17:01 Singapore):**
Differential01 PASSES ten original/Python equipped-pistol pairs, actual native
montage ReloadDone, both GAS refusal tags, cancel/interruption/external End/
Profile/pause, native ammo conservation and exact player/AutoReload restore.
Scopes balance 8/8, source observers 20/20; independent gate, strict logs,
normal exit and 1,367 frozen inputs pass. Native End counters show the child's
empty event did not block inherited cleanup on this path; no speculative child
asset edits. A stronger gate also rechecks CanActivate execution and actual
native End/owned tag cleanup on this same report and passes. Models PASS 804.
Network01 is RUNNING two real owners, nine pairs each / 36 authority rows,
native-active/task/montage barrier before early End, authority-only ammo fixture,
actual replicated owner result, foreign owner isolation, restore and server-last
exit. Network pause is explicitly excluded. Post-helper standalone due; full
weapon-family and version completion remain open. No new C++ build/package.

**ReloadMagazine authored; ten-pair native standalone running (2026-10-16, 16:53 Singapore):**
Assets01 PASSES retained class/defaults/all original graphs plus activation,
CanActivate(ActorInfo, Handle), public ReloadAmmoIntoMagazine(State) and native
End signatures. Two disposable Overlay assets only; no official changes.
Original LocalPredicted/per-actor/input policy and bStopWhenAbilityEnds=False
are retained. Python outputs both ReturnValue/RelevantTags explicitly; fallback
CanActivate is deliberately omitted so native missing-method fallback preserves
the original output frame. Models PASS 797. Differential01 is RUNNING ten real
equipped-pistol input pairs, actual montage ReloadDone source observation,
authority ammo conservation, two refusal tags, cancel/interruption/native End/
Profile/pause and exact native fixture/AutoReload restore. Wait for the old
montage to finish before starting another trial; late native notifies are not
invented or replayed. Runtime/network acceptance remains open.

**DropWeapon final standalone accepted; ReloadMagazine next (2026-10-16, 16:44 Singapore):**
Differential03 PASSES four post-network-helper/counter original/Python pairs,
independent gate, strict logs, normal exit and 1,357 frozen inputs. DropWeapon
now has bounded native standalone, two-owner authority/replication and matching
regression evidence, not whole-version completion. Continue weapon magazine
reload business: original CanActivate failure tags, native montage/event wait,
authority-only ammo transfer and owned NoFiring tag cleanup. Original animation
assets/notifies, GAS tasks, native ammo storage/replication and original class
identity remain. No C++ build or official edit planned for this batch.

**DropWeapon two-owner network accepted; final standalone running (2026-10-16, 16:42 Singapore):**
Network01 PASSES 16 authority trials and four original/Python pairs per real
client. Actual native local-predicted client branches perform zero inventory
writes; native GAS authority activation deletes/cycles and actual owner
inventory/equipment replication matches authority. Original BP activation/End
is independently counted as well. Original item identities and exact fixture
state restore; foreign owner stays unchanged. Independent gate, strict logs,
three server-last normal exits and 1,357 frozen inputs pass. No replicated
GameplayEvent bus, world pickup, packet-loss/travel/package or version-close
claim. Differential03 now runs all four post-hook/counter standalone pairs.

**DropWeapon standalone accepted; two-owner network running (2026-10-16, 16:41 Singapore):**
Differential02 PASSES all four original-BP/Python pairs, independent gate,
strict logs, normal exit and 1,353 frozen inputs. Actual one-frame EnhancedInput
reaches original delete/cycle behavior, including the native empty-slot branch;
all original item identities/equipment restore and no late activation remains.
Python activation/authority/cycle/native-End counts are 4/4/4/4, with three
actual items removed. Network01 is now RUNNING two real client owners and 16
authority trials. It checks local predicted non-authority versus native GAS RPC
authority mutation, replicated equipment, untouched foreign owner, exact native
fixture restore and server-last normal exits. Models PASS 784; network and
post-network-helper standalone regression are not yet accepted. No C++ build,
cook/package, official Lyra/Engine edit or world-pickup feature added.

**DropWeapon first pair passes; native cycle expectation corrected (2026-10-16, 16:29 Singapore):**
Differential01 completes rifle-to-pistol on both sides, then FAILS the next
original-BP case's expected slot. Source confirms native RemoveItemFromSlot
sets ActiveSlotIndex=-1; subsequent CycleActiveSlotForward begins from slot 0,
so the original pistol wins even when a shotgun remains in slot 2. Do not
rewrite that native behavior. Rename the case rifle-with-shotgun and expect 0;
also retain current native inventory/equipment observations on failure. Python
business is unchanged. Differential02 is RUNNING four full original/Python
pairs, one EnhancedInput press each, exact original item/slot/model restore and
late-reactivation checks. Models PASS 778. Runtime/network not accepted yet.

**ADS final regression accepted; DropWeapon authored (2026-10-16, 16:21 Singapore):**
ADS Differential05 PASSES all six post-network-plan/hook standalone pairs,
including the standalone-only pause case, independent gate/strict logs/normal
exit and 1,346 frozen inputs. ADS now has bounded standalone, shared-parent UI,
two-owner network and matching regression evidence. No network pause, audible
audio, packet-loss/travel/package or whole-version completion claim.
Continue GA_DropWeapon: Assets01 PASSES original LocalPredicted/per-actor/input
defaults, retained class/activation signature/full graph and guarded native End
adapter. Python retains the actual original delete-from-slot/inventory then
cycle behavior; no new world pickup is invented. Native authority/Quickbar/
inventory/equipment/GAS remain native. Runtime fixture/models are next; authoring
is not runtime acceptance. No C++ build or official/template edit.

**ADS two-owner native network accepted; final standalone regression running (2026-10-16, 16:18 Singapore):**
Network02 PASSES 20 authority trials and five original/Python pairs per real
client. Actual authority active ability, 0.5 speed, ADS camera mode and native
wait task precede intervention; original state restores and the foreign owner's
camera/speed/equipment/input stays exact. Each owner observes one typed on/off
pair and real reticle response per trial. Dedicated authority executes zero
local UI/mapping/helper calls, not a replicated UI bus. Scopes close server
10/10, clients 5/5 each, helpers 11/11 each, active/errors zero. Independent gate,
strict logs, three server-last normal exits and 1,346 frozen inputs pass. Pause
remains standalone-only. Differential05 runs all six post-hook/plan standalone
pairs. No whole-version completion; continue the next runtime business batch.

**ADS first network run rejects unauthorized client pause; five-pair lane running (2026-10-16, 16:13 Singapore):**
Network01 records ten authority rows, then the original-BP client pause call is
refused by native SetGamePaused. Its disconnect invalidates the server probe's
cached Pawn afterward; this is not an accepted network result. Do not force
pause authority or change native pause policy. Keep paused-world-time as the
accepted standalone-only case; network explicitly excludes pause and tests five
original/Python pairs per owner (20 authority rows). Generic fixture/gate plan
selection now distinguishes these scopes, with current local-only UI/state/RPC/
foreign-owner checks unchanged. Network02 is running, models PASS 770. Standalone
post-plan/hook regression remains due. No network pause or version completion.

**ADS shared-parent UI accepted; two-owner native lane running (2026-10-16, 16:11 Singapore):**
SharedWidget01 FAILS before any grant case because the older UI probe reads a
stale wrapper in world.all_objects. Apply the same validity-before-is_a guard;
SharedWidget02 PASSES all eight native grant/remove/Profile-lifetime cases,
independent gate, strict logs/normal exit and 1,342 frozen inputs. Existing
shared UI policy/defaults still behave correctly after parent gates/profiles.
Network01 is RUNNING 24 authority trials with two real local input/reticle/UI
owners. A held-state barrier requires actual native authority activation, half
speed, ADS camera mode and WaitInputRelease task before owner intervention.
Authority state/foreign owner/cleanup are compared independently; UI and mapping
business must remain local-only, not a replicated message bus. Client pause is
explicitly owning-client-only. Host models PASS 770. Network and post-hook
standalone regression remain due; no version/pilot completion claim.

**ADS six-pair native standalone accepted; shared-parent UI regression running (2026-10-16, 16:05 Singapore):**
Differential04 PASSES six original/Python pairs through the one-parent typed
gates. Actual EnhancedInput selects native ADS camera mode, halves native
MaxWalkSpeed by the retained 0.5 multiplier, adds the original mapping at priority
11, and sends exactly [on,off] through the original typed UI channel to the real
production reticle. Release/cancel/external end/Profile teardown/repeat/pause
restore camera/speed/mapping and retain valid shared widget grant handles.
Python activations/task scopes close 6/6, six native WaitInputRelease tasks,
three actual release callbacks and balanced 13/13 rooted transport helpers;
the extra global off/remove counters belong to original-fallback Profile cleanup,
not duplicate messages. Zero active/errors, independent gate, strict logs,
normal exit and 1,342 frozen inputs pass. SharedWidget01 is RUNNING the existing
eight-case native grant/remove UI suite against the extended parent Set. Two-
client ADS and post-network helper regression remain due; 0.11 stays open.

**ADS actual Python routing proven; same-frame input probe duplication fixed (2026-10-16, 16:03 Singapore):**
Differential03 reaches all six pairs with real Python counters, but final
independent gate FAILS duplicate source UI messages. Original and Python both
show [on,off,on,off] for cancel/external-end/Profile switch: the probe queued
held=True and ended+released=False in one input frame, so native input reactivated
the ended ability. Do not waive message counts. Hold frames now inject only true;
an intervention/release frame injects only false. Two focused probe models reject
the old same-frame mixed injection. Pause runs once; native original/Python both
observe input-release end during pause, then restore after unpause. Differential04
is running with 765 host models PASS; no ADS runtime acceptance yet. Shared-parent
UI lifecycle and two-client validation remain due. Retained animation tag-owner
warnings were also seen on the original-BP-only attempt; no engine/ABP edit or
warning-free animation claim is made.

**ADS inherited-router gap fixed with shared-parent typed gates (2026-10-16, 15:59 Singapore):**
Differential02 FAILS at paused timeout after repeated reactivation. Its policy
counters stay zero even for nominal Python sides, so none of its intermediate
rows are accepted. ADS inherits an already-routed parent; current UEP intentionally
does not install related parent/child routers. The child's old profile names
only selected shared UI, leaving its own ADS business in BP. ParentAssets01
PASSES one-parent authoring: three typed bool gates on GA_AbilityWithWidget and
two extra parent Set profiles ADSPython/ADSBlueprintFallback; the original ADS
Activate/End/Broadcast bodies remain behind gates, public signatures/defaults/
business graph semantics preserve. Existing parent UI profiles/default preserve.
Old independent DA_ADSAbilityMixin stage/Overlay drafts are retired recoverably
under ParentAssets01/RetiredAssets with four before-asset backup pairs. No core
router rule, engine source or binary is changed. Runtime probe now requires the
first actual ADSPython activation counter to increase, uses specific parent
profiles and pauses exactly once, then exits through native release instead of
reentering hold. Differential03 is running; shared-parent UI regression is due.
Models PASS 763. No ADS runtime/network acceptance yet.

**ADS first runtime probe fails before activation; validity guard fixed (2026-10-16, 15:47 Singapore):**
Differential01 FAILS with zero ADS activations: world.all_objects includes a
stale UObject wrapper and the reticle search read its class before checking
validity. Failed cleanup also attempted release before its action initialized.
Guard native validity before class/owner access and guard partial initialization
during cleanup. Production ADS policy is unchanged. Differential02 is running;
models still PASS 763. No ADS native acceptance yet.

**ADS authored; six-pair native input/camera/mapping/UI differential running (2026-10-16, 15:46 Singapore):**
Assets03 PASSES retained GA_ADS class, original LocalPredicted/per-actor/input
policy, ADSMultiplier 0.5, inherited touch-widget configuration, public activation/
end/BroadcastToUI/shared UI signatures and original business graph semantics.
Assets01/02 FAIL on a transient inherited FUNC_Native snapshot: loading the
already-migrated shared parent discovers runtime injection. Unregister again
after load before signature capture, then compare restored original signatures;
no flags are masked, serialized/patched or waived. Python uses original native
camera, CharacterMovement speed, mapping priority 11/options, audio calls and
WaitInputRelease. Typed ADS messages reuse the accepted compiled VM adapter;
retained fallback runs original ADS business, while both use already-accepted
shared parent UI grant/removal policy. Differential01 is RUNNING six original/
Python pairs with real input, camera-mode selection, native speed/mapping queries,
actual source messages and production reticle on/off, cancel/end/Profile/pause/
repeat cleanup. No probe camera/speed/mapping/message write. Models PASS 763;
no ADS runtime/network or audible-audio acceptance yet. Continue, do not release.

**Hero Heal standalone/network/foreign-lock regressions accepted (2026-10-16, 15:34 Singapore):**
Differential03 PASSES all eight post-helper original/Python pairs plus three
Python-only native foreign-input-lock regressions: montage end, state end and
Profile teardown. Each adds one independent native controller lock, observes it
survive native Heal cleanup, then removes it once and verifies exact unlocked
baseline. Each has one policy lock/unlock and one closed task scope; no late
callback, native task or effect remains. All native Health outcomes remain
75 -> 80, original player/ability specs restore, total policy scopes close 11/11.
Independent gate, strict logs/normal exit and 1,331 frozen inputs pass. Network06
remains bounded accepted under its documented authority-input and heal-before-
end fixtures; no natural original-BP external-lock or early-cancel equivalence
claim. Host models PASS 754. Continue ADS; 0.11 is not complete.

**Hero Heal bounded native network accepted; regression running (2026-10-16, 15:31 Singapore):**
Network06 PASSES 28 authority trials and seven original/Python pairs per real
client. Actual first authority healing, original GE/task activation, native
GAS input/end, authority cleanup and replicated owner Health/effect removal all
pass. Foreign fixture-baseline states stay exact; original Health/equipment/
ability specs restore. Native authority input suspension counts A=0/B0=1 are
restored exactly 0/1. Policy scopes close server 14/14 and clients 7/7 each,
zero active/errors. Independent report gate, strict logs, three server-last
normal exits and 1,331 frozen inputs pass. This is declared heal-before-end
and normalized authority input-fixture evidence, not early-cancel/latency,
natural original-BP foreign-lock preservation or replicated state-event proof.
Differential03 is RUNNING eight post-helper standalone pairs plus three Python
foreign-input-lock regressions (montage end, state end, Profile teardown).
Host models PASS 754. Pilot/version remain open until these regressions pass.

**Hero Heal Network05 catches pre-first-heal input timing (2026-10-16, 15:28 Singapore):**
Network05 completes authority scheduling but B0's final gate FAILS: Python's
native-input-press row confirms authority Health 75 rather than a healing delta;
the client ended before a first native GE execution. No "effect applied" counter
is treated as healing proof. Network06 explicitly gates cancellation/press/state
actions on actual authority task triple, active GE and first Health increase,
then retains the native effect/replication/rollback checks. This is a bounded
"heal then end" matrix, not an early-cancel/latency guarantee. Native skill
duration/effect are not changed and no test heal is supplied. Persist each
authority row independently so a failing peer shutdown does not erase evidence.
Network06 is running, models PASS 753. Separate foreign-lock native regression
and post-helper standalone regression remain due.

**Hero Heal Network04 completes rows but fails final local-state predicate (2026-10-16, 15:26 Singapore):**
All 28 authority rows complete, then both clients' independent shutdown gates
FAIL: local EndAbilityState immediately unlocks owner movement, but cannot remove
the server-owned replicated GE while the authority ability is still active.
This is a network timing/authority distinction, not an event-replication bus.
Keep the immediate-effect requirement in standalone; network instead requires
local movement release while active plus actual authority GE/task cleanup and
replicated owner effect removal before final ACK. Tests reject the missing local
movement release and any missing authority confirmation/cleanup. Network05 is
running, models PASS 753. No full network/pilot acceptance yet; separate Python
foreign-input-lock native regression remains due.

**Hero Heal original-BP double-unlock and replication lag exposed (2026-10-16, 15:24 Singapore):**
Network03 records fourteen A authority trials, then FAILS when B starts because
A's original input_ignored true became false. The very first original-BP trial
already reports an unrestored input baseline; its end event and native state-end
callback both execute the same unlock body. Python cleanup is idempotent, but
the comparison inherits the foreign lock already consumed by that BP trial.
Keep this failure as evidence; do not call the natural preexisting-lock baseline
equivalent. For routine differential comparison, Network04 uses an explicit
native-only authority input fixture: pop existing locks with SetIgnoreMoveInput
false until clear (bounded 16), record the exact count, and push exactly that
count back at final restoration. No raw counter write or Reset is used. Native
foreign-state isolation remains strict against this declared fixture baseline.
Separately, owner local End can precede replicated authoritative GE removal;
require actual owner effect/task cleanup plus authoritative Health agreement
before final ACK. Network04 is running; an independent Python foreign-lock
preservation regression is still required before accepting this pilot.

**Hero Heal foreign-owner failure diagnosed as wrong input baseline (2026-10-16, 15:21 Singapore):**
Network02 captures identical original/current foreign Health 100, pistol model,
ammo 12/48 and input_ignored true. The probe incorrectly required the remote
authority controller to be unblocked, even though its original state was already
blocked. Compare exact original/current input flags instead; also require the
target controller's post-end/final state to equal its original authority input
baseline. No ResetIgnoreMoveInput, raw counter write or forced unlock is used.
Network03 is running the same full 28-trial gate. Earlier failures are retained.

**Hero Heal first network run fails foreign-owner isolation (2026-10-16, 15:12 Singapore):**
Network01 FAILS before any accepted authority trial: the first original-BP
case sees a foreign-owner health/equipment/input predicate fail. The saved
per-tick status predates the failure and lacks the differing values, so no
startup-race or cross-owner root cause is asserted. Add exact original/current
foreign snapshots and failed-trial capture; require Health fixture TargetActor
to equal the intended authority pawn. Preserve the strict isolation gate and
rerun to diagnose; no network acceptance yet.

**Hero Heal standalone accepted; native two-owner lane running (2026-10-16, 15:10 Singapore):**
Differential02 PASSES all eight native BP/Python pairs. Original infinite healing
GE raises Health from 75 to 80 on every side, then removes cleanly. Original
montage, native GAS PressInputID, cancellation/interruption, external end, active
Profile teardown, state-end cleanup while still active and paused world time
all pass. Python creates 24 native tasks, eight scopes close 8/8, no late callback
or original player/spec leak. Independent gate, strict logs, normal exit and
1,327 frozen inputs pass. Network01 is RUNNING seven pairs per real owner (28
authority trials), excluding world pause. Authority alone grants/removes the
fixture spec and sets/restores Health; clients only activate/press native GAS
input, wait for authoritative Health and confirm native replication. Original
LocalPredicted policy/montage/effect stay unchanged. Host models pass 752.
Network and post-helper standalone regression remain pending; 0.11 stays open.

**Hero Heal first native failure is a fixture duplicate ID (2026-10-16, 15:03 Singapore):**
Differential01 FAILS during the first original-BP trial's Health rollback:
setup and rollback reused one request ID, correctly rejected by the unchanged
bridge's duplicate-command protection. Python activations remain zero in this
failed run. Give each bounded native health request a unique monotonic ID;
retain duplicate/magnitude/authority safety checks, report native rejection
status and preserve failed-trial observations. Rerun the full differential;
no Hero Heal runtime acceptance yet.

**Hero Heal authored; eight-pair native differential running (2026-10-16, 15:01 Singapore):**
Assets01 PASSES the retained GA_Hero_Heal class, LocalPredicted/per-actor defaults,
original generic Unequip montage and GE_GameplayEffectPad_Heal, public activation/
end signatures and all original business graph semantics. An existing native
End event receives only guarded typed dispatch transport; Python cleanup does
not fall through into original BP cleanup, while fallback keeps that body.
Python uses native StartAbilityState, PlayMontageAndWait, WaitInputPress, original
GE application/removal and controller movement-input APIs. Differential01 is
RUNNING eight native BP/Python pairs, including original montage, native GAS
PressInputID, cancellation/interruption, external end, Profile teardown, state
end and paused world time. Native fixture grant/activate/input APIs and bounded
authority Health setup/rollback are explicit; no handler/delegate replay, new
montage/effect, raw Health property write or hardware/EnhancedInput claim.
Host models PASS 746. No Hero Heal runtime/network acceptance is claimed yet.

**AutoReload network and post-helper regression accepted (2026-10-16, 14:57 Singapore):**
Network01 PASSES 24 authority trials, six original/Python pairs per real client.
Each owner really fires twelve native rounds and automatically reloads; native
authority reload activation and empty magazine are observed separately, final
replicated ammo matches, original inventory restores and the foreign owner stays
unchanged. Original LocalOnly authority owner abilities remain inactive; server
NPC loops are separate and all 1,122 task scopes close. Client source observers
close 12/12 each and policy scopes close 46/46 and 85/85. Strict logs, independent
gate, three server-last normal exits and 1,317 frozen inputs pass. Differential02
also PASSES all six post-helper-refactor standalone pairs and 1,317 frozen inputs.
No replicated GameplayEvent bus, packet-loss/travel/package or whole-version
claim is made. Continue the distinct GA_Hero_Heal runtime policy next.

**AutoReload standalone accepted; two-client lane implemented (2026-10-16, 14:52 Singapore):**
Differential01 PASSES six original/Python native pairs, including real fire of all
twelve rounds and automatic original reload on both sides. One native reload
event, actual reload ability/tag, ammunition conservation, cancel/Profile end,
zero post-end callbacks and exact original equipment/ammo/aim restoration pass.
Independent report gate, strict logs, normal exit and 1,313 frozen inputs pass.
The two-client fixture now pauses owner loops before authority-only native ammo
setup/rollback, injects only real client EnhancedInput, and separately observes
authority reload/empty magazine, foreign-owner isolation and replicated final
ammo. Original LocalOnly policy remains unchanged: remote authority AutoReload
must stay inactive. Host models pass 735. Network runtime and post-helper
standalone regression are pending; no whole-version/release claim is made.

**Cosmetic regression accepted; AutoReload authored and native differential running (2026-10-16, 14:45 Singapore):**
Cosmetic Differential03 PASSES the post-helper-refactor four deterministic pairs
and sixteen native random trials with independent gate, strict logs/normal exit;
the cosmetic pilot now has matching bounded standalone/two-client evidence.
AutoReload Assets01 PASSES retained GA_Weapon_AutoReload class, original public
Activate/PeriodicCheck/CheckAmmoState signatures, complete graph digests,
LocalOnly/per-actor/OnSpawn defaults, PollInterval 0.25 and idle threshold ~0.66.
Only a guarded four-node native End adapter plus Mixin Set are added; no C++ build.
Python uses native WaitDelay, inventory/stat reads, typed native tag-interface
query and the original SendGameplayEvent(InputTag.Weapon.Reload, default payload).
One task scope closes before each new wait; per-instance metadata counters avoid
mixing AI polls with player evidence. World/task/source objects are not stored
in metadata history. Differential01 is RUNNING six native BP/Python pairs:
nonempty, empty/no-spare, empty/spare automatic actual reload, real EnhancedInput
fire-to-empty automatic reload, native cancellation and active Profile teardown.
Native inventory API setup/rollback is explicitly separate from the no-ammo-write
real-fire interval. Native event delivery, actual original reload ability/tag,
ammo conservation, task cleanup and ignored post-end callbacks are required.
Host models PASS 729; no AutoReload runtime/network acceptance is claimed yet.
GA_Hero_Heal is NOT the already migrated legacy GA_HealPickup asset and remains
pending. This does not finish 0.11 or authorize a commit/push/release.

**Cosmetic Network01 bounded native two-owner/two-viewer pilot accepted (2026-10-16, 14:31 Singapore):**
Network01 PASSES 48 authority trials across two owners, four deterministic
original/Python pairs plus sixteen random trials per owner. Each real client
independently observes 48 actual FastArray-driven body additions/removals, native
change delegates, expected class/no-collision/attachment and exact original
part/child-actor rollback. Viewer scopes each close 48/48. Dedicated-server
records contain only native part specifications, no cosmetic child actor; clients
execute zero choice-policy calls, proving native replication rather than replay
of a Python handler. Foreign authority part state stays exact. Independent gate,
strict logs, three normal server-last exits and 1,308 frozen inputs PASS.
Native part generation, ownership and animation remain native. Packet-loss,
travel/rejoin and a live-added component's possession turnover are not claimed.
Differential03 is RUNNING the complete post-network-helper standalone regression.
Continue later hero/weapon policies; this bounded pilot does not finish 0.11.

**Cosmetic standalone pilot accepted; native FastArray/two-viewer lane running (2026-10-16, 14:30 Singapore):**
Differential02 PASSES four deterministic native BP/Python pairs and sixteen
unseeded native RandomBool trials; each Profile exercises Manny and Quinn.
Actual native child actors, no-collision/attachment, retained component class/
owner, CDO default Python dispatch, Profile roundtrip and exact original part/
child-actor identities after native component EndPlay pass the independent gate,
strict logs/normal exit and 1,304 frozen inputs. No direct Python body spawn,
part-array mutation, seeded replay or animation edit occurs. Differential01
remains failed. Network01 is RUNNING at least 48 sequential authority trials
across two owners. The dedicated server retains native part specifications but
does not spawn cosmetic actors; both clients must independently observe actual
FastArray-created child actors, the native change delegate and exact rollback.
Files schedule barriers only, never supply parts or replication. Native scopes
are test-owned and must balance on both peers. 715 host models PASS. Network and
post-helper-refactor standalone regression remain open; no whole-version pass.

**Cosmetic Differential01 FAILS in pre-test native observation (2026-10-16, 14:23 Singapore):**
No cosmetic comparison trial begins: GetChildActor is a C++-only getter, not a
reflected function. The independent probe must read the reflected ChildActor
property instead. Add a focused read-model test; isolate native bots during
Warmup as well as active trials and avoid duplicate cleanup reads before a
baseline exists. Retain this failure; production choice policy is not changed.

**Death regression accepted; two cosmetic decisions authored, runtime running (2026-10-16, 14:21 Singapore):**
Death Differential05 PASSES the complete post-refactor five native pairs,
independent gate, strict logs/normal exit and 1,287 frozen inputs; scopes 5/5,
source scopes 10/10, actual wait completions two, active zero/errors empty.
Cosmetics Assets01 PASSES four output assets for B_CharacterSelection and
B_PickRandomCharacter plus their Mixin Sets. Original classes, BeginPlay
signatures, component replication/auto-activation defaults, configured part
classes and complete business graph digests remain; official hashes unchanged.
Only native Actor-count/remainder or native RandomBool -> native AddCharacterPart
choice is Python. Controller/Pawn part ownership, spawning, attachment, FastArray
replication, possession change, cleanup and animation remain original native.
Differential01 is RUNNING four deterministic original/Python pairs and at least
sixteen native random trials, retained-class/default-CDO BeginPlay, native body
creation/no-collision/attachment, inactive Profile roundtrip and exact original
part/child-actor identity rollback. Random sequence replay is NOT claimed; both
Manny/Quinn choices are required independently per Profile. Native cosmetic
runtime/network acceptance is not yet claimed. Host models PASS 708. No C++ build.

**Death Network05 bounded two-owner/two-viewer pilot accepted (2026-10-16, 14:15 Singapore):**
Network05 PASSES twenty native authority trials, twenty independent observations
on EACH real client, independent report gate, strict native logs, three normal
server-last exits and 1,284 frozen inputs. Actual source GameplayEvents come from
the lethal native GE; server source observers close 20/20 and deliver with Death
active. Each client sees one original OnBurst per trial with native payload,
owning-client ServerInitiated activation/camera and original respawn; the foreign
authority Pawn/Health/death state stays exact. Native classes and noncancelable
policy remain. Scopes server 10/10, clients each 5/5, all active zero/errors empty.
Four authority Python waits really finish after eight seconds. Client waits are
ended by native replicated server end (zero local completions); do not claim a
local timer completion or replicated GameplayEvent bus. Explicit nine-second
respawn fixture values on authority/owner restore after death and on errors;
the original five-second production preemption remains a separate pair.
Threaded native loading is process-local and recorded, not an Engine change.
Differential05 is RUNNING the complete post-refactor standalone five-pair
regression. New cosmetic decision policies/host models exist but are not native
accepted or authored yet; 702 host models pass. This does not finish 0.11.

**Death Network04 reaches twenty trials but independent timer gate FAILS (2026-10-16, 14:08 Singapore):**
All twenty native authority trials and both twenty-row viewer reports complete;
real lethal damage, native ServerInitiated owning-client activation/camera,
one Cue on each client and scope cleanup are recorded. Native process/log checks
pass, but the independent gate FAILS: the nominal nine-second respawn fixture
still permits native Death to end around five seconds, waits_finished zero.
Do not accept the peer reports alone or rewrite this failed result. Keep the
explicit fixture value on authority AND owning client for the complete death
interval, assert it each active tick, restore on end and every error cleanup,
and rerun. Source/event scopes close 20/20; policy server 10/10, clients 5/5,
all active zero/errors empty. Neither Death Duration nor production CDO changes.

**Death Network03 identifies the dedicated-authority probe-owner error (2026-10-16, 13:59 Singapore):**
Threaded loading reaches Playing. The bounded prepare gate FAILS with exact
native evidence: Death instances 1, AutoRespawn instances 1, AutoRespawn active
false, NetExecutionPolicy 0 (LocalPredicted). The original BP still binds health
via OnPawnAvatarSet; its active flag is not a valid authority readiness gate.
Do not change that native policy or force activation. The dedicated server's
test-only WaitGameplayEvent observer will instead be owned by Death itself,
bound before lethal GE and required to deliver once while that owner is active.
Native GAS activates Death before dispatching the generic event delegate. Native
Death end also destroys that test task; close the test subscription scope
independently. Standalone keeps its previously verified active observer owner.

**Two hero shells source-reviewed; no Python policy to move (2026-10-16, 13:58 Singapore):**
SourceAudit01 verifies original/stage asset hashes and all original graph nodes
for Character_Default and B_SimpleHeroPawn. They contain only empty events and
parent construction/BeginPlay calls; no independent business nodes. Retain the
original shell assets rather than generate Python no-ops. The 37 static candidate
count stays unchanged and parent-Python inheritance runtime remains explicitly
pending, not accepted from this source audit.

**Death Network02 fails native map streaming before Python test ticks (2026-10-16, 13:56 Singapore):**
The server exits 3 with AsyncLoading2.cpp:13069 "Loading is stuck, flush will
never finish" inside WorldPartition/NotifyBeginPlay. No Python script stack or
test status is reached; both clients time out. The driver closes its owned
peers. This is a native startup FAIL, not a Death policy verdict. The earlier
Network01 prepare-gate cause remains unconfirmed. Both runs used the editor's
single-thread async loader despite the later config CVar. The next run explicitly
requests the engine-supported -AsyncLoadingThread command-line switch and records
that choice; this changes only this test process, not Engine/project source,
assets or persistent settings. Preserve failures and continue exact diagnostics.

**Death Network01 diagnostic aborted before damage (2026-10-16, 13:51 Singapore):**
The first dedicated server/two-client lane reaches native Playing and distinct
owners but remains in the prepare gate before any damage. Stop only its verified
owned server (PID 51284, run fd9c5ca9-b324-4242-a82a-18347ba0b6bd); the driver closes
its peers. This is an ABORTED diagnostic, not a pass or an accepted normal exit.
Add explicit native Death/respawn-instance counts, active/net-policy/readiness
details and bounded phase timeouts so the next lane identifies the actual
readiness condition instead of waiting silently. No inferred cause is accepted.

**Death standalone five-pair pilot accepted; native two-viewer lane running (2026-10-16, 13:48 Singapore):**
Differential04 PASSES all five original/Python pairs, independent report gate,
strict logs, normal exit and 1,281 frozen inputs. Original production respawn
preempts at 5.00s; the explicit restored nine-second respawn fixture allows two
real eight-second Death WaitDelay completions. Cancellation remains refused;
external native end and active Profile teardown close the original death path.
Native source observers close 10/10; policy scopes 5/5, five camera/Cue/wait
executions, two wait completions, active zero/errors empty. Earlier Differential01
through 03 stay failed. No whole-version, packaging or network acceptance yet.
The shared fixture's attach/expected-Cue hooks were subsequently factored for
dedicated-server reuse; a post-refactor standalone regression remains due.
Network01 is now RUNNING one native server and two real clients, twenty
sequential deaths/respawns, both clients independently observing the original
GCNL_Death OnBurst (always forwarding its BP), owning-client ServerInitiated
activation/camera/native payload, exact foreign-owner health/Pawn state and
server-last normal exit. Hardware, packet loss, travel/rejoin and UI timer
presentation are not claimed. Host report/policy models PASS 696; no C++ build.

**Death Differential03 exposes original native five-second preemption (2026-10-16, 10:18 Singapore):**
All four BP/Python rows reach native zero Health, camera/Cue and original respawn,
but the final gate correctly FAILS its incorrect eight-second-completion claim:
both original BP and Python are ended by unchanged GA_AutoRespawn at 5.00s;
neither WaitDelay completion fires. Do not waive this check. Add a fifth pair for
that unchanged production path. For the two eight-second timer/cancel-refused
pairs only, temporarily set the original AutoRespawn instance's delay to nine
seconds before lethal GE, then immediately restore its original five-second
property in finally (the native latent delay has captured nine). Death Duration
and CDO/assets stay unchanged. Require actual eight-second completion, original
five-second preemption and verified fixture rollback independently.

**Death Differential02 fails observation, real native lethal GE succeeds (2026-10-16, 10:15 Singapore):**
The original native damage GE reaches Health zero and activates the original BP
death ability. Independent Cue/source observation fails on an incorrectly named
reflection query (EffectContextGetInstigator, actual 5.8.1 name includes Actor).
Keep this failed run. Correct the probe and always forward the original Cue even
if recording fails; rerun all four native pairs, no partial acceptance.

**Death Differential01 failed before activation; fixture repair (2026-10-16, 10:14 Singapore):**
The first native Death run FAILS before ability activation: its fixture called
the existing bounded/nonlethal bridge with -100 Health. That API intentionally
rejects magnitude over 25 and lethal damage; its safeguards remain unchanged.
The replacement fixture applies the original GE_Damage_Basic_SetByCaller through
native MakeOutgoingSpec/AssignTagSetByCallerMagnitude/BP_ApplyGameplayEffectSpecToSelf.
No direct Health write or synthetic death GameplayEvent is used. Original GE
asset provenance is now required by the runtime driver. Death runtime is still
NOT accepted; rerun the full differential and then the two-owner lane.

**0.11 Quickslot two-owner RPC/equipment pilot accepted; Death runtime pending (2026-10-16, 09:30 Singapore):**
Quickslot Differential01 PASSES ten native BP/Python pairs, independent gate,
strict logs/normal exit and 1,261 frozen hashes; scopes 20/20, sixty native
tasks, no active/error entries. Network01 PASSES forty sequential trials across
two real owners: local native GAS event delivery reaches the selected BP/Python
task, retained native Quickbar Server RPC changes authoritative slot/equipment,
and exact server/owning-client native models agree. The other owner's inventory
and equipment remain unchanged in every trial. Original item/slot/equipment
identities restore on server and both clients, native OnSpawn Python scope
ownership is explicitly checked, original active ability restored. Three normal
server-last exits, independent gate, strict logs and 1,265 hashes pass. Server
scopes 56/56 (168 tasks), clients each 14/14 (42 tasks), all active zero/errors
empty. Server selection callback counts are zero: this is local GAS-event intent
plus native component RPC, NOT replicated GameplayEvents. Hardware/EnhancedInput,
packet-loss and new UI presentation comparison are NOT claimed. Continue later
hero/weapon BP batches; this does not finish 0.11.
GA_Hero_Death Python camera/cue/native WaitDelay orchestration and original BP
fallback are authored by Death Assets01, preserving original eight-second
Duration, camera class, EventData signature, ServerInitiated/per-actor defaults
and original graph. Native death's noncancelable flag is not changed. Five
policy models plus twelve new death/network-report rejection tests bring host
models to 684 passes. Death Differential01 is RUNNING actual lethal GAS damage,
independent source GameplayEvent and original GCNL_Death OnBurst observation,
native timer/cancel-refused/external-end/Profile switch and original respawn.
No Death runtime/network acceptance is claimed yet. No C++ build/cook occurred.

**0.11 Quickslot Python tasks authored; native differential running (2026-10-16, 09:13 Singapore):**
GA_QuickbarSlots retains its BP class, original EventGraph digest, Activate
signature, per-actor/local-predicted/OnSpawn defaults, native GAS event tasks and
QuickBar/equipment/RPC implementation. Only the three-tag decision orchestration
is Python. Assets01 in 20261016-quickslot PASSES Interface/CDO/4-node native End
adapter authoring, two output assets and unchanged official-reference checks;
no C++ build/cook. Host models pass 667. Differential01 is RUNNING ten native
BP/Python pairs using real inventory/equipment and native SendGameplayEventToActor:
fraction/negative/out-of-range selection, forward/back/wrap, unrelated event,
cancel and active Profile switch plus explicit native reactivation. It requires
three native tasks before, zero after end, ignored post-end events and exact
inventory/equipment parity, then original item/slot/movement/aim/Profile/active
ability restoration. A GameplayEvent API producer is NOT EnhancedInput or hardware
input. No native runtime or two-client result is yet claimed for Quickslot.

**0.11 Jump bounded two-owner acceptance passes; continue Quickbar orchestration (2026-10-16, 09:06 Singapore):**
Network01/02 FAIL the foreign-owner-idle gate at the unchanged native Warmup ->
Playing transition: the old other Pawn stops movement (mode None), Health 100,
Jump inactive. Capture post-transition Pawns instead. Network03 is deliberately
ABORTED after diagnosing an impossible server-side local-input readiness gate;
the dedicated server's remote Pawns do not bind local InputComponents. Only its
exact owned diagnostic server was stopped; the driver closed its owned peers.
No acceptance is claimed for these three runs. Network04 PASSES native Playing
phase plus stable combat-ready authority Pawns, each local client's own input
readiness, 28 sequential BP/Python Jump trials, two distinct PlayerState owners,
actual authority GAS activation/ascent and idle foreign owner, three normal
process exits with server-last barrier, strict logs, independent report gate and
1,256 frozen hashes. Server scopes 14/14, A/B0 each 7/7; all active zero/errors
empty. Server executes fourteen Python activations; client native input-release,
state-end and active Profile teardown evidence remains independently checked.
WidgetLifecycle04 passed eight native UI/spec/CDO restoration cases and 1,252
hashes. This accepts only the Jump/shared-widget pilot, not all 37 static 0.11
candidates, packet-loss prediction, travel/rejoin, hardware input or packaging.
Continue the retained GA_QuickbarSlots decision/task orchestration next; native
GAS, QuickBar RPC/equipment/replication and existing animation remain unchanged.

**0.11 native ability UI lifecycle accepted; two-client Jump running (2026-10-16, 08:52 Singapore):**
WidgetLifecycle03 correctly restores native specs/UI but FAILS when the probe
reads the test ability after native ClearAbility already invalidated it. Record
type/Profile before removal rather than retaining a destroyed UObject. Keep the
failure. WidgetLifecycle04 PASSES eight real GAS GiveAbility/ClearAbility trials:
Jump one UI, invalid WidgetClass zero, shared empty array zero, shared two
same-tag classes two, each original/Python grant Profile. Every case switches to
the other Profile before native removal: actual production extension-point
entries remain unchanged at the switch, then restore EXACTLY on removal. Native
ability spec sets and temporary unsaved CDO defaults restore. Neither production
specs nor native UI pools are written by the probe. This is real native lifecycle
proof, not handle IsValid or callback replay. Network01 now runs one server and
two real owners, 28 sequential native input/GAS/CharacterMovement trials, with
independent authority activation/ascent and idle-other-owner checks plus a
server-last process-exit barrier. Host models pass 655. No network result or
whole-version acceptance is claimed until reports/logs/hashes finish.

**0.11 Jump native movement differential accepted; UI lifecycle baseline repair (2026-10-16, 08:47 Singapore):**
Differential01 completes all seven native BP/Python movement pairs but FAILS
its final gate: the first loading frame produced only one input injection,
not the two actually required to claim a held input. Keep the failure. The
fixture now waits for real repeated injections instead of assuming frame rate.
Differential02 PASSES all seven pairs, independent report validation, strict
normal-exit/log checks and 1,248 frozen source/binary/asset hashes. Native apex
parity stays within the explicit 2 cm sampling tolerance. Python scopes 7/7,
active zero/errors empty; native state-end delegate one, native input-release
four, native end adapter six (active Profile teardown deliberately suppresses
the busy router and closes its own scope). No direct Jump/ability activation,
callback replay, velocity/gravity write or fabricated grant is used.
WidgetLifecycle01/02 FAIL their exact spec-restoration gate; the recorded native
UI pool IS restored, and the only extra specs are the ORIGINAL asynchronously
granted pistol fire/reload/auto-reload abilities, not the test-granted Jump.
WidgetLifecycle03 now waits for that actual native equipment grant plus a stable
baseline before any fixture grant. No assertions were waived. Host models pass
648. UI lifecycle and one-server/two-client Jump acceptance remain open; no
whole-version acceptance, build, cook or publication is claimed.

**0.11 Jump native click smoke passes; differential running (2026-10-16, 08:37 Singapore):**
ClickSmoke01 PASSES the existing four CommonUI/native EnhancedInput/GAS Jump
trials against the new Python ability default, real ascent and normal shutdown.
It does not yet assert Jump's own task counters or BP-ability fallback parity.
Independent Differential01 now runs seven original/Python pairs: short/held
release, native cancel/end, active Profile switch, native EndAbilityState and
repeat release. It uses the production native-granted per-actor ability and
injects only native EnhancedInput action values; no direct Jump/activation,
task callback replay, velocity/gravity write or fabricated grant. Frozen inputs
include all Overlay/staged assets, core/bridge sources and binaries. Host tests
pass 642, including seven fail-closed report models. These models are not native
runtime proof. UI grant/remove and two-client Jump acceptance remain open.

**0.11 Jump/shared ability UI pilot authored, runtime pending (2026-10-16, 08:34 Singapore):**
The continuing migration now includes Python profiles for GA_Hero_Jump and
GA_AbilityWithWidget's native UI-extension registration/removal. Assets01 in
20261016-jump passes staged Interface/CDO configuration, Blueprint compilation,
four output asset copies, unchanged original business-graph/signature/default
checks and official-reference hashes. Only disposable stage/Overlay assets
changed; no C++ build or cook/package was run for this pilot. Host models now
pass 635 tests, including six task-order, cancellation and ownership models.
These are NOT runtime acceptance. ClickSmoke01 is running the existing real
CommonUI -> EnhancedInput -> GAS -> native Jump chain against the newly staged
Python ability. Ability tasks/movement and UIExtension native code are retained;
UI handles belong to the granted ability and are deliberately preserved across
Profile changes until native OnAbilityRemoved. Hold/release, cancellation,
original-BP parity, active Profile teardown and two-client acceptance remain
open. Neither 0.10 nor 0.11 is a completed/published release.

**Original two-owner interaction producer accepted (2026-10-16, 08:21 Singapore):**
InteractionProducer04 PASSES genuine Chair/native scan -> TriggerInteraction
-> GAS -> original Sit BP duration publisher for BOTH real owners, test-owned
same-class Python/original BP UI pairs, visible half-second exact models,
automatic native ticks/completion and owner isolation. Both original interactor
grants remain, and each owner has two original Sit instances; no deduplication.
Server-last barrier passes, all three processes exit normally, STRICT logs and
1,079 frozen hashes pass. Independent report gate and seventeen unchanged
original ability/Chair/Rock/UI/VM-transport asset hashes pass. A/B0 progress
scopes each 3/3, final active zero/errors empty; server 0/0. Native positions,
movement and aim fixtures restore. external-gate.json records separately run
report/asset checks; the original driver summary is not retroactively rewritten.
This closes the bounded ORIGINAL native producer gap, not physical input,
EnhancedInput, production Explorer widget placement, gameplay-message-bus
replication or whole-version/package acceptance. Original Sit/Collect/Interactor
BP policies themselves remain future 0.14 work, not silently counted as Python.
Add rejection tests for missing native source, fake broadcasts, deduplication,
UI mismatches/leaks, invalid owner IDs and host-first exit; then continue the
remaining authorized migration/acceptance work rather than release this pilot.

**Original Sit producer functional proof / exit-barrier repair pending (2026-10-16, 08:19 Singapore):**
InteractionProducer01 FAILS fixture readiness: Lyra's real nickname overrides
URL Name; associate clients with matching native PlayerState IDs instead.
InteractionProducer02 FAILS a fixture GetActorBounds call: positional bool was
incorrectly passed into native Origin out slot; omit the trailing optional
input so out vectors are allocated normally. Both failures are retained.
InteractionProducer03 records two genuine owner Sit activations, one native
duration each, two original Sit instances retained, exact native BP/Python
visible model parity, 32 automatic ticks each and completion/cleanup. Independent
functional report gate and 17 unchanged original/UI/transport asset hashes pass.
BUT OVERALL RUN FAILS strict logs: server quit races client release, producing
Host closed / ConnectionLost errors. Do not promote functional pass to acceptance.
InteractionProducer04 adds a proper server-last exit barrier: test driver
records both CLIENT PROCESSES exited zero before server exits. Same strict log
checks remain; no exception whitelist. This native run is pending, no new C++
build, package, original BP/replication setting change or handler replay.

**Original interaction world inspected / real producer trial (2026-10-16, 08:10 Singapore):**
InteractionDefaults01 PASSES unchanged official/stage CDO inspection of three
original abilities and Chair/Rock (832 hashes). InteractionWorld01 PASSES
actual L_InteractionTestMap startup: WorldSettings selects original
B_TestInventoryExperience, real B_Hero_Explorer/ASC and original GA_Interact
activate. InteractionWorldNetwork01 PASSES dedicated server + two clients,
three normal exits/logs and 1,077 frozen hashes. Original placed actors keep
bReplicates=false and are Role Authority on server / None on clients; actual
classes are correct despite some historical actor names still containing Rock.
Two original active GA_Interact specs EACH have InputTag.Ability.Interact;
preserve this upstream state rather than canceling one to manufacture a pass.
All these are READ-ONLY inspection, NOT producer/gameplay acceptance.
InteractionProducer01 now trials original native target scanning and ONE
selected real native TriggerInteraction/GAS/Sit ability per owner. Position,
movement/aim and two extra UI panels are explicit test fixtures; original map,
actors, ability classes, replication settings and duplicate grants stay intact.
The same genuine original-BP duration publisher must reach Python and retained
BP UI, auto-countdown and close scopes. No synthetic broadcast/handler replay;
no hardware/EnhancedInput or replicated-message-bus claim. 622 host tests pass;
this three-process native producer trial is PENDING. No new compile or package.

**Public BP ingress native acceptance / next producer inventory (2026-10-16, 07:56 Singapore):**
CombinedNetwork05 PASSES all nineteen original weapon/HUD/nameplate stages,
four normal exits, strict protocol/log/scope gates, 548 input hashes and 410
native source pairs. Added Health/Pawn ingress gate PASSES on A: Health Changed
8 and OnPosessedPawnChanged 11 actual reflected Python entries. EventOnEliminated
is correctly zero in this network run; its actual native animation completion
was independently counted once in HealthbarPublicEntries02. Never combine these
into a false claim that real GAS death reached elimination in this network run.
The three original public methods now route Python without changing assets,
types or the plugin DLL. Existing fallback BP remains available per instance.
InteractionDefaults01 now reads FIVE unchanged original ability/Chair/Rock
CDOs to plan a real producer trial; no compile, save or second concurrent native
lane. Still 0.10.0 development, no commit/push/tag/release. Later original world
placements, native interaction producer and remaining authorized BP batches
continue after this bounded gate.

**Native elimination ingress counted / real Health-Pawn network pending (2026-10-16, 07:54 Singapore):**
HealthbarPublicEntries02 PASSES the tightened eight-frame REAL UMG run:
native animation completion traverses EventOnEliminated exactly once; strict
normal exit and existing visual/cleanup contracts pass. Health Changed and
OnPosessedPawnChanged are correctly zero in this deterministic Python-health
fixture; it is NOT GAS/Pawn delegate proof. Host counter tests pass 621.
CombinedNetwork05 now runs all nineteen weapon/HUD/nameplate gates plus an
explicit nonzero A native Health/Pawn PUBLIC reflected-entry counter gate.
No diagnostic original-call wrapper, new build or asset edit is used. Source,
scripts/assets/tests/driver remain frozen during this native run.
Prepare a read-only five-original-CDO interaction inventory (three abilities,
Chair/Rock) for the next serial lane. Their producer/real-world activation is
still untested; this upcoming inventory is not runtime acceptance.

**Original healthbar public BP ingress closed / native counters pending (2026-10-16, 07:50 Singapore):**
Original/staged graph review distinguishes 108 direct routed entries, thirty
dispatch-forwarder entries, ten disconnected entries, ten parent-forwarders,
and three review exceptions. One exception exposed a real public-call gap:
Healthbar production subscriptions were Python-owned, but an external BP could
still explicitly call Health Changed/OnPosessedPawnChanged/EventOnEliminated
and reach retained BP business. Add all three original-name Python routes;
production Health/Pawn callbacks now invoke their reflected ingress, and native
animation completion invokes the public elimination route. No asset edit/build.
Host tests pass 621. HealthbarPublicEntries01 PASSES precompiled generic BP
callsite, deterministic REAL UMG eight-frame rendering and separate mid-animation
Profile-switch processes. This is NOT native GAS Health input evidence.
Add metadata-only public-entry counters; HealthbarPublicEntries02 reruns native
animation ingress with a required nonzero elimination count. CombinedNetwork05
will require actual native Health/Pawn reflected counts on A, as well as all
unchanged 19-phase gates. These later runs are pending, not yet accepted.
Two explicit retained thin bridges remain: spawner NetMulticast failure FText
VM transport and heal End Heal -> native K2_EndAbility. Neither is represented
as Python policy or whole-version completion. Source, scripts and assets freeze
during each native lane; remaining gameplay batches continue afterwards.

**Current-DLL core gates accepted / entrypoint review (2026-10-16, 07:36 Singapore):**
CallMatrix01 PASSES all eleven lanes, including precompiled BP callers,
missing-method original fallback, named outputs/rejections, inherited selector,
parent construction forwarding, soft class paths and Python exception recovery;
843 input hashes pass. Lifecycle01 PASSES three PIE cycles in one Editor:
placed/spawned construction, paired Begin/End, scope closure, GC and router
restoration; 417 source and five binary hashes pass. PackageLoad01 PASSES both
author/load processes and automatic discovery (843 hashes); Transport01 PASSES
typed VM transport (1,075 hashes). These gates reuse DLL 3FF11B4D...622526,
with no further compile, cook or package. SharedModule reuse is native-verified.
Coverage04 refreshes original-class/property/default-profile registration on
this DLL. A separate original-graph ENTRYPOINT review now checks actual wired
events/functions against the default profile, not just the registered union.
Any original delegate-forwarder exclusion must be justified, never silently
called whole-game migration. Remaining runtime producers/placements and later
versions continue after the current small review; 0.10.0 remains development.

**Standard combined network accepted / current-DLL core gates (2026-10-16, 07:30 Singapore):**
CombinedNetwork04 PASSES every original 19-phase gate: real owner fire/reload,
switch, respawn, two travels, exit_b, A solo fire, B1 rejoin/fire, final barrier.
Four processes exit normally; strict logs, external protocol, 548 input hashes
and 410 core/bridge source pairs pass. Diagnostic wrapper is FALSE and lane is
acceptance-eligible. Final source/manager/widget active counts are zero on all
four peers; A source scopes 32/32/widget scopes 100/100, B0 27/27 and 88/88,
B1 5/5 and 20/20. Sparse-map correction resolves the repeated exit_b read
divergence without pruning maps or changing original BP bodies.
SharedModule01 reuses EXACT new DLL/PDB in matching generic UE58Host (all
BuildIds match), with two changed implementation sources mirrored and previous
binaries/sources recoverable. No metadata rewrite or additional compilation.
CallMatrix01 now validates precompiled BP/native/Python dispatch and fallback;
native lifecycle and package-discovery gates follow serially. Still 0.10.0 dev:
native interaction producer, other production placements/hardware/package gates
and later authorized BP batches are NOT certified by this combined pass.

**Sparse TMap green / standard combined retry (2026-10-16, 07:24 Singapore):**
PluginBuild02 PASSES exactly three UEP-only actions (UEPyModule.cpp/lib/DLL),
107.70s, NoEngineChanges; BuildId remains 2f7b5df8-1c9a-4414-a598-6d3b022aa38d.
New stage UEP DLL SHA256 3FF11B4DF909ED763D294A3B08A4E63DA1881BD01FA883C91E91300660622526.
SparseMapGreen01 PASSES all SIX native dense/first/middle/last/multiple-hole/
empty cases. Independently exported native map contents match expected keys;
Python reads now match all keys and descriptor values. Strict normal commandlet
exit/log gate and 824 frozen input hashes pass; host tests 619 pass separately.
CombinedNetwork04 now runs the STANDARD 19-phase/two-travel/exit/rejoin suite
on this DLL, WITHOUT OriginalRemoveDiagnostic. All source/scripts/assets/tests
and lane driver are frozen again. Native call-matrix/lifecycle follow afterwards.
This does not certify the combined lane or complete 0.10.0 before its result.

**Sparse TMap read defect reproduced / bounded module build (2026-10-16, 07:21 Singapore):**
SparseMapRed01 runs unchanged original BP Map_Remove in a transient manager:
native T3D export retains five entries after first/middle removal but UEP reads
only four; multiple holes retain three but UEP reads one. Dense, last removal
and empty maps read correctly. UEP iterates Num() rather than GetMaxIndex() on
sparse native Map slots. This is a core CONVERSION defect, not proof that BP
deleted an extra actor. Correct the read loop only and rebuild UEP module with
NoEngineChanges (three planned actions), preserving previous binaries.
OriginalRemoveDiagnostic01 captured correct original-call arguments and the
read mismatch, then its identified server was intentionally stopped; it is
aborted/failed diagnostic evidence, not acceptance. Correction to earlier
wording: Pawn 6 in CombinedNetwork03 was a bot (PlayerId 0), NOT A's Pawn 5.
After the build rerun six native sparse cases with independent native export,
then the STANDARD 19-phase lane without the diagnostic wrapper.

**Disconnect third failure / original-call diagnostic pending (2026-10-16, 07:15 Singapore):**
NameplateRuntimeWrites01 PASSES all fourteen native widget comparisons,
strict logs/normal exit/external gate and 1,075 frozen hashes; host tests pass
617. CombinedNetwork03 nevertheless FAILS exit_b again: Python removes remote
Pawn 8 while original BP also loses own Pawn 6. Neither the live-map reread nor
the widget runtime writes is certified as this disconnect cause.
OriginalRemoveDiagnostic01 reruns the same 19-phase lane with an OPT-IN
test-only Profile wrapping original UnregisterNameplateSource to record its
argument and map before/after while executing the unchanged preserved BP body.
This deliberately distinguishes automatic missing-method fallback from explicit
original invocation; it is diagnostic, not normal-lane acceptance. Keep all
three failed runs. Frozen Source/scripts/assets/tests/driver; reuse the matching
DLL, no additional build, original asset edit, map pruning or gate waiver.

**Disconnect mismatch persists / runtime nameplate writes corrected (2026-10-16, 07:03 Singapore):**
CombinedNetwork02 FAILS again at exit_b. The bounded remove trace shows no
nested map mutation during the final native unregister, so the independently
proved live-map repair is NOT certified as the disconnect cause. Original BP
Remove listener/function graph wiring is correct. Keep both failed runs.
A further concrete runtime risk remains in W_Nameplate: Pawn/Indicator/
NameText/TeamId dot assignments still call Editor property notifications.
Replace these with existing set_property, as already required for components
and action-touch. No arbitrary entry cleanup or comparison waiver. Add a
static write guard and rerun the fourteen native widget comparisons before
the next full network retry. Matching new DLL is reused; no new C++ build.

**Reentrant Map component regression accepted / full retry (2026-10-16, 06:54 Singapore):**
NameplateReentrantRegression01 PASSES all eleven native component BP/Python
cases with the live-map reread, strict logs, normal exit, zero final active
sources/managers and 1,088 unchanged frozen hashes. Host green02 passes 616;
the red 615-test report preserves the nested-removal failure on old code.
This fixture does NOT by itself certify the exact network disconnect cause.
CombinedNetwork02 now reruns every original 19-phase/two-travel/rejoin gate,
with bounded metadata-only remove traces available on any discovery mismatch.
No baseline replay, arbitrary map pruning, new C++ build or package is used.

**Combined regression failure / reentrant Map repair under test (2026-10-16, 06:52 Singapore):**
CombinedNetwork01 FAILS at exit_b after both travels: B0 exits cleanly but A's
Python manager retains its own Pawn 5 while original BP has removed it (both
remove disconnected Pawn 8). Readiness correctly stays false and the native
140s phase deadline fails. This is NOT whole-suite acceptance. Native producer,
heal and declaration results above remain bounded prior evidence.
Code/graph comparison finds a definite reentrancy mismatch: original BP's
Sequence does Map_Find -> native UnregisterIndicator -> LIVE Map_Remove;
Python rewrote the pre-native dict snapshot, restoring any nested removal or
discarding a nested registration. A modeled nested-removal test FAILS on the
old code, then passes after rereading IndicatorMap AFTER the native call.
Add nested-registration coverage and bounded metadata-only remove traces for
the next native run; do not erase unrelated entries or weaken parity gates.
The real disconnect cause is not yet certified by the modeled reproduction.
Next rerun native component BP comparison and the full two-travel/rejoin lane
on unchanged matching binaries; no new C++ build/package.

**Declared coverage / combined new-DLL regression (2026-10-16, 06:35 Singapore):**
Coverage03 PASSES read-only native inspection of all 37 historical 0.9/0.10
candidates: 29 direct and six inherited routers default to Python; two touch
regions are explicitly retained empty/parent-forwarder shells. No unrouted
business candidate or missing default-profile method from the REGISTERED
function union is found. Strict commandlet exit and 860 frozen hashes pass.
This is declaration/registration coverage, NOT proof that every original BP
method/business path or placement has been exercised. Coverage01/02 remain
failed root-parent walker attempts; explicitly stop at native UObject because
the existing null-parent wrapper raises. No additional plugin build was needed.
CombinedNetwork01 now runs the full 19-phase original-BP/Python weapon/HUD
suite, two travels and rejoin, using new UEP DLL 4B5FE65E...418C2BD and the
accepted component/typed-transport provenance. Source/scripts/assets/tests and
lane driver are frozen. No Engine rebuild or cook/package. This regression is
pending and must finish all phases plus final external/log/hash checks.

**Real native foreign Controller proof accepted (2026-10-16, 06:30 Singapore):**
FailureNative03 PASSES all five checkpoints. The actual native second
LocalPlayer/Controller has a different PlayerState ID, its real starting Pistol
AbilitySet/source and its own production Python failure HUD. Native ASC rejects
its full-magazine reload and publishes once to its UI; first-owner Python
records one foreign payload, zero accepted messages, and both first-owner
Python/original BP states remain unchanged. Native RemovePlayer restores local
player count; second inventory/Health are unchanged. Legacy FCharacterEvent
user zero and optional user one are verified in runtime; a synthetic unhandled
control-character event supplies Slate registration, not hardware input.
Native pending cleanup now tolerates the old proxy's legitimate GC only after
its cancellation was captured. Final scopes balance 3/3, active/errors zero,
strict logs/normal exit/external gate/1,102 frozen hashes pass. Secondary-player
native screenshot was inspected: only the second pane shows the failure text.
Host-tests03 passes 614. FailureNative02 remains failed (ensure + stale proxy).
Next audit actual declared/inherited routers for all 37 0.9/0.10 candidates,
then combined weapon/HUD/lifecycle/two-client regression on the new plugin DLL.
Native dead-health failure, network GAS failure producer, physical input,
FiringRange placement and whole-version/package gates remain explicitly open.

**Real-owner fixture repair / bounded plugin build (2026-10-16, 06:28 Singapore):**
FailureNative02 FAILS overall despite correct native second-LocalPlayer
filtering records: CommonUI ensures SlateUser at secondary-player creation
because no hardware event registered user 1, and the later cleanup check calls
an already-collected, successfully-cancelled original proxy. Retain this failure.
The existing FCharacterEvent constructor hardcoded user zero. Add an optional
fourth positional user index, preserving legacy zero, and bootstrap user 1 via
an unhandled synthetic native control-character event BEFORE native CreatePlayer.
This is explicit input-environment setup, NOT hardware/gameplay-input proof.
Capture cancellation at Profile replacement, then accept either still-inactive
or natively-collected proxy at the later check. Never suppress the ensure.
PluginBuild01 PASSES exactly THREE actions (one UEP cpp compile, lib and DLL
links, 26.61s), with -Module=UnrealEnginePython -NoEngineChanges. No Engine
source edit/full build/cook/package; Engine/project/UEP/bridge BuildIds remain
2f7b5df8-1c9a-4414-a598-6d3b022aa38d. New UEP DLL SHA is
4B5FE65E5062E377FBEB6369FCE3995D5F8CB00A90DAFBFD0BDC5A360418C2BD;
old binaries are recoverable under PluginBuild01/PreviousBinaries. Build alone
is not acceptance. FailureNative03 now must verify legacy/default and user-1
events, native second-player filtering, removal and strict logs/final cleanup.

**Native GAS failure producer accepted / real-owner extension (2026-10-16, 06:19 Singapore):**
FailureNative01 PASSES four real original-Pistol full-magazine native ASC
rejection BP/Python checkpoints. Exact native MagazineFull tag, real payload
owner and opaque native FText compare pass; repeat delivers once without new
intro, native latent/Outro collapses at 1.516s and active Profile cleanup stops
pending work. Original inventory identities/ammo/Health stay unchanged. Final
failure scopes balance 2/2 with zero active/errors. Strict logs, normal exit,
external proof gate and 1,102 frozen hashes pass; screenshot visually inspected.
This closes the bounded native GAS producer gap, not real foreign ownership.
FailureNative02 adds a native second LocalPlayer/Controller/starting equipment
and production UI, requests that owner's actual full-magazine rejection, checks
first-owner Python AND original BP ignore it, then removes the temporary native
LocalPlayer. No fake Controller payload is certified as real ownership. Native
second-player/cleanup gates are pending; hardware/network failure/dead-health
and entire 0.10/package acceptance remain open.

**Native GAS failure producer selected (2026-10-16, 06:16 Singapore):**
Native-producers Audit03 PASSES eight unchanged-original ability CDO/cost/
failure-map inspections, strict commandlet exit and 838 frozen reference/input
hashes. Audit02's data passes but its external driver initially applied runtime
atexit marker ordering to a commandlet; that failed driver result is retained.
The corrected driver requires commandlet success -> Goodbye Python -> closed
log, still rejecting all error/fatal/ensure lines. Dash/Grenade have no authored
simple failure text map; do not demand a toast on repeat Dash rejection.
The original fully loaded Pistol reload DOES map MagazineFull to native FText
"Already Full of Ammo". FailureNative01 now tests this actual equipment-granted
ASC rejection -> native GAS publisher -> production Python and original BP
same-class comparator, repeat deduplication, native latent/animation completion
and Profile pending-work cleanup. No synthetic message, failure handler replay,
ammo/Health write or cost/CDO edit. Host-tests01 PASSES 613; native run is pending.
Current project/plugin/bridge DLL BuildIds must match UE5.8.1; prior Blueprint
authoring provenance is recorded separately, never patched as a fake DLL match.

**Native producer audit transport correction (2026-10-16, 06:12 Singapore):**
Native-producers Audit01 FAILS read-only CDO inspection because the current
UEP struct wrapper is unhashable and cannot serve as a Python dict key for
TMap<GameplayTag,FText>. No asset edit or runtime producer claim. Audit02 uses
the existing native ObjectExporterT3D CDO text export for failure maps, retaining
ordinary reflected reads for scalar/array cost defaults. Do not change/build
the plugin/Engine merely to inspect that map. Original eight ability byte
hashes must still match official Lyra and remain unchanged.

**Heal two-client native GAS acceptance (2026-10-16, 06:10 Singapore):**
Network03 PASSES all twelve BP/Python trials (A/B0 x natural Montage/native
cancel/native timer). Real original inventory/equipment AbilitySets grant the
RangedWeapon source; each owning client requests native ASC activation through
the original LocalPredicted GAS path. Server and owner observe native active/
ended state, 75->100 Health, exactly one committed item use 1->0, unchanged
other-owner inventory/Health and actual HUD numbers/materials. Owning clients
play native Montages; each Python timer case fires its native 1s timer once.
Server timers may instead close on the owning client's native end RPC; this
preserves GAS prediction rather than requiring both roles to produce an end.
Native item identities, slots, Health, movement and aim restore. Final Python
scope/timer counts balance server 6/6, A 3/3, B0 3/3, active/errors zero. All
three processes exit normally; strict logs/external protocol/1,075 frozen
hashes pass. Host-tests09 passes 607. Network01 startup-clock and Network02
incorrect zero-cost assumption remain failed history. Native refusal branches,
FiringRange placement, adverse networking, hardware input, package and entire
0.10 release remain open. Next close producer/coverage gaps, not release yet.

**Heal network native item cost correction (2026-10-16, 06:07 Singapore):**
Network02 reaches case 0 original-BP native GAS activation and replicated
75->100 Health, but FAILS the client inventory gate: the original heal item
commits one MagazineAmmo use (1->0), whereas the initial gate expected no stat
change. Retain the original native cost. Require exactly that one-use delta,
all other inventory/equipment fields unchanged, other-owner isolation and full
native identity rollback; BP/Python must match on both server and owner. No
network pair is yet accepted. Also reuse the existing fail-closed transient
status readiness gate rather than dereferencing an absent atomic-file sample.

**Heal network first-run fixture failure (2026-10-16, 06:05 Singapore):**
Network01 FAILS before case 0 activation: the new fixture mistakenly charges
native startup/Warmup against the first case timeout. No network treatment
pair is accepted. Reset the per-case wall clock after native ready/baseline
capture; do not shorten Warmup, force readiness or weaken native GAS gates.
Host tests still pass 606. Retry Network02 after the first owned lane has
fully exited; scripts/assets remain frozen during each native lane.

**Heal ability lifecycle differential accepted (2026-10-16, 05:59 Singapore):**
Differential05 PASSES seven native BP/Python pairs, strict logs, normal exit
and the external report contract; all 1,083 frozen input/reference hashes
remain unchanged. Each ordinary Python trial records exactly one native end
notification, including an external native EndAbility while the Montage is
still playing. Active Profile switching separately exercises the intentional
teardown notification guard: no reentrant dispatch, scopes/timers close and
native GAS cancels. All fourteen inventory/Health trials restore original
identities and state. This closes the missing end-entry proof, NOT networking,
native cost/commit-refusal, FiringRange placement or full 0.10/package acceptance.
Next: two real owning clients activate the original equipment-granted ability
through native ASC prediction/RPC, compare BP/Python and owner isolation, then
verify native end and inventory/Health/lifetime rollback. No C++ build/cook.

**Heal ability end-entry proof strengthened (2026-10-16, 05:56 Singapore):**
Differential04 passes six behavior pairs and strict logs (1,083 frozen hashes),
but its native-end counter is zero: it does NOT prove the new lifecycle
notification entry. Investigation finds the generic graph event constructor
does not itself mark an override. Assets03 explicitly sets the node's existing
bOverrideFunction property, then requires compiled K2_OnEndAbility ownership
on GA_HealPickup_C; no plugin/Engine source edit. The report contract now
requires exactly one native-end cleanup on each ordinary trial, and adds an
external native EndAbility case (no montage callback replay). Differential05
is running all seven pairs with the stronger contract; do not promote the
older six-row report into full lifecycle acceptance. Host-tests06 PASSES 600.
The original End Heal single native-call forwarder stays unmixed, and the
four-node normal-end/teardown guard remains transport only. Cost/commit refusal,
networking, FiringRange placement, full 0.10/package gates remain open.

**Heal ability bounded proof / active-switch repair (2026-10-16, 05:47 Singapore):**
Differential02 PASSES five real native inventory/equipment/ASC BP/Python pairs:
75->100 heal, natural Montage completion (~.77s), native ability cancellation
and Montage interruption, native 1s timer (1.001564/1.004123s) with the authored
bStopWhenAbilityEnds=false (long Montage remains playing), and world-time pause.
Five Python scopes/timers close, native item identities/slot/Health restore,
strict logs/normal exit/external gate pass. Differential01 failed the existing
UEP timer wrapper's GameplayAbility World lookup; use native Avatar actor for
the same TimerManager, with explicit ability-end cleanup (no C++ change).
Differential03 adds active Profile switching and behavior rows match, but the
STRICT LOG GATE FAILS two router-unavailable callbacks during teardown. This
is NOT accepted. Assets02 adds four native end-notification guard nodes plus
a signature-only helper; the original one-call End Heal remains an UNMIXED
native end-signal forwarder. During teardown Python first disarms callbacks/
timer and sets an example-owned guard, native GAS cancels, and no notification
reenters the unavailable router. Native GAS cancellation and core reentry
protection remain intact. Original graph digest/type/defaults still pass;
old staged assets are recoverable in RetainedAssets01. Host-tests05 PASSES
599. Differential04 now reruns all six pairs with the strict log gate; active
switch acceptance, native cost/commit-refusal coverage, multiplayer, original
FiringRange placement and package remain open. No Engine/plugin C++ edits/builds.

**Old heal ability 2S is required / native run started (2026-10-16, 05:40 Singapore):**
UnusedHealAudit01 forces synchronous native Asset Registry scan, all dependency
categories, and finds GA_HealPickup -> AbilitySet_HealPickup -> WID_HealPickup
-> ID_HealPickup -> an L_FiringRange_WP external actor. It is NOT excluded for
its Unused folder name. Heal-ability Audit01 reads original Montage/effect,
InstancedPerActor/LocalPredicted policies and native task signatures. Assets01
PASSES unchanged ability class, one original graph digest, references/policies
and direct Mixin Set; only the original native task proxy is exposed for proof.
Python keeps cost/commit -> native Montage task activation -> immediate GE ->
native 1s TimerManager ordering, completion/interruption/cancellation and owned
task/timer cleanup. Host-tests02 PASSES 598, NOT native GAS acceptance.
Differential01 is executing five planned BP/Python pairs. Fixture preflights
the native RangedWeapon source requirement before activation, then uses the
original inventory/equipment/AbilitySet grant instead of an invalid source-less
direct grant (the native superclass CHECKS WeaponData). No direct Activate/
task callback replay, Health property write, animation asset edit, C++ build or
cook/package is authorized/used by this lane. Active Profile switching, cost/
commit rejection and networking remain named future gates, not certified here.

**Action touch two-client acceptance (2026-10-16, 05:28 Singapore):**
Network02 PASSES eight native A/B phases: mounted pairs, each actual replicated
target Pawn, foreign rejection, native unmount/no late delivery, reconstruct,
Profile roundtrip and own-root/scope cleanup. Each client preserves its two
legitimate production Dash/Grenade listeners before readiness; after native
World/UI teardown, both final snapshots show eight scopes created/eight closed,
zero active/errors. All three peers exit normally; strict logs, external proof
gate and 1,068 frozen input/reference hashes pass. Producers are explicitly
client-local synthetic typed messages, NOT replicated GameplayMessage traffic
or a native duration ability producer. Physical hardware/prediction/package
remain unverified. Host-tests08 PASSES 586. The unreferenced heal-ability
native registry audit is now the sole active Editor lane; no new C++ build.

**Action touch two-owner cleanup correction (2026-10-16, 05:28 Singapore):**
Network01 passes baseline, A/B owner, actual replicated foreign Pawn rejection,
unmounted no-delivery, native reconstruct and Profile-roundtrip phases, then
FAILS cleanup because its global scope gate includes two legitimate live
production ActionTouchButtons (Dash and Grenade). Own test paths/roots have
already closed; do NOT cancel unrelated production listeners to turn it green.
Network02 now compares owned scope deltas against the production baseline,
requires unchanged production active paths at test cleanup, and extends the
existing Python-exit snapshot gate to require ALL ActionTouch scopes including
production to close after native World/UI teardown. Host-tests08 PASSES 586,
including rejecting cleanup that destroys those unrelated listeners. Network02
is loading both native clients; no final two-owner acceptance yet. The old
heal-ability dependency audit is prepared but not run concurrently with this
lane; it will force synchronous asset-registry discovery and examine every
dependency category instead of excluding it merely for its Unused folder name.

**Action touch native click/input proof (2026-10-16, 05:21 Singapore):**
Click01 PASSES four base/MobileOnly x original-BP/Python trials. One synthetic
activation of the existing native CommonUI HandleButtonClicked entry injects
the authored IA_Jump value through the BP/Python button logic; the existing
native Enhanced Input/GAS Jump path emits exactly one native OnJumped event
for the actual owner and produces observed >20cm rise, positive vertical
velocity and Falling mode. Python click counters are one only on Python lanes.
The fixture never calls BP click directly, injects input directly, calls Jump/
Launch, grants abilities or writes velocity/gravity. It lets native release/
gravity land before the next trial. Four widget roots release, original native
OnJumped UFunction restores, player location/Health restore, strict logs,
external report and normal shutdown pass. This is synthetic CommonUI input
acceptance, NOT physical touchscreen or multiplayer input/prediction proof.
Next: two real owners with explicit client-local typed message provenance,
actual replicated foreign Pawn identity and widget teardown/reconstruct/Profile
cleanup. GameplayMessageSubsystem itself does not replicate those messages;
do not mislabel fixture orchestration as gameplay message network transport.

**Action touch bounded native acceptance (2026-10-16, 05:17 Singapore):**
Differential05 PASSES 30 base/MobileOnly mounted UMG BP/Python checkpoints,
native CommonUI enabled/selected transitions, style/padding/materials, typed
owner/foreign messages, restart/pause, base automatic completion, native remove/
reconstruct and Profile roundtrip. Four roots release, eight scopes close,
strict logs, normal exit, external gate and 1,078 input/reference hashes pass.
Both PNGs were visually inspected; the matched grenade-icon overlays are
visible, with pre-existing Steam/TEDS diagnostic banners. WeaponHUDRegression01
PASSES all 42 older weapon presentation cases; not GAS/fire input acceptance.
Differential02 locates the first material mismatch: reflected attribute writes
emit Editor property notifications and rerun PreConstruct even in this Editor
game. Production Duration/StartTime/Charging now use existing set_property,
without Engine/plugin C++ edits. Runtime AST guard prevents new notified writes.
Differential03/04 fail expecting MobileOnly completion: live CDО script-Tick
flag is false. Audit03 restores ONLY staged original files after verified
Assets01 backups and proves the OFFICIAL original flag is also false (Auto
frequency, base true/child false). Assets02 proves identical scheduling; no
forced native flag or hand-invoked Tick is used. Mobile acceptance explicitly
tests original-child-no-tick, not a fabricated completed cooldown. Old staged
assets/Set remain recoverable in RetainedAssets01; canonical Overlay preserved
until the successful generation replaces it. Host-tests05 PASSES 573.
Remaining: actual click/input effect and dual-owner message/lifetime isolation,
physical touch hardware, production placement and package. Next read-only
audit checks whether left/right touch regions have any BP business at all.

**Action touch 2R native differential in progress (2026-10-16, 05:05 Singapore):**
Audit02 PASSES semantic defaults (tags/margins/brushes, not transient pointer
strings), two native class/signature reads and the composite FireButton parent
check. Assets01 PASSES one parent Set inherited by MobileOnly, five original
graph digests and retained native typed message transport. This uses direct
UFunction Mixin replacement, not extra branch gates; original async factory
proxy is exposed only for owned cleanup, with a signature-only resume entry.
Host-tests02 PASSES 571. Differential01 passes seven mounted base-widget
checkpoints through style/primed material reset/CommonUI disabled/enabled/
selected/deselected, then FAILS owner-duration: native cooldown values match
but Python Animate_FromEmpty=0 vs BP=1 after the animation transition. This
failure is NOT accepted. Its cleanup also used a nonexistent API; corrected
to the existing clear_mixin_profile cache/teardown API, without plugin edits.
Differential02 now records both typed/legacy native IsAnimationPlaying,
animation time and pre/immediate-post broadcast material state to locate the
first divergence. No manual Widget Tick, input gameplay, touch hardware,
network/production-placement/package or full 0.10 acceptance is claimed.

**Teleporter real-owner two-client acceptance (2026-10-16, 04:56 Singapore):**
Network02 PASSES 12 launch/no-launch/relative-offset x A/B x original-BP/Python
cases. Actual server entry overlaps alone drive teleport/launch; both clients
ACK stable baselines, native owner exit/flight, unchanged other owner/Health/HUD
and per-trial restore. Original non-replication remains. Exact OnLaunched
request/override flags, native position/rotation/control and real server/client
motion pass. All 24 portals/12 scopes and the temporary native launch observer
close; player position/rotation/aim/movement/Health restore before readiness.
Three peers exit normally, strict logs and external protocol pass. Network01
FAILS its final gate after all 12 observations because it wrongly expects
constant 1,250 horizontal velocity on real Lyra Pawns. Both BP/Python naturally
brake (~935-1,021 at sampled frames). The gate now keeps exact native request
parity, requires actual forward flight/braking, and rejects sideways/reverse/
excess speed or missing motion; no production movement parameter changed.
Host-tests05 PASSES 559, including that negative coverage. No full 0.10,
original level portal placement, client portal Profile/audio/manual input,
grenade/multi-destination/invalid-config or package acceptance. Next 2R:
W_ActionTouchButton/MobileOnly, native audit first. Static audit confirms
W_FireButton is a UserWidget COMPOSITE, not an ActionTouchButton subclass;
do not remove its independent working router based on a false inheritance premise.

**Teleporter bounded native acceptance / two clients (2026-10-16, 04:53 Singapore):**
Audit02 and Assets01 PASS original B_Teleport data, five dispatch gates, five
original graph digests/macros, unchanged class/signatures/non-replication and
one Set. Differential04 PASSES seven BP/Python native physical-overlap pairs:
launch/no-launch, forced/free control direction, original world-space relative
offset and upper/lower clamp, and no controller. Native Niagara parameters,
teleport location/rotation, synchronous control rotation and actual resulting
CharacterMovement velocity match. All 54 actors/14 scopes close, strict logs,
normal exit, external proof gate and 1,059 input/reference hashes pass.
Differential01 FAILS a destroyed UObject-property read; Differential02 FAILS
sampling AI control after its later native orientation tick. Differential03
behavior reports match but STRICT LOG GATE FAILS: Python omitted the hidden
DefaultToSelf owner for K2_DestroyComponent. Production now passes the owner;
receiver proof queries current native components, not stale deferred SCS
handles. No failure is waived. Host-tests04 PASSES 558 including network
negative proof gates. Network01 now runs 12 launch/no-launch/relative-offset x
real owner A/B x BP/Python cases; no native network acceptance yet. Server
test portals retain original non-replication; client portal Profile/audio,
manual input, production placement, grenade/multiple-destination runtime,
invalid-config parity and package are NOT certified. No C++ build or cook.

**Spawner shared-lane regression / teleporter start (2026-10-16, 04:43 Singapore):**
InventoryRegression01 PASSES the original 16-case two-client inventory lane
after shared startup/import-guard changes; report gate, native per-owner fire,
equipment/ammo replication and normal peer shutdown pass. Teleporter Audit01
reads the original data successfully but its driver FAILS a PowerShell
single-item array Count check. Audit02 PASSES after retaining array shape;
no asset/runtime claim follows from that read-only result. Original B_Teleport
is not replicated; authority-only Character teleport, local control/audio
sequence, native movement and original world-space offset policy stay intact.
Five dispatch gates and a single Set are now being authored in the marked
stage; original graph/signature/replication proofs are required before runtime.
Host-tests01 PASSES 544 including ten teleporter policy tests. No C++ build,
official asset edit, cook/package or complete 0.10 acceptance.

**Spawner original-level two-client acceptance (2026-10-16, 04:31 Singapore):**
Network02 PASSES all 36 nine-scenario x A/B x original-BP/Python cases. It uses
the original level Rifle and small-heal actors/classes/serialized definitions,
not new derived classes or invalid dynamic actor configuration. Both clients
select the runtime Profile, then observe native inventory/equipment/ammo,
actual target fire, Health/material HUD, pickup/respawn mesh/light availability,
and exactly one target-owner Spare Ammo Full message (other owner zero).
All successes await natural 10s cooldown. Native player item identities,
Health/position/movement/aim and original actor flags/definitions/Profiles
restore; 36 collision scopes close, no level actor is destroyed. Three peers
exit normally, strict logs/protocol and 1,059 frozen input/reference hashes pass.
Network01 FAILS at case 6 after six passes: two owner messages. Native
ResetCoolDown also schedules CheckForExistingOverlaps after .25s; next-trial
entry was too early. Prepared-phase native settling prevents that previous
trial callback entering the next trial, WITHOUT changing production timer or
one-producer/one-message gates. Fallback/Python production counts now both
require one. Host-tests07 PASSES 534. No C++ build/cook/package. Not full
0.10 acceptance: PostGame/culture/all pickup definitions and exact constructor
Profile parity on clients remain open. InventoryRegression01 now rechecks the
old 16-case two-client inventory lane after shared entry-guard changes.

**Spawner real-owner/level-actor network started (2026-10-16, 04:19 Singapore):**
Host-tests06 PASSES 534, including 36-case network matrix and foreign-owner,
wrong ammo/HUD, short timer, repeated failure message, replaced level actor,
missing availability restore/fire/lifecycle and all three exclusive-import
guards. Network01 now runs nine scenarios x A/B x BP/Python. It borrows
unoccupied original Rifle/small-heal level actors, not invalid dynamically
spawned actors: WeaponDefinition is instance-only and is not network-replicated.
No new test-derived class, replication field, map save or actor destruction.
Both clients explicitly select the same runtime Profile (constructor parity
is separately covered by standalone), then ACK prepared/observed/restored
native inventory, equipment, ammo, Health/HUD, availability/mesh/light and
failure owner. Successful cases await each natural 10s cooldown; no timer
replay or Duration override. Server/client actor configuration/Profile and
native player inventory identity/Health/position/movement/aim must restore.
No native network acceptance yet; source inputs remain frozen during this run.

**Spawner bounded native acceptance (2026-10-16, 04:07 Singapore):**
Differential03 PASSES all nine real-Pawn original-BP/Python pairs: unowned
Rifle grant/equipment and real 30 -> 29 firing, full slots, duplicate refill
and native owner failure message, reload guarded/unguarded selection, another
same-definition instance, healing and full-health refusal. Four observed native
default cooldowns are 10.003540/10.001678s (weapon BP/Python) and
10.001120/10.004414s (heal BP/Python); no timer/Timeline/handler replay or
Duration override. Native respawn curves/light and material alpha match.
All 18 pads and collision scopes, message subscription/helper root, original
inventory identities/aim/movement/position/Health restore. Strict logs, normal
exit, external report gate and 1,068 frozen input/reference hashes pass.
Host-tests05 PASSES 528. This bounds standalone selected Rifle/small-heal
data, not multiplayer, PostGame-native branch, culture, all definitions,
placement or package. Next: two-client original level spawners; native
WeaponDefinition is instance-only, NOT replicated, so do not invent a network
field or spawn invalid unconfigured actors on clients.

**Spawner native material correction (2026-10-16, 04:04 Singapore):**
Differential02 reaches native Rifle grant/equipment, real one-shot magazine
30 -> 29, default 10s cooldown completion and native respawn curve on BOTH
BP/Python lanes, but comparison FAILS: BP material Color alpha=1 while Python
scaled alpha to .02. The original promoted node converts scalar .02 to a
color with RGB=.02/Alpha=1 and then multiplies colors. Python now uses that
same native color multiplication; no tolerance is relaxed. Host-tests05
PASSES 528, including arbitrary-alpha preservation. Differential03 reruns all
nine pairs; neither this partial gameplay success nor normal exit is acceptance.

**Spawner native baseline correction (2026-10-16, 04:02 Singapore):**
Differential01 FAILS on the original-BP first pickup, before any Python grant.
The fixture assumed Pistol was new, but native Lyra starts with a Pistol and
48 spare ammo (also recorded by Inventory Network03). Original spawner
correctly rejects an already-full duplicate. The fixture now records its
initial inventory and chooses an unowned original pickup definition (normally
Rifle) without changing the spawner's default duplicate-ammo rule. Native
failure snapshots include current inventory/messages/availability/Profile.
Host-tests04 PASSES 527, including the initial-Pistol negative. Differential02
reruns all nine pairs; no native runtime acceptance yet.

**Spawner 2P implementation / native run (2026-10-16, 03:58 Singapore):**
Audit01 PASSES two original BP CDO/signature/curve reads and five original
pickup data assets. Selected pistol/small-heal data have 10s cooldowns (big
heal=25s); retain those, not the 4s BP CDO default. Assets01 FAILS because
editor-internal message-node flags are not reflected. Assets02 PASSES eight
gates, six original graph digests, unchanged GiveWeapon/multicast signatures,
native Timeline samples and one inherited parent Set. The original failure
RPC's controller/typed-message/FText transport stays intact; decisions calling
it are Python. A four-node native reload-interface adapter preserves native
C++ interface dispatch. Host-tests03 PASSES 526, with incomplete/shortened
cooldown, fake fire, wrong grant/heal, cleanup/message-owner and import-guard
negatives. Differential01 now runs nine real-Pawn BP/Python pairs, native
inventory/GAS/tag fixtures, actual pistol fire, two full native 10s cooldowns
per profile and native respawn curves. No runtime/network acceptance yet.

**Launcher real-owner two-client acceptance (2026-10-16, 03:43 Singapore):**
Network05 PASSES all 12 Push-forward/Push-target/Up x A/B x BP/Python cases
on actual Lyra Pawns with original gravity, native collision and native
OnLaunched requests. Both owners ACK native initial position, actual target
movement/other-owner isolation, and per-case restore; final original Health,
position and movement mode restore. Native OnLaunched observation forwards
the original and restores the original UFunction before readiness. All 12 pads
and collision scopes close, three peers exit normally, strict logs/external
protocol pass and 1,037 frozen hashes remain unchanged. Host-tests10 PASSES 509.
Historical failures remain: Network01 sampled an unready Pawn; Network02's
final no-op teleport falsely failed a return-code check; Network03 redundantly
restored already-disconnected Pawns; Network04 rewrote immutable ready files
and raced an unshared reader. Restoration is now verified/idempotent and
readiness publishes once with shared reads. No handler/LaunchCharacter replay,
Health/velocity/gravity writes or forced launcher replication. Client pad
Profile/VFX parity, physical client input, placement and package remain open.
This does not close 0.10 or later versions. Next 2P: weapon/ability spawner BPs.

**Launcher real-owner network started (2026-10-16, 03:32 Singapore):**
Host-tests06 PASSES 506, including foreign owner/world, stationary fake target,
other-owner motion, repeated/mismatched native launch requests, forced actor
replication, missing lifecycle/restore, wrong owner HUD and NaN vectors. Both
base network imports are excluded from launcher startup so one ticker owns
the scenario. Network01 now runs 12 Push-forward/Push-target/Up x A/B x BP/Python
cases on actual Lyra player Pawns. It uses original gravity/velocity physics,
native OnLaunched observation with original-event forwarding, two-owner native
baseline/motion/restore ACKs, and mandatory observer/function restoration.
Server fixture spawn/teleport/collision arming is declared; no handler/launch
replay, velocity/gravity/Health write or forced pad replication. No network
acceptance yet. The earlier fixture differential froze 1,045 unchanged inputs.

**Launcher bounded native acceptance (2026-10-16, 03:26 Singapore):**
Assets03 PASSES seven gates on one parent Set, retaining all three classes,
RPC signature/flags, bReplicates=false and seven original graph digests (only
declared execution/return transport endpoints excluded). Differential01 FAILS
because native Flying fluid drag invalidates the fixture's constant baseline.
The fixture now uses owned, zero-gravity Falling Characters with native physics.
Differential02 finds the original Y Clamp literals both zero; Python now
preserves this authored asymmetry. Overlap's user-defined packed bool output
uses the existing typed output API. Differential03 completes all eight pairs
but FAILS cleanup acceptance because Cue construction rejects FVector for a
NetQuantize10 field; use native MakeGameplayCueParameters instead. Differential04
PASSES eight original-BP/Python pairs, 16 real collision begins, all 36 fixture
actors destroyed and 16 scopes closed, strict logs and frozen hashes. Native
physics, default light/material/radius/clamp, forward/target/up, falling and AI
filters match; policy errors are empty. Host-tests05 PASSES 500. No real player
movement was modified in that lane; real-owner two-client physics remains open.

**Launcher 2O preparation (2026-10-16, 03:18 Singapore):**
Audit02 PASSES a read-only native CDO/locals audit for B_Launcher, Push and
Up; all three retain bReplicates=false. Audit01's completed native read was
rejected by the new driver using runtime rather than commandlet exit ordering;
the corrected Audit02 preserves normal Python exit and unchanged hashes.
Host-tests01 PASSES 492. Assets01 FAILS: adding editable return nodes alters
the inherited Overlap signature. Assets02 FAILS before saving: SelectBool is
not a reflected function in this engine. Assets03 reuses the existing return
node and native boolean transport (original return only when dispatch=-1).
Python 0/1 returns do not fall through; zero-initialized exceptions do not run
old BP. This is authoring in progress, NOT native runtime/network acceptance.

**Shared Health presenter regressions (2026-10-16, 03:10 Singapore):**
HUDRegression01 PASSES the native callsite fixture, eight rendered Health
states with ordinary teardown, and the separate mid-animation Profile-switch
process. WeaponHUDRegression01 PASSES the original four-widget native suite.
Images include a correctly settled 60/100 Health bar; the retained Steam
deprecation banner is not a gameplay difference. The old weapon driver now
selects its exact original eight BP/Set inputs rather than rejecting later
batches' additional assets. No build/cook/package. Next 2O: the three launcher
BPs, preserving CharacterMovement, collision and existing multicast RPC.

**Grant-GE two-client acceptance (2026-10-16, 03:04 Singapore):**
Network04 PASSES all four BP/Python x A/B cases: native physical healing,
non-target owner isolation, inactive reentry rejection, actual default 15s
Timeline recovery, and both clients' replicated numeric/material Health HUDs.
Both players' original health/position/movement restore and all fixture scopes
close. All three peers exit normally; strict logs/protocol and 1,019 unchanged
input/reference hashes pass. No native source, animation asset or replication
flag was changed. This bounds 2N, not 0.10/full/package acceptance. The queued
spawn-animation flush fix additionally needs the existing native HUD/weapon
regressions, now running serially before the next launcher batch.

**Early damage / queued spawn animation fix (2026-10-16, 02:59 Singapore):**
Network03 confirms cached and actual brush MID are identical and both remain
Health_Updated=1 with native/model/numeric Health=75; all owned animations
eventually report stopped. HealthAnimationAudit01 reads the retained native
asset without changes: OnSpawned frame zero keys Health_Updated=1, while the
damage track does not author that parameter. Engine source confirms Stop
queues return-to-start evaluation; its public reflected FlushAnimations
drains queued work. Python health rendering now flushes after stopping owned
animations and BEFORE setting new health materials. Cleanup/router teardown
does not force a flush. No engine/animation asset edit. The fake presenter
models a delayed OnSpawned reset; two new ordering/teardown tests pass, total
Host-tests06=482. This is implementation/model proof only; Network04 and
subsequent existing native health/weapon regressions are required.

**Grant-GE replicated HUD discrepancy (2026-10-16, 02:46 Singapore):**
Network02 still FAILS at pickup-ack with the corrected full case deadline.
Native B0 Health=75, numeric text/target=75, but cached BarFillMID
Health_Updated=1.0 instead of 0.75. Health events show a real 100 -> 75 damage
transition, not a missing GAS update or zero/max-health initialization. Do
not relax the material gate or call this networking accepted. Network03 adds
read-only diagnostics for cached vs actual brush MID identity/ratio, authored
NormalizedHealth/old/new, presented state and native animation playback. No
production presenter fix is applied until those observations identify cause.

**Grant-GE network first diagnostic (2026-10-16, 02:41 Singapore):**
Network01 FAILS at 0/pickup-ack. Native server/target client A reach Health=100;
B0 reports Health=75 but its comparison visual is None, so no B0 ACK is
accepted. The first 120s case budget also incorrectly includes scene/client
startup. Reset the deadline at baseline/case start and record raw native HUD
text/target/material ratio for diagnosis; no numerical/owner/HUD gate is
relaxed. All owned peers have exited. Network02 must rerun all four cases.

**Grant-GE multiplayer in progress (2026-10-16, 02:38 Singapore):**
Host-tests03 PASSES 480 tests, including wrong-owner/inactive re-heal/short
cooldown/collision/UI failures and both network modules' mutually exclusive
startup guards. Network01 now runs four BP/Python x A/B cases. It requires
both replicated Health HUDs after pickup and after inactive reentry/default
15s cooldown, plus final health restoration acknowledged by both clients.
Native server spawn/teleports and bounded native GAS baselines are explicit
fixture setup; no handler/Tick/Timeline replay, attribute writes, forced pad
replication, client prediction or client pad Profile parity is claimed.

**Grant-GE bounded native acceptance (2026-10-16, 02:31 Singapore):**
Differential02 PASSES six same-class original-BP/Python comparisons: retained
construction/text/mesh/light, native 50 deg/s Tick, real Pawn overlap + instant
heal, real leave -> charge, native curve/material progress while Actor Tick
is paused, and native finish restoring visibility/light/text/rotation. No
Tick, collision handler or Timeline event is replayed. Actual native default
cooldowns are Python=15.004688s and BP=15.005099s; Duration is NOT overridden.
Two fixture actors and both collision subscriptions close; player health=100,
position error=0 and movement=[1,0] restore. Strict logs, normal exit and frozen
hash gates pass. Host-tests02 PASSES 476 tests. This is standalone instant-GE
proof, not multiplayer, culture switching, persistent GE, package or full
version acceptance. Next: four two-client BP/Python x A/B cases including
target healing/other-owner isolation, inactive reentry and default cooldown.

**Grant-GE preparation/first native failure (2026-10-16, 02:26 Singapore):**
2N Audit01 reads original client-visible replicated pad defaults: active=true,
15s cooldown, HELLO text, instant GE_InstantHeal_Big and native 1s linear
Timeline. Assets01 PASSES six virtual gate authoring, four-node native FText
transport, retained class/interface, unchanged two original graph digests and
curve samples. No runtime acceptance is implied. Host-tests01 PASSES 471.
Differential01 FAILS before pad creation: fixture asks native GAS bridge for
100 -> 55, exceeding its existing absolute-delta safety limit 25. The bridge
is NOT changed; use baseline 75 and include native rejection Status in errors.
The fixture now measures both actual 15s native cooldowns rather than overriding
Duration, in addition to physical heal/end, native curve progress and finish.
Player/fixture cleanup and all strict/log/hash gates remain mandatory.

**Inventory two-client bounded acceptance (2026-10-16, 01:57 Singapore):**
Network03 PASSES all sixteen parent/mesh x pickup/full x A/B x BP/Python
cases. Native server collision events are exactly begin/end; authority grants
and full-slot rejections match original BP. Both owning clients read matching
native inventory, QuickBar and equipment instigator state; the target drives
real Enhanced Input/GAS firing (one shot), while the other owner's inventory
and ammo remain unchanged. Native item rollback is acknowledged by both
clients after every case. Server player position/movement and client aim are
restored; all fixture scopes close. All three peers exit normally, strict
logs/protocol pass and 1,012 frozen input/reference hashes remain unchanged.
Host-tests05 PASSES 464 checks. Pads inherit their original replication flag
(true); it is not forced. Client pad Profile parity, remote audio, physical
client movement, placement, native exception gating and package are NOT
certified. This does not close 0.10 or later versions. Next 2N:
B_GrantAbilityPad_ApplyGE, retaining native Timeline/curve, collision and GAS.

**Inventory transient-status correction (2026-10-16, 01:42 Singapore):**
Network02 FAILS after two completed pickup/fire/rollback cases (original BP
and Python, target A) when a peer status read returns None during atomic file
publication. The next-case baseline assumed a dictionary. A pure readiness
gate now waits for both current inventory samples; it never substitutes a
stale sample and retains the same deadline/identity/value checks. Its negative
test covers None/missing/incomplete/different state. Historical Network02 stays
failed; Network03 must pass all sixteen cases and final process/log/hash gates.

**Inventory network harness correction (2026-10-16, 01:38 Singapore):**
Network01 FAILS after one case with a missing inventory status field. The base
uep_lyra_network import auto-started its generic health scenario because its
exclusion guard knew Weapon/EffectPad lanes but not the new Inventory lane;
two test tickers wrote the same peer status files. This is not inventory
replication acceptance. All owned peers have exited. The base guard now
excludes Inventory too; an executed AST guard test checks all three specialized
lanes stay off while generic MultiClient still starts. Network02 must rerun
the complete matrix. No production gameplay or native implementation change.

**Inventory real-player proof / multiplayer in progress (2026-10-16, 01:34 Singapore):**
Player01 PASSES all four parent/mesh x pickup-fire/full cases, each comparing
Python and same-class original BP. Native overlap grants one Pistol, selects
slot 1 and binds native B_WeaponInstance_Pistol to that item. One native
Enhanced Input frame fires through Lyra GAS on each Profile: 12 -> 11 ammo.
Full-slot cases grant nothing. Eight fixture pads are destroyed; original
inventory item/slot identities restore after each trial, final position/aim
error=0 and movement=[1,0] restored. Strict logs/normal exit/frozen hashes pass.
This is standalone authority, not replication. Host-tests03 PASSES 462 tests.
Inventory Network01 now starts a new sixteen-case two-client matrix with
native physical begin/end, owning-client equipment/ammo replication and fire,
unchanged other-owner state and native inventory rollback acknowledged by
both clients. Report contracts reject missing/foreign/partial evidence. Pads
are server-spawned fixture actors; replication is not forced, remote audio,
client pad Profile parity, physical client movement and travel/rejoin are not
claimed. No engine edit, C++ build, cook/package or publication.

**Inventory bounded native acceptance / real-player extension (2026-10-16, 01:19 Singapore):**
Differential02 PASSES all twelve cases (51.953s), native automatic mesh Tick
and both Profile transitions, physical parent/mesh pickup, full/no-controller
rejection, and native pad destruction. All sixty test actors are destroyed;
policy errors=[], grants=4, full=2, no-controller=2, destroy=2, ticks=372.
Strict logs, normal exit, official asset and frozen-input gates pass. This
lane uses test-owned plain controller/Pawn native services, not real-player
equipment/GAS/network proof. A separate four-pair real-Lyra-player fixture is
now prepared: physical pickup, native QuickBar equipment instigator, Enhanced
Input -> pistol ammo decrement, full-slot rejection, exact native per-trial
inventory rollback and final position/movement/aim restoration. It must pass
its own native run; existing twelve-case evidence is not inflated.

**Inventory first native failures (2026-10-16, 01:11 Singapore):**
Differential01 FAILS after the two construction cases pass. Native automatic
Tick reaches Python, but the generic positional call tries to convert the
last False to the native SweepHitResult out-struct. Use named bTeleport after
the first two inputs, leaving that out slot initialized by UEP. Cleanup also
detects retained test controllers: native AController::K2_DestroyActor is
intentionally a no-op. The fixture now uses the existing native actor_destroy
wrapper for only its own actors (production pad destruction remains K2).
No weakening of rotation, actor-cleanup or strict-log gates; rerun required.

**Inventory-pad asset authoring (2026-10-16, 01:09 Singapore):**
0.10-2M Assets01 PASSES in the marked Lyra stage. Both original BP class
identities survive; only one parent Interface/Set owns four virtual boolean
dispatch gates, with no related parent/child routers. Four original business
graph digests remain unchanged after compile. Two configured BP assets plus
DA_InventoryPadMixin are copied to Examples only after the authoring, normal
exit, strict-log, frozen-input and official-reference hash gates pass. This is
NOT runtime acceptance. Differential01 now runs the prepared twelve-case
native physical-overlap fixture. No C++ build, cook/package or official edit.

**Nameplate loopback acceptance / next batch (2026-10-16, 01:07 Singapore):**
Network14 PASSES all nineteen phases, native fire/reload/weapon switch,
respawn, both travels, departure, solo continuation and B rejoin. All four
processes exit normally; final protocol and strict-log gates pass, 415 frozen
input hashes remain unchanged. Source scopes A/B0/B1=32/32, 27/27, 5/5;
Manager=3/3, 3/3, 1/1; Widget=100/100, 88/88, 20/20. BP comparator roots
are also 100/100, 88/88, 20/20, active=0. Dedicated server has zero scopes,
consistent with the original client-only component configuration. A's third
nameplate PNG and rejoined B1's PNG were visually inspected: world, HUD and
native nameplates are visible; native/scalability warning banners remain.
This is bounded Editor/loopback acceptance with declared low-quality rendering
and fixture-owned old-Pawn/Source retirement, NOT projection parity, native
death-ability, native duration producer, package or full-version acceptance.
Host-tests16 PASSES 451 checks. No Engine/official Lyra implementation edit,
native build, cook/package or publication. Next: 0.10-2M inventory-pad marked
stage authoring followed by twelve physical-overlap/native BP comparisons.

**Pre-exit configuration snapshot safety (2026-10-16, 01:01 Singapore):**
Network13 was deliberately ABORTED before gameplay acceptance (only its two
owned peers stopped) when review found a new read_placement call in atexit.
It is not a runtime failure/pass claim. Native component policy is now read
before request_exit and copied into the pending report; finalization uses only
the immutable JSON snapshot plus pure policy counters, no new UObject calls.
A static regression covers both boundaries. Host-tests16 PASSES 451 tests.
Network14 is the next fresh complete run; no old failure report is rewritten.

**Nameplate full-path / placement gate correction (2026-10-16, 00:59 Singapore):**
Network12 completes all nineteen gameplay phases, both travels and B rejoin.
Clients A/B0/B1 pass final scope/root cleanup: Source scopes 32/32, 27/27,
5/5; Manager scopes 3/3, 3/3, 1/1; comparator roots 100/100, 88/88, 20/20.
It still FAILS overall because the server shutdown gate incorrectly demands
Source activity. The server actually records zero Source/Manager/Widget
scopes. Placement01 reads the real retained StandardComponents Action Set:
both NameplateSource and NameplateManagerComponent are client=true,
server=false. Official/stage asset SHA-256 both 1E790976...99F25C8; no save or
asset mutation. This is native configuration proof, not a new runtime pass.
The corrected gate requires that exact native policy, zero dedicated-server
component scopes/Add/Remove, and positive balanced client scopes. Frozen
reference/stage placement hashes are now checked by the driver. Host-tests15
PASSES 450 tests. Historical Network12 remains failed; Network13 must finish
all peers, native policy, protocol, strict logs and unchanged-input gates.

**Nameplate respawn comparator correction (2026-10-16, 00:46 Singapore):**
Network11 FAILS at respawn_a (140s readiness timeout). The unmounted BP
comparator remains at designer defaults while Python reaches the native Pawn
name/visibility/health state. This experiment does NOT prove parity and did
not reach either travel. Restore the previously working native UMG viewport
mount/Construct epoch (zero opacity); retain native release-hook cleanup,
exact comparator-root gates and the explicitly low-quality client budget.
No remaining Editor processes. Network12 is the next fresh attempt.

**Resumed native regression (2026-10-16, 00:40 Singapore):**
No leftover Editor/build processes on resume. WidgetReleaseRegression01
PASSES all 14 cases (16.73s); its PNG was visually inspected, showing native
indicators/nameplate labels and the pre-existing Steam configuration warning.
ComponentReleaseRegression01 PASSES all 11 cases with the post-release-hook
scripts and accepted 19-function transport revision. These bounded passes do
not close multiplayer or 0.10.0. Next: Network11, one server plus two clients,
including respawn, two travels, departure/rejoin and final cleanup/hash gates.

**Nameplate network diagnostics (2026-10-15, 20:06 Singapore):**
Still **0.10.0 development**, not released. Network08 FAILS an overbroad
native-health assertion: BP/Python both cache 1 for a Pawn with no initialized
native HealthSet (MaxHealth=0). The contract now declares that unavailable
case and still requires initialized native-health parity at every checkpoint.
Network09 FAILS on two simultaneous native Dash widgets after the second
travel. A bounded census now waits for convergence (four observations over
two seconds), without selecting one widget or clearing production state.
Network10 FAILS with server exit 3 in AsyncLoading2 during the second map
load: `Loading is stuck, flush will never finish`. This is NOT an out-of-memory
fatal, though free physical RAM was about 1 GB and native skinned-asset
compilation logged a memory-budget shortage. All owned peers have exited.

Opt-in nameplate BP comparators no longer enter the viewport and now release
their roots in the production native Unbind/Destruct/teardown epoch; normal
gameplay observers remain empty. Per-checkpoint and final comparator-root
accounting is fail-closed. The nameplate network lane declares a 30 FPS / low
scalability / 256 MB texture-pool client budget and explicitly does NOT claim
visual-fidelity acceptance. Host-tests13 PASSES 449 tests; post-change widget,
component and complete four-process network regressions are still required.
No engine/official Lyra edit, native compilation, cook/package or publication.

**Nameplate network diagnostics / next pilot (2026-10-15, 19:35 Singapore):**
Version remains **0.10.0 development**. Component Differential03 PASSES all
11 cases with stable UClass paths on the explicit 19-function asset revision
chain. QuickBarRegression19 PASSES its 12 cases/named query on that chain.
WidgetPawnReadyDiagnostic01 PASSES all 14 cases plus an additional real
original BP PawnReady -> InitializeNameplate -> SetNameText check: expected
Pawn, native PlayerState name, cached NameText and displayed text all agree.
This is before the new optional native-Bind observation hook below.

Network02 identifies an earlier comparator error: a UClass debug repr includes
Python refcounts (3 vs 2); identical native class pointers were mislabeled as
different. Both fixtures now compare UClass paths, with a static regression.
Network03/04 FAIL at respawn: Controller::Reset unpossesses the previous Pawn,
whose native HealthSet can be uninitialized (Health/MaxHealth=0), while both
BP/Python widgets retain cached progress=1. No Source EndPlay has occurred.
The nameplate lane now explicitly declares server old-Pawn native destruction
and client old-Source native destruction, identified by PlayerId before reset.
These are fixture lifecycle actions, NOT native death-ability certification.
Network05 FAILS an older respawn UI probe's whole-phase foreign-count=2
assumption; the revised proof requires exactly two synchronous injected
rejections/unchanged UI, counts subsequent native foreign deliveries separately
and rejects missing pairs or decreasing counters. Native UI policy is unchanged.
Network06/07 still FAIL at respawn due mismatched late-created BP Widget
initialization epochs. Refreshing only the late BP PawnReady does not resolve
the whole pipeline. None of these runs is accepted as completed networking.

Network08 is currently executing: an empty-by-default, validation-only native
Bind observer creates each test-owned BP comparator synchronously inside the
actual production Bind callback, before either init-state registration. The BP
uses its serialized instance Name selector, not nested registry mutation. The
probe does not rebind production, replay its lifecycle or copy its UI results.
Normal play has no observer. Full post-hook Widget/component/network cleanup
and hash/strict-log gates remain required. Host-tests09 PASSES 434 tests;
this includes next-pilot contract/model tests, NOT native inventory proof.

The next 0.10-2M pilot is prepared, not accepted: B_GrantInventory_Pad and
B_GrantInventoryPad_WithMesh, one parent Mixin Set, four virtual boolean
dispatch gates preserving original BP blocks, native inventory/RPC/audio and
mesh rotation. Nine policy checks and five contract checks pass. The generator,
guarded asset-authoring driver and a 12-case native fixture are written but NOT
executed. No canonical inventory assets are generated/copied yet. Finish the
nameplate network investigation first; do not claim these new files as runtime
acceptance or silently enable related-class routers. No Engine/official Lyra
implementation edit, C++ build, cook, package, commit, push, tag or release.

**Nameplate regression/network integration (2026-10-15, 18:56 Singapore):**
`20261015-nameplate-components/WidgetRegression01` PASSES fourteen cases on
the enabled component pipeline (18.172s, scopes 23/23, team proxies 13/13,
init unregisters 10/10, zero active/errors). Its PNG was visually inspected;
viewport comparison labels/native scene indicators are visible, with the
pre-existing Steam config warning banner. `TransportRegression01` PASSES
the prior native UI/Verb/copy/lifetime cases on the 19-function adapter.
`QuickBarAssets19` creates fresh accepted QuickBar/transport authoring evidence:
19 functions/59 nodes, all NINETEEN existing semantic digests preserved. Its
resaved transport has a new SHA-256; historical Assets01 is NOT rewritten.
`UEPNameplateAssetProvenance.ps1` checks the predecessor accepted hash was the
reauthoring input, every known function/node/digest, then current stage/overlay
output hashes. Component/network drivers accept that explicit revision chain.
The opt-in nameplate two-client probe/protocol is implemented: production
local manager, native Indicators membership/config, same-class original BP
component and Widget comparisons, native binding, respawn/travel/departure and
final scope/root/team/init cleanup. All 413 host tests pass; these are not
network proof. `Network01` FAILS before complete phases: A observes descriptor
configuration difference, originally without per-field diagnostics; a separate
unused RemoteSession auto-host port 2049 conflict also emits native errors.
The difference is now logged in full; Network02 is executing with only that
unused RemoteSession plugin disabled. Do not accept it before four final
reports/exits/strict logs/input hashes and nameplate-specific gates pass.

**Nameplate native component differential (2026-10-15, 18:46 Singapore):**
`20261015-nameplate-components/Differential02` PASSES all eleven native/BP
cases in 53.844 seconds and strict normal-close/no-error gates. Source scopes
and actual helper roots both close 10/10; Manager both close 3/3; final active
counts/errors are zero. This includes the real production manager, Character
and plain-Pawn descriptors, targeted discovery through the compiled VM,
Profile listener-only resume, Source Remove during native EndPlay, nonlocal
manager self-destruction and native Python/original manager destruction.
Repeated registration retains the former descriptor in BOTH original BP and
Python; native membership confirms it, and fixture-only orphans are actually
unregistered/checked. No silent production deduplication was introduced.
Differential01 remains FAILED before case comparisons: fallback proxy clearing
used attribute assignment, triggering Editor PostEditChange and reconstructing
the dynamically added component. Runtime set_property fixes both Source and
Manager; a negative notification regression is added. The first version of
that mock reused one cancelled proxy and failed its own expectation;
host-tests03 now PASSES all 407 tests with distinct native-proxy models.
`WidgetRegression01` is running against the 19-function transport and enabled
production Source/Manager; not accepted until its report/log/exit gates pass.
The dedicated nameplate two-client lane remains to be implemented/accepted.

**Nameplate component checkpoint (2026-10-15, 18:42 Singapore):**
`20261015-nameplate-components/Assets01` PASSES retained Source/Manager BP
Interface/CDO authoring and the 19-function / 59-node typed VM adapter. All
15 preceding graph semantic digests and official reference hashes remain
unchanged. Five accepted assets are copied to Examples/the marked stage;
this is asset authoring, not component runtime acceptance. The independent
15-function asset backups and their hashes are in `Before19Functions`.
The production Manager now explicitly passes itself to K2_DestroyComponent:
Blueprint's DefaultToSelf pin is not a ProcessEvent default. Both components
count real helper roots/unroots. A separate 11-case native differential and
strict report driver are added, covering native deferred component finish,
original-BP discovery/configuration/membership, typed messages, Profile
resume, source/manager native destruction and legacy duplicate descriptors.
Host tests pass 406 checks; `Differential01` is currently executing, NOT yet
accepted. Nameplate-specific multiplayer and later migration batches remain
open. No compile/cook/package or publication is performed by this step.

**Latest DLL checkpoint (2026-10-15, 17:51 Singapore):**
HostBuild03 and UEPRefresh02 both PASS guarded incremental builds (25.27s /
20.62s, zero compiler warnings, no Engine rebuild). Protected Engine hashes
stay unchanged. The latest Lyra UEP DLL SHA-256 is
`A37911F9105E33A130BE049C93F86911CAD5C2B305CEB04C702CCE8AF5B65555`.
CallMatrix02 PASSES all ELEVEN lanes, including native multicast broadcast,
with strict normal-close/declared-negative-error gates and stable input hashes.
NameplateDifferential06 PASSES all fourteen actual Widget/BP comparisons in
15.765 seconds. Final scopes 23/23, team proxies 13/13, init delegates 10/10
explicitly unregistered (init_owner_released=0), zero active/errors, strict
normal-close/no-ensure gate. The 1280x720 PNG was inspected: the viewport
comparison labels and native scene indicators are visible; native Steam
warning banner remains. Native damage/team reassignment, projection parity,
component-pipeline and multiplayer nameplate proof are NOT claimed.
Lifecycle02 PASSES three PIE sessions on the latest DLL; PackageLoad02 PASSES
fresh-process/imported-package discovery, and Transport02 PASSES typed VM
delivery/copy/lifetime regression. QuickBarDifferential02 PASSES all twelve
production/BP cases, nine named-output queries and scopes 12/12 on the latest
DLL; its screenshot was inspected. Network03 PASSES all nineteen phases on
this final DLL, two clients/two travels/B0 leave/B1 rejoin/four clean exits,
all existing optional HUD gates, native weapon input and BP/Python/native
comparisons. Final server/A/B0/B1 quickbar scopes are 0/0, 12/12, 12/12, 6/6,
query counts 0/15/8/2, zero active/errors; progress scopes 0/0, 6/6, 6/6, 2/2.
All 24 PNGs are hashed; A switched-fire and B1 rejoin-respawn were inspected.
The switched-fire frame has a steep controlled aiming view; this is not a
physical/free-camera acceptance claim. Native Editor warning banners remain.
The native broadcast defect's required latest-DLL regression is now accepted
within these bounded Editor lanes, not packaged/non-Editor certification. 2L
component discovery/management and nameplate-specific multiplayer stay open.
Their next native execution plan and verified API boundaries are recorded in
`Migration/NEXT_NameplateComponents.md`. Version remains 0.10.0 development;
no commit/push/tag/release, no package, and no custom Engine implementation edit.

**Earlier 5.8.1 runtime checkpoint (2026-10-15, 17:08 Singapore):**
EditorBuild01, HostBuild02 and UEPRefresh01 are complete. HostBuild02 builds
the source-matching generic host (220 actions); UEPRefresh01 refreshes only
the Lyra UEP module with -NoEngineChanges. Both have zero compiler warnings
or errors, and the protected Engine hashes/BuildId remain unchanged. The two
deprecated callback warnings from the full build are resolved for Editor
targets only; ordinary non-Editor package discovery remains an open risk.

CallMatrix01 PASSES ten lanes on the rebuilt 5.8.1 DLLs. Lifecycle01 PASSES
three PIE sessions in one Editor: placed/spawned objects, Construction,
Begin/End counts 2/2 per session, two closed scopes, native GC and restored
routers. Transport01 PASSES compiled-VM UI/Verb delivery, nested copies,
wrong-reader/outside-delivery rejection and close/no-later-callback checks.
All have strict completion/normal-close evidence and unchanged input hashes.

PackageLoad01 PASSES a new two-process regression: the first saves Main,
Companion and their Mixin Set only in the marked generic stage. A fresh
process loads Main's class with a hard CDO import of Companion's class;
both BP packages are automatically discovered without any registration API
in the load phase. Both prove per-instance Python/original profiles without
type replacement, no implicit original after a Python override, automatic
fallback for an absent callable, and restored originals after unregister.
This directly exercises Editor OnEndLoadPackage; no cooked/non-Editor claim.

QuickBarDifferential01 PASSES all twelve production HUD/BP comparisons on
5.8.1 (64.266 seconds), nine external named-output Python queries, scopes
12/12 and zero final active/error state. Its 1280x720 production screenshot
was visually inspected: native gameplay/HUD, filled and empty quickbar slots
are visible. host-tests02 again passes all 388 checks, not runtime proof.
Network01 FAILS early on WinError 1175 while ReplaceFileW publishes a harness
status JSON, before the two-client scenario completes; owned processes are
stopped and failed evidence retained. The bounded atomic I/O retry now also
handles 1175 (no destructive delete/non-atomic publication); partial-replace
1176/1177 and unrelated errors still fail immediately. Three new host tests
cover success/exhaustion/non-retryable errors; host-tests03 passes 391.
Network02 PASSES the same dedicated-server/two-client weapon lane: nineteen
phases, two travels, B0 leave/B1 rejoin, native firing/reload/switch/respawn
and all previous optional HUD gates. All four owned processes close normally;
stable input hashes and post-shutdown state are checked. Final A/B0/B1
quickbar scopes are 12/12, 12/12, 6/6, with query counts 15/8/2; progress
scopes are 6/6, 6/6, 2/2, with zero final active state/errors. These final
counts come from shutdown, not the intentionally live pre-exit snapshots.
Twenty-four PNGs are hashed; A/B0 join and B1 rejoin respawn PNGs were
visually inspected. Existing native Editor widget-factory warning banners
remain. This is not physical touch, replicated duration-message, native
interaction-producer or packaged acceptance. Version
work is still 0.10.0 development; nameplate 2L and later batches remain open.
No cooking, packaging, commit, push, tag or release was performed.

NameplateAssets01 now PASSES widget authoring on 5.8.1: retained BP class and
Tick, Interface/CDO, two four-node init-state transports, six-node original
health cleanup, stored original team proxy and unchanged official asset hash.
The two accepted BP/Set assets are copied to Examples, not official Lyra.
The prepared fixture's WorldType access is corrected to get_world_type:
native UWorld::WorldType is not a reflected UPROPERTY. NameplateDifferential01
then exposes real native CompareTeams tuple/int errors in UpdateVisibility.
The exact owned process is stopped early after recording the unrecoverable
error; its -1 exit is NOT graceful cleanup or a runtime pass. The native
reflected signature has ReturnValue plus TeamIdA/TeamIdB out parameters,
unlike its non-reflected C++ convenience overload. Python and the fixture now
strictly unpack three outputs; the mock now models this ABI instead of an int.
Two new output-selection/shape checks bring host-tests04 to 393 passes.
NameplateDifferential02 is stopped and FAILED: its unowned ticker handle was
immediately deallocated, so game startup did not execute the comparisons.
The fixture now retains the handle, uses the nullable reflected controller
query, and queries widgets with native GetAllWidgetsOfClass instead of the
nonexistent ue.get_objects API. Two static entry-point regressions bring
host-tests05 to 395; this is still not native acceptance.

NameplateDifferential03 executes/passes its first eight comparisons, then
FAILS Profile resume visibility parity and produces a native unregister
ensure during shutdown. The test now rebinds both candidates through the same
native resume entry, rather than comparing different binding epochs. UEP's
nameplate cleanup now checks the native GameInstance component manager/owner
before its interface helper (whose ensure requires both), and separately
counts init_owner_released when that lifetime is already gone. The final gate
requires explicit unregisters to be exercised and bound = unbound + owner
released; release is not relabeled as a successful native unregister. Both
negative/native-owner mock tests pass; host-tests06 passes 397.
NameplateDifferential04 PASSES ten comparisons including both Profile resumes,
then FAILS on a nonexistent fixture broadcast_event API. All 21 scopes and 12
team proxies close, all nine init registrations explicitly unregister, and the
native ensure is absent; that clean cleanup is not a pass of the missing cases.
The fixture now uses UEP's existing broadcast multicast entry point and logs
each completed comparison. Its API regression rejects broadcast_event too.
NameplateDifferential05 FAILS/crashes at UEP's legacy multicast broadcast
entry, after the same ten cases. Native source/stack proof: GetMulticastDelegate
takes PropertyValue, but UEP passes the UObject container; the inline delegate
implementation directly reinterprets that pointer, causing garbage access-
detector state and an ensure/OOM, not evidence of genuine concurrent writers.
UEPyObject.cpp now resolves ContainerPtrToValuePtr before reading/copying the
delegate and handles an unbound sparse delegate's null result. No Engine edit.
A new native delegate-broadcast lane checks empty/bound delegates, native and
Python calls, parameter rejection/recovery and no callback after unsubscribe.
The matrix grows from ten to eleven lanes. Guarded plugin-only rebuilds and
all affected native regressions must pass before accepting this correction.
HostBuild03's first launch guard rejects leftover idle MSBuild nodes from the
completed UEP refresh; no compiler was started by that rejected invocation.
The SDK's supported build-server shutdown releases those idle nodes before
retrying the guarded incremental build. No full Engine rebuild is authorized
or needed for this defect; the earlier ten-lane/multiplayer results refer to
the preceding DLL, not the next one. Nameplate runtime/component gates stay open.

An additional real-filesystem I/O stress check remains separate from UE
acceptance. IOStress01 fails a too-strong uninterrupted-presence assertion
(its first diagnostic does not distinguish absence from invalid state).
IOStress02 explicitly follows read_json's existing polling contract: 500
writes, four readers, 10,386 valid reads, two 1175 retries, 724 absent polls,
no malformed/backward snapshot, and final sequence 500. Absence is counted,
never accepted as an ACK; continuous path visibility is NOT proven. Neither
this stress check nor the 391 host checks substitute for Network02's full gate.

**User-approved 5.8.1 dependency/build step (2026-10-15):**
after being informed that the current planner lists 964 Engine/plugin DLLs,
the user explicitly approved synchronizing dependencies and building matching
5.8.1 Editor plus UEP/Lyra validation modules. This supersedes the earlier
no-Engine-build boundary for this environment update only. Do not modify
Engine implementation or official Lyra, clean caches, package, relabel
manifests, or start duplicate build/test jobs. Use the marked full Lyra stage
for LyraEditor Win64 Development and the generic host for call/lifecycle
acceptance, preserving the mixed source worktrees. Dependency dry-run,
conflict/backup checks and actual build/test evidence are separate gates;
neither a running build nor its exit code alone is runtime acceptance.

Dependencies01 now PASSES: 302 updates, two additions, 31 obsolete dependency
removals; 304/304 downloaded/updated, about 979.6 MiB transferred, and a second
official dry-run reports zero remaining actions. No force overwrite and zero
locally modified dependency paths. The 31 removed dependencies are recoverable
with the other replaced files under BeforeDependenciesAndBuild. In total 1,606
dependency/runtime binary/metadata files (8,480,104,103 bytes) have verified
independent SHA-256 backups there. PDB/object caches are ordinary replaceable
build products, not backed-up runtime acceptance. Default Python stays 3.11.8.

EditorBuild01 completed at 15:54 Singapore on 2026-10-15: all 4,610 actions,
UBT Result Succeeded (5,714.65 seconds), 5.8.1 Editor version and matching
Lyra/UEP module IDs. BuildId is `2f7b5df8-1c9a-4414-a598-6d3b022aa38d`.
It is a BUILD/METADATA pass, not runtime acceptance. The build has zero C++
errors and two C4996 warnings, both from UEP's old package-load delegate.
Progress/acceptance continuation did not resume immediately after compilation;
do not treat the quiet interval as a stuck compiler or a completed acceptance.

The Editor discovery path is now adapted to OnEndLoadPackage's complete batch
without changing Engine source. Its old mutation/deferred/teardown guards
remain. Non-Editor builds retain their existing per-package callback; its
known unsafe/deprecated API and packaged replacement/acceptance remain open.
This is not silently warning-suppressed or claimed fixed for packaged games.
Incremental UEP rebuilds and native call/PIE/load/network gates are required
before accepting this change.

EditorBuild01 used one official build invocation combining
LyraEditor and ShaderCompileWorker Win64 Development. The actual graph has
4,610 actions (different from the earlier 8,236 OUTPUT FILE list). The user
then explicitly allowed full CPU use and requested regular progress; this run
uses -AllCores and up to 16 parallel actions rather than the former two-action
cap. No clean/package or additional Editor test process. Idle MSBuild servers
from the completed managed-tool phase were shut down using the bundled SDK's
supported command to release memory for C++; the active UBT/compiler job is
not stopped. Native/runtime gates follow compilation; current results are above.

**Historical 5.8.1 prerequisite check (before the approved build, 2026-10-15):** the user explicitly
approved updating F:/UnrealEngine's source to official `5.8.1-release`, commit
`71fe36aac5a8df5ccd66c763ffc902b29b6a9c43`, then requested acceptance on it.
The 826 upstream delta paths are applied and verified, with all 777 replaced/
removed local files independently backed up under
E:/UnrealEngineSourceUpdates/20261015-5.8.0-to-5.8.1/Backup. Extra projects and
existing compiled Editor files are preserved. Dependencies/Setup and Engine
compilation have NOT been run; the installed compiled Editor remains 5.8.0,
BuildId `e3415f47-6f61-4145-b84b-cfbeb0377ffa`. Changing source version does not
upgrade the executable or qualify previous runtime reports for 5.8.1.

Actual evidence is in
`.build/LyraValidation/BlueprintPython/20261015-ue581-acceptance/`:
`host-tests01.json` passes all 388 Python 3.11.8 host checks with zero failures,
errors or skips, explicitly runtime_acceptance=false. `CallMatrixPreflight01`
fails on Module BuildId differs before an Editor launch. All 20 checked host/
full-Lyra stage manifests differ from the current compiled Editor BuildId.
`HostBuildPlan01` uses the official UBT/UHT planner with -NoEngineChanges;
it exits 5 (FailedDueToEngineChange) before C++ compilation, not a runtime
test failure. Its guard lists 8,236 existing Engine outputs including 964 DLLs,
1,695 objects and 963 libraries. These are OUTPUT FILE counts, not action counts
or a time estimate. No action plan is executed or accepted as a compatibility
proof. UHT does write 37 generated intermediate files plus ordinary caches/
diagnostics; all seven checked canonical Engine source-version/binary files
retain their before-check hashes. No runtime Editor/test process remains.

`engine-readiness.json` records the prerequisite failure and required output
statistics. Actual 5.8.1 native/differential/lifecycle/multi-client acceptance
remains unrun. A matching 5.8.1 Editor and rebuilt validation modules are needed
first; the planner indicates a broad Engine/plugin rebuild, not a UEP-only
refresh. Do not bypass this with manifest relabeling or an unrestricted build.
Explicit user direction is needed before the large dependency/build step.
Earlier accepted runtime gates below remain historical 5.8.0 evidence only.

Environment discovery / earlier guarded recovery check (2026-10-15): the only
confirmed compiled UE5.8 Editor is F:/UnrealEngine (binary 5.8.0; source now
5.8.1 as above). F:/Epic Games/UE_5.8.1 exists
but contains zero entries, not an installed Editor. The UE_5.7 directory has
no Editor executable/Build.version either; Epic install records only list
4.27/5.2. Do not report a directory name as a usable matching installation.

`20261015-environment-recovery/HostPlan01` and `LyraModulePlan03` run the
official UBT action planner with -NoEngineChanges, not compilation. The former
requires NetCore DLL/object/import-lib plus Engine metadata updates; the latter
still requires NetCore object/import-lib. Both guards reject before compilation.
HostModulePlan02 restricts five project/UEP modules and exports ZERO actions,
but this is NOT Lyra compatibility or runtime acceptance, and no manifest was
relabeled. LyraPrecompiledPlan04 also hits the Engine-change guard and exposes
an invalid artificial recursive Session/UBA diagnostic combination; that
Session workaround is removed, not used as a compatibility bypass.

Each attempt preserves existing stage DLL/PDB bytes via owned evidence hard
links and copies its metadata. The seven checked canonical Engine files have
unchanged hashes before/after; no compilation, Engine source/binary change,
asset authoring or runtime pass is claimed. UBT writes its ordinary diagnostic
trace/cache while inspecting; this is not an Engine binary build. No owned UE
test process is left. A full Lyra-compatible recovery still needs permission to
update the shared NetCore build products, or an independently matched binary
set. Do not execute an unrestricted target build or force the old BuildId.

Current checkpoint (2026-10-15): QuickBarDifferential03 PASSES all twelve
current-DLL cases, including nine routed Python named-output queries, scopes
12/12 and an inspected production screenshot. QuickBarRespawnNetwork03 PASSES
all nineteen phases, two travels, B0 exit/B1 rejoin and four normal exits on
the same new UEP DLL. Client A/B0/B1 query counts are 15/8/2; quickbar scopes
12/12, 12/12, 6/6; no final active scopes/errors. All 24 PNGs are hashed;
selected A/B0/B1 respawn and A switched-weapon screenshots were inspected.
The respawn screenshots show '1 RESPAWNING'; native Editor warning banners
remain. These are bounded native gameplay/local-message and display proofs,
not original BP OnInitialized, physical mouse, replicated message or package
acceptance. The driver summary in Differential03 predates its corrected
external-query flag; the runtime report and network query counters are the
actual implementation proof, not that stale summary flag.

TransportRegression01 is FAILED AT PREFLIGHT, with process=null and
'Editor BuildId mismatch', not a failed runtime transport test. A separate
BMFont build is currently using the shared Engine installation. Engine
UnrealEditor.modules/version changed to e3415f47-6f61-4145-b84b-cfbeb0377ffa,
and NetCore.dll also changed (old accepted SHA256 5650E5F0..., current
D47E6995...). This is not merely a metadata mismatch that can safely be
ignored. Do not rewrite Engine or relabel staged module manifests to force
loading. Continue nameplate source migration and host checks while determining
a source-compatible, stable binary set for the next native regression.
No duplicate UE test process or new Engine build was started.

Active next small batch: **0.10-2L nameplates**. The read-only captured audit
contains NameplateSource (16 nodes), NameplateManagerComponent (82) and
W_Nameplate (104). Native IndicatorManager/Descriptor/projection, team and
health capabilities remain; Python will own discovery/register/unregister and
name/team/health/visibility orchestration. No nameplate assets or runtime gates
are accepted yet. All remaining authorized batches remain unfinished.

2L implementation checkpoint: `nameplate_mixin.py` covers retained Widget
Bind/Unbind, immediate native init-state callback, name/text, normalized health,
team material and authored visibility decisions. `nameplate_source_mixin.py`
preserves Add-before-Discover-listen and EndPlay Remove. The manager preserves
local-controller eligibility, both listeners before Discover, native descriptor
configuration and Map/register/unregister ordering. No new business Tick,
native Health/team/inventory writes or replacement Unreal classes.
Native init-state delegates require two four-node VM helpers; original health
cleanup is six nodes. Component authoring prepares four new typed transports
(expected total 19 functions / 59 nodes, all fifteen earlier semantic digests
preserved). These are expected authoring postconditions, NOT generated assets.

Captured graph details requiring native confirmation: TeamIcon SetBrush has no
exec connection, so Python does not invent an icon refresh. OnSameTeam/no-filter
visibility returns do not restore a previously collapsed widget. K2 Select's
unmatched-index default is Option 0 (null Health resource here). Repeated
register replaces the Pawn's Map value but leaves the former descriptor in the
native indicator manager; the source model explicitly tracks this legacy risk.
Do not silently deduplicate it or call the mock an original-BP proof.

`20261015-batch2l/host-tests05.json` passes **388** checks, zero failures/errors/
skips, runtime_acceptance=false. Forty are new nameplate policy/discovery,
binding/reentry/cleanup, report-negative, optional native-reference and startup
checks; real SubscriptionScope is used by the widget policy tests. All three
PowerShell authoring/focused drivers parse cleanly. The prepared fourteen-case
runtime fixture explicitly separates actual production binding, original BP
comparison and test-owned native viewport Destruct/remount; it disclaims native
damage/team reassignment, physical input, projection parity and packaging.
It is NOT executed. Component pipeline and multi-client fixtures still need
native authoring/bounded evidence first; 2L and the full version remain open.

`Assets01` actually fails the nameplate authoring launch guard with the same
BuildId mismatch: process=null, copied assets=0. No Unreal process starts and
no canonical nameplate asset is copied. The shared BMFont job is now building
Shipping; it is unrelated and is not stopped, modified or reported as this
task's compile. A stable matching Engine/project binary set is required before
native acceptance can resume. No forced manifest relabel, Engine edit, package,
commit, push or release was performed in this continuation.

Next order: restore compatible validation prerequisites within the no-Engine-
change boundary; finish current-DLL transport/lifecycle/native Dash/Respawn
regressions; author/inspect nameplate Widget and components with the prepared
guards; run actual BP/Python, native unregister/delayed-ready and multi-client
travel/rejoin checks. Reconcile the duplicated-descriptor edge against real BP.
Only after those gates proceed to touch parent/world interaction batches.

Latest accepted bounded step (2026-10-14): ability-failure feedback uses an
explicit native RetriggerableDelay with a one-int32 Linkage completion routed
to Python. No external ticker, new script Tick or Engine/source build is used.
`Assets06` passes clean authoring after prior failed attempts; original Tick
flag is restored, ten transport functions / 32 nodes and the old six digests
remain intact. Native delay completion declaration contains no UI business.
`FailureDifferential05` passes all seventeen original-BP/Python cases, 69.280s,
final scopes 4/4, no active/errors. Its screenshot is too early for visible
text, so it is not accepted as the visual gate. `FailureDifferential06` repeats
all seventeen with a later screenshot: both 'UEP resumed' labels were actually
inspected, root opacity 1.0, retained class and strict closed logs/input hashes.
The first native Outro is observed at 1.000s on both sides, frame step 0.016s /
tolerance 0.032s. Deferred latest foreign payload and persistent callbacks now
have actual baseline evidence, not only the former source-model hypothesis.

The different-message failure in `FailureDifferential04` was a real policy
bug: SameFailureText returns one named output as `(False,)`, not a bare bool.
Python now validates tuple shape and extracts the bool. The initial host mock
had the wrong output shape; it now matches reflection and has negative shape
checks. `host-tests08.json` passes 237. Native callback Linkage/duplicate/late
completion checks and culture report guards are included, not runtime substitutes.

`TextFixtureAssets01` compiles a four-node test-only native live-text seed,
without changing production transport or copying it to the distributable overlay.
`NativeCulture02` passes an English/Chinese/English roundtrip on one native
live-table FText broadcast (47.859s). Correctly labelled English and Chinese
PNGs were inspected; both widgets display the same translated text. Native
timer cancellation to hold already-received text is explicit fixture setup.
NativeCulture01's data gate passed but its deferred screenshots had swapped
language labels; it is not accepted as visual evidence. The text seed lives
only in the marked validation stage, not in the shipping overlay.

`AbilityFailureNetwork01` stopped without complete peer reports or a driver
summary; it is incomplete, not a pass or a diagnosed migration failure. No
owned UE process remained before retry. `AbilityFailureNetwork02` now passes
all 19 server/A phases, 14 B0 and 3 B1 phases, two travels/rejoin/four clean
exits. Final failure scopes server/A/B0/B1 are 0/0, 6/6, 6/6, 2/2; active/errors
zero. Selected A/B0/B1 images were inspected. This lane tests local synthetic
messages and null-controller filtering, not RPC or native GAS production.
`TransportAdapterRegression01` passes the current ten-function asset's old
UI/Verb nested-copy/wrong-reader/outside-delivery/cancel paths (32.720s).
Duration is exercised by the simultaneous progress network lane, failure/FText
by the bounded differential/culture lanes. Native failure producer/dead/invalid
health and packaging remain open. Do not mark the whole pilot/version done.

Current small batch: **0.10-2I W_DashCooldown**. Typed duration filtering,
native game-time charging/material/animation and native-health visibility
policy are implemented on the retained class. Assets01 passes clean authoring;
the duration transport is reused unchanged, four-node original death-binding
cleanup and proxy storage are ownership-only plumbing. DashDifferential01
fails live-Profile animation parity: cleanup incorrectly paused native UMG
animations without script callbacks. That pause was removed, not hidden by
a relaxed assertion. Runs 02/03 expose an invalid fixture assumption: the
production Dash belongs to UIExtension's native pooled Slate container, not
a UPanel/viewport, so RemoveFromParent does not trigger Destruct. Lifecycle
tests are explicitly separated onto same-class test-owned viewport widgets;
nine other comparisons still use production UI. Run04 fails because it tries
to inspect a proxy field correctly cleared by cleanup; it now holds/checks
the original proxy itself. Run05 passes all 11 (50.422s), material tolerance
0.00001, inspected PNG, scopes 11/11 and no active/errors.

DashNetwork01 then fails on the second travel (13 A / 12 B0 phases recorded):
two production pooled entries retain active Python subscriptions. This is
not treated as a passed lifecycle gate. A read-only shared UIExtension
GetAllEntries sampler now disarms inactive pooled entries, blocks inactive
Tick from rebinding health and permits natural reinsertion/Construct/Tick to
resume. It does not alter pools, replay events or scan all UObjects per frame.
Snapshot is metadata-only at shutdown; active pool membership is refreshed
before the network owner census. Host-tests07 passes 269, including eight new
membership/negative checks. DashDifferential06 repeats all 11 on this fix
(50.297s), scopes 11/11 and pool watches 2/2, no active/ticker/errors. The stricter
pure final report gate also passes; host-tests08 passes 270. DashNetwork02
has no recurrence through both travels/B0 exit, but fails at B1 rejoin on
WinError 5 during atomic status replacement. No complete network pass is
claimed. The Windows harness now uses delete-sharing readers and ReplaceFileW
for existing destinations (the ordinary os.replace path fails with a held
reader on this filesystem). A real held-reader/old-snapshot replacement test
passes; permanent access errors still raise after ten bounded attempts.
DashNetwork03 is stopped by host preflight before UE launch: the new test
exposes that os.replace alone is insufficient. Host-tests10 passes 272 after
ReplaceFileW. DashNetwork04 fails a second-read TOCTOU: _server_roster sees a
missing status after its initial roster check. Peer status now uses one fresh
snapshot per peer per frame, never a previous-frame fallback; missing data
waits for the next frame and wrong identities still fail. host-tests11 passes
276, including four snapshot-cache checks.

**DashNetwork05 passes** all 19 server/A, 14 B0 and 3 B1 phases, two travels,
Pawn restart/rejoin and four normal exits (server 230.500s). Final Dash scopes
server/A/B0/B1 0/0, 14/14, 12/12, 3/3; Health 0/0, 7/7, 5/5, 1/1. Pool watches
0/0, 4/4, 4/4, 1/1; A and B0 each record one actual inactive-pool deactivation.
No final active scopes/ticker/errors. Selected A/B0/B1 images inspected.
The original native weapon and all earlier optional HUD lanes pass together.
NativeDash01 actually reaches the original granted GA_Hero_Dash/native ASC and
native death callback, but fails an invalid-health fixture assumption: clearing
UserWidget's owning player falls back to player zero. NativeDash02 instead uses
native post-death UnPossess, and passes five cases (45.141s): native 1.5s duration,
repeat rejection, native countdown, exact-once death/hidden wrapper and a
separately declared synthetic failure payload with genuinely absent Pawn.
Its PNG was inspected; final Dash/failure scopes 4/4 and 4/4, pool watches 1/1,
no active/ticker/errors. No Health/ability/CDO/velocity writes or widget event
replay. This is not lethal damage or physical key input. Native repeated Dash
produces zero user-facing failures, so that producer remains untested. Host
checks pass 282; whole-version/package and remaining groups stay unfinished.

Current small batch: **0.10-2J W_RespawnTimer**. PlayerState duration/completion
filtering, native 0.25s function timer, CommonNumeric/material/audio and retained
Outro completion policy are implemented. Assets01 cleanly passes copied
Interface/CDO, preserved class/official hash, five-node exact delegate cleanup
and reused duration/verb transport. RespawnDifferential01 fails because its
remaining-time variable is function-local BP storage, not a UObject field;
policy now uses a Python local and observations explicitly derive the native
deadline. Run02 exposes a wrong graph-only first-material inference: actual
BP updates BOTH FillGlow/Fill, so Python now matches that measured behavior.
Run03 passes ten runtime cases but fails an incorrect minimum-three-scope
gate. Baseline changes to BP before first Construct; only candidate initial
and resumed Python create scopes. Gate now requires exactly two epochs, not
an unbounded lowered count. Run04 cleanly passes all ten (51.578s), both
materials/numeric/audio/native timer/pause/completion/Profile states, final
scopes 2/2 and shared pool watches 3/3, zero residue/errors; PNG inspected.

Collapsed respawn entries cannot use Tick to rearm after native pool release.
Optional dormant membership watches now reactivate an explicit business resume
after native reinsertion, never replaying Construct or modifying the pool.
Reentry and inactive/active watcher tests pass; host-tests07 passes 299.
NativeRespawn01 actually observes the original 5s producer/restart but rejects
same-frame UI closure; the next run waits for native completion/Outro to
converge within the unchanged bounded phase. NativeRespawn02 passes three
cases (49.735s): native GAS death -> original GA_AutoRespawn -> duration ->
Python/BP/audio/timer, genuinely new Pawn with positive native Health, native
completion and closed timers/visibility. Scope 1/1 and pool watches 2/2, no
residue/errors; PNG inspected. No synthetic duration/completion, Health/CDO
writes, manual widget events or lethal-damage/acoustic claim.
RespawnNetwork01 fails the strict log gate after both travels: fallback
Destruct reads an already-invalid CountdownAudio native reference before
valid(value) can inspect it. Both A/B0 show the same traceback; it is not a
passed exit/lifecycle run. A narrowly scoped optional-audio read now handles
only that exact invalid-value condition on a still-valid widget, propagating
other errors. Both Python and original proxy/timer/delegate cleanup have host
negative coverage. host-tests09 passes 313, including six respawn network and
five native-report checks. The stricter native report recheck passes the saved
NativeRespawn02 data; it is not a new engine run. RespawnNetwork02 is running
all earlier HUD lanes plus the local typed ownership/native pool lane. Run02
passes all phase/data/shutdown gates (server/A 19, B0 14, B1 3; respawn scopes
0/0, 3/3, 3/3, 1/1), but fails the driver screenshot gate: simultaneous native
Shot commands overwrite Dash paths with Respawn paths. This is not a completed
network pass. An owned one-request-per-frame queue now serializes commands;
the driver still requires/hashes every PNG, separately from queued/issued
counts. Run03 passes all 19 phases/two travels/rejoin/four exits and all earlier
HUD data/lifetime gates with the repaired queue. It supplies all 24 required
PNGs; no final pending requests. Respawn scopes server/A/B0/B1 are 0/0, 3/3,
3/3, 1/1; shared pool watches 0/0, 7/7, 7/7, 2/2, zero active/ticker/errors.
A/B0 each record one real pool deactivation, but no native reinsertion yet.
Selected respawn A/B0/B1 images were inspected: simultaneous short interaction
and respawn UI overlap, so visible respawn text is not accepted by filename
alone. The local respawn fixture now uses 3s and captures after 2s, after other
short test HUD lanes close. Run04 will repeat this on the next accepted
transport generation; it is not already passed.

RespawnDifferential05 passes all twelve current cases, including actual native
viewport RemoveFromParent/AddToViewport on an explicitly test-owned same-class
pair. No manual Construct/Destruct replay or production-pool remount claim.
Held original proxies become inactive, late owner delivery does not mutate the
removed pair, native remount rearms once and resumes timer/audio/material/text.
Final scopes 4/4, shared pool watches 3/3, no active/ticker/errors. PNG inspected.
Host-tests11 passes 319. Multi-client
completion, actual inactive-pool reinsertion, current affected regressions and package
remain open. All remaining roadmap batches remain authorized and unfinished.
No C++ build, Engine/reference edits or source publication.

Current small batch: **0.10-2K W_QuickBarSlot**. The captured official audit has
106 nodes: two typed QuickBar owner messages, native slots/component reads,
icon-material/empty/selected animation decisions, per-slot total ammo and the
mouse-to-Enhanced-Input entry. Runtime baseline must verify the branch/cast
semantics; the compact graph alone is not acceptance. Inventory/equipment,
replication, GAS and animation assets remain native. Assets01 passes configured
class/Interface/CDO/original Tick and fourteen transport functions/44 nodes,
old ten digests unchanged. QuickBarDifferential01 records twelve display/model
cases but FAILS the report gate: Python mouse calls remain zero. Its strict
log also contains a RawValue conversion traceback: FInputActionValue reads
back as a Python scalar, which cannot be fed into generic struct marshalling.
That first run is not accepted. A three-node native Axis1D input transport
now keeps the struct in the VM, with no UI/game branch; Assets02 passes
fifteen functions/47 nodes and unchanged prior fourteen digests. The fixture
also asserts the mouse count immediately, not merely its default EventReply
type. QuickBarDifferential02 passes all twelve cases, mouse count exactly one,
final scopes 12/12 and no active/errors; its production quickbar screenshot
was inspected. The stricter exact-twelve-epoch report recheck also passes saved
data, not a new engine run. Host-tests05 in batch2k passes 347 (including policy,
report, network negatives and four actual baseline-reconciliation method tests).
QuickBarRespawnNetwork01 completes the first eleven native gameplay phases
but fails first-travel readiness: reused production empty slot retains old
numeric 84 while the newly created BP counterpart has the template's 999.
No native input traceback recurs. The comparator now retains the same BP
counterpart for the same production widget across worlds, uses native owning
player / actual viewport remount / listener resume, and never copies Python
numbers/icons or replays OnInitialized. Identity changes still create a fresh
baseline. QuickBarRespawnNetwork02 is running all preceding HUD lanes, native
slot/fire/reload/switch reads and refined 3s respawn screenshots. Named output
IsThisTheActiveQuickbarSlot remains BP for external
callers, explicitly outside the current mixin ABI; internal Python decisions
use native index reads. BP OnInitialized baseline parity, physical mouse input,
full native weapon switching/replication acceptance, cast-failure runtime and
full 2K release remain open. No complete multi-client 2K pass yet.

QuickBarRespawnNetwork02 subsequently PASSES all nineteen phases, both travels,
native pistol/rifle inventory and selected/ammo UI comparisons, B0 exit/B1
rejoin and all four normal exits. Quickbar scopes server/A/B0/B1 are 0/0,
12/12, 12/12, 6/6; respawn 0/0, 3/3, 3/3, 1/1. All final active/errors/pending
screenshot requests zero; shared pool watches 0/0, 7/7, 7/7, 2/2. A's travel
ACKs prove unchanged production AND original counterpart identities across
two distinct worlds, retained empty numeric 84/84 and one/two native baseline
owner-resume epochs. All 24 PNGs are present/hashed; selected A/B0/B1 respawn
images now clearly show '1 RESPAWNING' after the overlapping short UI closes,
and were actually inspected. Native Editor warning banners remain.

Next required gap is named-output Mixin dispatch. Initial scoped core work is
in progress in PythonFunction.cpp / UEPyMixin.cpp: explicit
`uep_named_outputs=True`, named dictionary outputs, isolated conversion before
copying, actual BP caller addresses/packed-bool masks and original fallback
output propagation. Mutable reference inputs, RPC/static/latent/delegate
functions stay rejected. Build01 is a plugin-module-only failure: C4800 rejects
implicit PyDict_Check int-to-bool; one local UBA worker was also restarted for
memory pressure. It does not build Engine modules. The explicit comparison
fix and two-action cap yield Build02 success in 7.79s (one compile/two links).
Generic/Engine BuildId still matches. Previous generic and Lyra DLL/PDBs are
preserved in workspace evidence. New DLL SHA256 is
`1037876718A5B7ECB41B7C60D90EBEAA6183B5D49E4DD75F6CE367A32874DB6A`.

Native01/02 fail fixture setup before routing: assigning an Actor's Target
attribute did not set the native BP reference. The fixture uses explicit
set_property, and its diagnostic no longer mutates the original BP count.
Native03 passes seven actual cases: precompiled BP multiple outputs, repeated
native/BP entry, explicit-original and missing-method fallback, invalid opt-in,
return+named native signature and unregister/type restoration. Packed bool
layout is NOT explicitly proven by those adjacent sentinel checks. Negative01
data passes five cases, but its plain wrapper rejects expected error exit1.
The matrix driver now explicitly whitelists only three intended conversion
errors, requires unchanged seeded caller output storage/no original BP side
effect, recovery/restoration and a normal closed log.

CallMatrix01 passes all ten lanes on the new source-matching generic DLL:
standalone/shared signature (legacy unmarked outputs still rejected), callsite,
experimental body, named positive/seven and negative/five, inherited selector,
construction forwarder, soft-class path and exception recovery. All frozen
matrix input hashes rechecked before copying only the accepted UEP DLL/PDB and
two changed source files to the marked Lyra stage. The QuickBar Python profile
now opts in its IsThisTheActiveQuickbarSlot dictionary output; internal calls
also use the routed UFunction with strict named-bool tuple checking. Host tests
pass 348. QuickBarDifferential03 is running the new DLL/query; its current HUD
and later network/lifecycle/package acceptance are NOT already passed.
No Engine full build, Engine/reference source edits, package or publication.

Earlier resumed work (2026-10-14): execution permissions are unrestricted again.
`20261014-batch2h/Assets02` genuinely passes asset authoring in 84.932s: ten VM
transport functions / 32 nodes, six old graph digests unchanged, compiled
Interface/CDO, seven exact original-delegate cleanup nodes and unchanged
official reference hash. Canonical failure/transport assets have been copied.
The former pre-log startup limitation is historical, not the current blocker.

`FailureDifferential01` times out before its fixture: the isolated UserDir/DDC
triggers eight active shader workers. All owned processes are stopped. The
driver now reuses existing runtime caches by default; isolated caches are
explicit opt-in. `FailureDifferential02` runs real UI and passes its first four
cases, then fails the paused-timer comparison. Source/runtime evidence shows
UUserWidget::NativeTick advances widget latent actions with Slate InDeltaTime
even while world game time is paused. The original world-clock Python policy
is not equivalent. Final scopes/tickers balance 2/2, zero active/errors, but
the differential is failed, not partially accepted as complete.

The intermediate, subsequently superseded fix used native Widget Tick delta, with a
two-node transport-only Tick declaration in the staged BP. Schema 2 now
requires frozen world time AND continued UI expiry under pause; timer tolerance
still stays within two observed UI frames / 0.15s. `host-tests03.json` passes
223 with that intermediate policy. Assets03 fails the Tick declaration, Assets04
compiles it but FailureDifferential03 still fails timing/animation alignment.
It is removed by the native-delay implementation, not accepted as equivalent.

Earlier completed bounded group: production reticle host. `20261013-batch2f/
HostDifferential02` passes eight original-BP/Python cases and native death-event
one-shot cleanup (not lethal damage). `ReticleHostNetwork01` passes nineteen
phases/two clients/rejoin/four exits. Host final scopes server/A/B0/B1 are
0/0, 7/7, 5/5, 1/1. Standalone and selected network screenshots were inspected;
known native audio/Editor warnings remain. No C++ build or package was needed.

Last bounded accepted group: ability progress (0.10-2G). `20261013-batch2g/assets01.json` passes
compilation/serialized Interface/CDO and prior transport semantic digests.
`ProgressDifferential01` failed a fixture-wide callback count: the actual HUD
also received the injected message. It is retained as a failed run. The fixture
now uses the actual production widget and per-instance counts.
`ProgressDifferential02` passes eleven original-BP/Python comparisons (71.211s):
owner/foreign/repeated typed messages, automatic UMG Tick, numeric/material/text,
completion, 1.109s paused wall time with frozen native game time, explicit hidden
Profile resume, native Destruct and no later delivery. Final scopes 3/3, zero
active/errors; screenshot inspected. Initial collapsed widgets have different
initialization times; StartTime equality is required after the shared message,
not before. Native interaction-ability production is not tested.

`ReticleAdapterRegression01` passes six geometry/three message cases, actual ADS
input and native equipped-shotgun fire 8->5, final reticle scopes 6/6. Screenshot
inspected; native warning banners remain. `TransportAdapterRegression01` timed
out during NullRHI startup before its fixture ran and was stopped. The new
offscreen `TransportAdapterRegression02` passes nested-copy/wrong-reader/
outside-delivery/close regression with a strict closed log. No build/package.

Examples tests now pass 196. The optional `-AbilityProgress` network lane is
implemented; `AbilityProgressNetwork01` fails at the first travel's readiness
timeout after recording eleven phases. Server and clients reload the map and
recover native Health; a complete gate is not passed. All owned processes are
stopped. `AbilityProgressNetwork02` reproduces the failure with durable per-client
readiness history (player/panel/combat/progress reason plus actual BP/Python
duration state). The new map/player/Health recovers, but both clients report
`production-widget-unavailable` with an empty progress scope ledger. A reused
hidden widget loses its listener at Destruct; OnInitialized is one-shot, and
Collapsed prevents Tick-based rearming. Python Construct now idempotently
rearms, and BP fallback Construct uses the explicit preserve-model resume.
`ProgressReconstructRegression01` passes twelve cases including native
same-widget RemoveFromParent/AddToViewport remount. Final scopes 4/4, zero
active/errors, strict closed logs and inspected screenshot. The construct fix
has bounded standalone acceptance (118.167s, exit 0). `AbilityProgressNetwork03`
passes the complete nineteen-phase gate and unchanged timeout: two clients,
native firing/reload/switch/respawn, two travels, B0 leave/B1 rejoin and four
clean exits. Server/A/B0/B1 progress scopes balance 0/0, 6/6, 6/6, 2/2; all zero
active/errors. Owner/foreign deliveries are 0/0, 19/19, 14/14, 3/3. Twelve PNGs
are hashed; A/B0 join and B1 rejoin progress images were inspected. Existing
native warning banners/resource preparation remain; no warning-free claim.
The lane uses the actual production widget, hidden original-BP
baseline, per-phase local synthetic owner/foreign messages, visible countdown
comparisons, native completion and shutdown scopes. Foreign Instigator is the
owning Controller (not its Pawn), not a claim about a remote player. It does not
certify a native interaction producer or replicated GameplayMessage delivery.

Active group: ability-failure feedback (0.10-2H). Python policy/lifecycle and
`generate_ability_failure_mixin_assets.py` are written, but no generated assets
or runtime acceptance yet. Typed ReadFailure/BroadcastFailure and opaque native
FText copy/equality helpers are planned to extend the adapter; no string round
trip. Same reason is an authored no-op; different reason waits for native Outro,
then Intro/one-second game-time delay. Existing animations remain. The deferred
latest-message behavior is an audited hypothesis requiring real BP comparison.

Seventeen new host checks cover policy, game-clock pause, opaque text handling,
native-event continuation model, idempotent Construct, ticker/root release and
cleanup despite errors. `20261014-batch2h/host-tests01.json` passes all 213.
The first 211-test attempt had one pre-existing atomic-rename test fail in the
restricted environment's temporary directory; a workspace-owned temp root
resolves it without changing permissions. The new reusable host runner records
counts/status and explicitly keeps runtime_acceptance false.

The opt-in production-widget/original-BP differential is now implemented, but
**not executed**. It declares seventeen ordered cases for owner/foreign/same
reason, real pause, the first native Outro within two observed game frames of
one second, native animation completion, hidden Profile resume, natural
Destruct/remount, deferred latest foreign payload, persistent callback result
and cancellation with animation/delay pending. It never invokes Tick,
OnAnimationFinished or the original outro events to manufacture success.
The baseline is test-owned and uses an explicit listener-only resume; the
fixture does not replay original OnInitialized. Its FText producer is synthetic
display text, not localization-history or native GAS proof; dead-health and
multiplayer branches remain separate gates.

Ten new report-gate/static fixture checks bring the host suite to **223** in
`20261014-batch2h/host-tests02.json`, zero failures/errors/skips. They reject
missing/reordered cases, identical-but-wrong visible state, widened/NaN timer
limits, unsupported claims and unbalanced post-shutdown scopes/tickers. The new
PowerShell driver parses without errors. `fixture-preflight01.json` actually
verifies that the failed Assets01 authoring report blocks the driver before any
runtime output directory or UE process is created. This is a launch-guard check,
not seventeen runtime passes. No new Unreal process was launched in this step.

Historical restricted-environment blocker: `Assets01` exits 0 after 5.976s but creates neither
Unreal log nor fixture JSON. `StartupDiagnostic01` without the new UserDir
flag also exits 0 after 0.814s with neither file. No authoring/runtime gate is
passed; no canonical failure assets or extended transport have been copied.
Application event diagnostics and Examples Git metadata were inaccessible in
that restricted execution environment. Do not infer a specific crash
cause, bypass restrictions, widen permissions or repeatedly start UE processes.
The owned processes exited; their process reports/empty stdout/stderr remain.

Immediate next work:

1. Resume asset authoring only once the existing Unreal binary can reach normal
   log initialization in the execution environment; keep marked stage/fresh
   evidence directory/current DLL source and BuildId guards. Fix any actual
   generator diagnostics, then verify six old transport graphs and Interface/CDO.
2. Run the prepared `Run-UEP58FocusedAbilityFailureValidation.ps1` against a
   newly accepted asset-authoring directory, then prove
   message ownership/duplicate/retrigger/pause/animation/lifetime and two-client
   travel/rejoin behavior before extending. The complete 32-candidate batch,
   physical input, network shotgun, current packages and release review are
   still open. Native localized FText identity, retained BP deferred payload/
   repeated callback ordering and timer frame boundary need explicit evidence;
   mock-policy success is not that evidence. Static audit counts are not
   migration completion counts.

Marked disposable full stage:
`F:/UnrealEnginePython5/.build/LyraValidation/Full/Stage/Lyra/LyraStarterGame.uproject`.
Reuse source-matching current Editor DLLs; no full Engine build. No owned Unreal
test processes remain at this checkpoint. Check current processes and reports
before starting a new lane. This group performed no C++ build/cook/package,
commit, push or release.
