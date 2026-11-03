# Native migration hardening and delivery

The user selected all four follow-up groups on 2026-11-03. Progress is tracked in
[hardening_batches.json](hardening_batches.json). This work keeps the selected
UE5.8.1 / CPython3.11 / Win64 Development target. CPP09 actual desktop Escape/Menu
acceptance remains explicitly deferred; no computer or OS keyboard operation is
authorized by these groups.

| Group | Required evidence |
| --- | --- |
| H01 | Actual native callback exceptions for damage admission, original equipped item-cost check/apply, reward settlement after a broadcast, and native Reset; no duplicate native payment/reward, successful subsequent calls, inactive failed Reset and restored subscriptions/profiles |
| H02 | Interleaved native-fallback/Python timings on identical native fixture entrypoints; a twenty-minute actual game process with repeated native Reset/respawn, persistent PlayerState, bounded traces and quiescent post-GC object plus OS memory/handle samples |
| H03 | A fresh independent stage created from the reference project and versioned SDK, bridge, overlay, fixtures and ordered production recipes; no old stage/compiler output copied; protected Engine build, composed source inventory and actual fresh-stage runtime |
| H04 | Current protected Win64 Development Game build, actual cook/stage/archive, cooked asset and loose Python/dependency fingerprints, and real packaged standalone/server/two-client execution using the packaged executable |

H02 timing includes the same reflected entrypoint and installed bridge admission
on both routes. It does not measure bare-engine calls or rendered frame rate.
The primary sustained run is at least 1,200 seconds after runtime readiness.
Work pauses around two scheduled full native GC passes. Operational budgets are
declared before that primary run: post-warmup private-memory growth <=256 MiB,
handle growth <=32, world actor population range <=25, no mixin-registration
growth, <=8 quiescent policy contexts, and diagnostic traces <=128 entries.
These are workload-specific checks, not universal memory/performance guarantees.

The initial H01 run retained its failure evidence. It exposed an engine ensure
for an incomplete Python world policy. The adapter now logs a rejected operation
and returns failure without replaying the original native body. The first cost
fixture invocation incorrectly used an editor-only factory in a game world;
the runtime case now observes the existing player's native spec/ActorInfo/item.
Reset's incomplete plan is changed to its terminal EndAbility action so a failed
script plan cannot leave its native GAS instance active or reset/broadcast its
Pawn. Affected compiler dependency files select only the changed body units;
unchanged UHT, SDK, bridge, other game units and protected CPP09 stage are reused.

Fresh reproduction and Game packaging are separate stage gates. They require
their own target builds; they are not routine full regression after every edit.
Every accepted group is committed and pushed to Examples before the main
validation scripts and Demos pointer, with both remote heads verified.

## H01 accepted

[H01 acceptance](NativeGameplay/H01-acceptance.json) closes thirteen real native
exception/recovery cases: damage admission three times, original equipped-item
cost check/apply six times, a reward callback failing after its native broadcast,
and three Reset failures followed by actual new-Pawn recovery. Failed payment
does not deduct, recovery deducts once, failed settlement broadcasts once, and
closing its observer suppresses later native deliveries. Failed Reset ends its
GAS instance without resetting the Pawn; the following valid request respawns it.
All temporary declarations, selectors and subscriptions are restored. The normal
default offline frontend and 52 opt-in startup selection tests pass.

Only LyraGame body units 3 and then 1 were compiled for the two separate fixes;
UHT, unit 2, TopDownArena, SDK, bridge and Engine are retained. Reward inputs are
explicit callback fixtures. Tags are detached value snapshots before replacing
their source native map. This does not claim that every game operation is
transactional after arbitrary user-code side effects. H02-H04 continue separately.

## H02 incremental world-lifetime repair

The first full-length run exposed the original twelve-minute match ending and
seamless travel invalidating the cached world. Mixin get/set/clear selectors
accepted a retained wrapper without first checking its tracked weak owner. The
shared conversion helpers now reject that wrapper before inspecting its raw
native pointer. Only `UEPyMixin.cpp` and the SDK import-library/DLL links rebuild.

[The selector guard acceptance](NativeGameplay/H02-selector-guard-acceptance.json)
records ninety seconds of active native gameplay, one actual early server travel,
three safe get/set/clear rejections, three original Reset/respawns and 4,250 native
queries. The harness reacquires the ready world and excludes travel waits from
its active duration. Post-GC actor/router populations remain constant. Engine,
game/bridge DLLs and the preserved CPP09 checkpoint keep their protected hashes.
The subsequent full-length H02 run passes the independent operational gate below.

## H02 accepted within its operational budgets

[H02 acceptance](NativeGameplay/H02-acceptance.json) records 1,200 seconds of
active gameplay, 58 original native Reset/respawns, 57,250 native queries and one
natural match-ending seamless travel. Its 34.843-second travel/readiness wait is
excluded from activity time. The three expired selectors are safely rejected.

After the declared 120-second warmup, 111 OS samples and 103 quiescent native-GC
samples pass the budgets set before the run. Median private bytes grow by
217,219,072 bytes (207.16 MiB; limit 256 MiB), handles by four (limit 32), actor
population ranges by one (limit 25), router population stays constant, and at most
two temporary native policy contexts remain (limit eight). This is a bounded
twenty-minute observation, with measurable memory growth; it is not a proof of
unlimited stability or leak freedom.

The current SDK benchmark interleaves twelve 300-call batches per route/family:
14,400 timed calls total after separate warmups. Damage admission medians are
6.18 microseconds native and 17.22 Python; Pawn data medians are 4.70 and 15.43.
Both use the same reflected fixture entrypoint; the native fallback includes
the installed bridge admission. These figures do not measure rendered frame rate.
H04 remains a separate actual-package gate.

## H03 accepted

[H03 acceptance](NativeGameplay/H03-acceptance.json) closes the independent
[reproduction entry point](REPRODUCE_NATIVE.md): fifteen versioned recipes compose
63 production C++ outputs, 9,702 original and 1,871 versioned inputs are pinned,
and 11,341 final staged files match the ordered copy/overlay/patch composition.
No old project binaries or intermediate build directories are imported. The
owned production descriptor disables only the reference test plugins in addition
to the existing SDK/bridge and AndroidFileServer settings.

The reviewed project build contains 23 modules and 289 compile/link actions,
with every output inside the fresh stage. Local loader manifests use the unchanged
Engine BuildId; Engine source/binaries/manifests and the original Lyra project are
preserved. Thirteen actual native exception/recovery cases pass on these new
DLLs, with independent result/log gates and normal interpreter shutdown. Initial
guarded full-target attempts, the content-only descriptor fix, and the missing
reference test-plugin setup are retained in the ledger. The latter configuration
change regenerated shared compiler headers and rebuilt the affected project
modules before final runtime acceptance.

H04 now builds the Game target and its runtime dependencies in the same isolated
project. That is a separate compilation configuration from the Editor target;
its first runtime-library build is not a routine full regression after an edit.
