[English](HARDENING_REVIEW.md) | [简体中文](HARDENING_REVIEW.zh-CN.md)

# Native migration hardening and delivery

The user selected all four follow-up groups on 2026-11-03. Progress is tracked in
[hardening_batches.json](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/hardening_batches.json). This work keeps the selected
UE5.8.1 / CPython3.11 / Win64 Development target. H01-H05 kept CPP09 desktop input
separate. On 2026-11-05 the user unlocked the screen and authorized continuation;
[CPP09 actual-window acceptance](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP09-acceptance.json) now closes
that input gate. The earlier scope and capture limitations below remain historical.

| Group | Required evidence |
| --- | --- |
| H01 | Actual native callback exceptions for damage admission, original equipped item-cost check/apply, reward settlement after a broadcast, and native Reset; no duplicate native payment/reward, successful subsequent calls, inactive failed Reset and restored subscriptions/profiles |
| H02 | Interleaved native-fallback/Python timings on identical native fixture entrypoints; a twenty-minute actual game process with repeated native Reset/respawn, persistent PlayerState, bounded traces and quiescent post-GC object plus OS memory/handle samples |
| H03 | A fresh independent stage created from the reference project and versioned SDK, bridge, overlay, fixtures and ordered production recipes; no old stage/compiler output copied; protected Engine build, composed source inventory and actual fresh-stage runtime |
| H04 | Current protected Win64 Development Game build, actual cook/stage/archive, cooked asset and loose Python/dependency fingerprints, and real packaged standalone/listen-authority/two-client execution using the packaged executable |

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

[H01 acceptance](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H01-acceptance.json) closes thirteen real native
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
transactional after arbitrary user-code side effects. H02-H04 acceptance follows.

## H02 incremental world-lifetime repair

The first full-length run exposed the original twelve-minute match ending and
seamless travel invalidating the cached world. Mixin get/set/clear selectors
accepted a retained wrapper without first checking its tracked weak owner. The
shared conversion helpers now reject that wrapper before inspecting its raw
native pointer. Only `UEPyMixin.cpp` and the SDK import-library/DLL links rebuild.

[The selector guard acceptance](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H02-selector-guard-acceptance.json)
records ninety seconds of active native gameplay, one actual early server travel,
three safe get/set/clear rejections, three original Reset/respawns and 4,250 native
queries. The harness reacquires the ready world and excludes travel waits from
its active duration. Post-GC actor/router populations remain constant. Engine,
game/bridge DLLs and the preserved CPP09 checkpoint keep their protected hashes.
The subsequent full-length H02 run passes the independent operational gate below.

## H02 accepted within its operational budgets

[H02 acceptance](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H02-acceptance.json) records 1,200 seconds of
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
H04 records the separate actual-package gate below.

## H03 accepted

[H03 acceptance](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H03-acceptance.json) closes the independent
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

## H04 accepted

[H04 acceptance](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H04-acceptance.json) closes current Game delivery
from the same independent project. The cold Game configuration compiled 1,190
actions, including its Engine runtime dependencies inside the owned project;
4,105 compiler output/PCH/dependency paths stay inside that stage. Existing Engine
distribution binaries, manifests and source stay unchanged. This first Game
configuration build is separate from the Editor build and incremental regression.

The actual cook processed 4,707 packages. The archived container listing includes
all 246 original candidate assets, 493 overlay assets, twelve runtime maps and
three stage-only typed message observers. Production assets and source fingerprints
stay fixed. The inner packaged executable equals the new Game build. Cooked
presence does not establish all original candidate behavior.

Eight actual packaged processes pass: thirteen standalone native exception/recovery
cases, the normal frontend flow, and Damage/Pawn network lanes with one listen
authority and two real remote clients each. The native host LocalPlayer is removed.
Together the network lanes check eight authority trials and sixteen independent
client rule views, including replicated damage, spawn classes, Reset, RPCs,
restoration and observer cleanup. Files coordinate timing/acknowledgments; native
RPCs carry gameplay state. All eight processes exit normally.

Every process loads CPython from the archive with its home and 4,578 receipt files
inside that archive. One standard-library test INI receives UAT's UTF-8 BOM/CRLF
transformation: exact normalized bytes must agree, while every other byte stays
strict. Its original failed pure dependency summary is retained beside a reviewed
summary; the successful native process was not repeated.

The first network attempt exposed the packaged Game target ignoring Editor-style
`-server`. The successful runs use its supported listen URL. The dedicated-server
contract also expected no authority UI/cosmetic completion; listen preserves a
stable UI reference and its native local completion message. The listen-specific
checker asserts those facts and retains all other raw peer assertions. The first
successful Damage run's failed pure gate is preserved, with a separate review of
the unchanged peers; Pawn uses the final checker directly. Neither pure gate fix
triggered another build, cook or repeat of successful gameplay.

All four selected groups are accepted for UE5.8.1 / CPython3.11 / Win64 Development.
CPP09 physical Escape/Menu was deferred at this capture and completed separately
on 2026-11-05. Packaged Dedicated Server,
Shipping, additional platforms, rendered graphics and hardware/audio acceptance
are outside these results.

## H05 rendered frame rate and CPU follow-up accepted

The user subsequently requested actual FPS and CPU comparisons.
[H05](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/H05-acceptance.json) and
[its method/results](RENDERED_PERFORMANCE.md) add an actual D3D12 offscreen
comparison on the current package, without compilation or recooking. This
compares only the shared native world-policy carrier; other migrated layers stay
fixed. At 1080p Medium, four balanced pairs per workload provide 38,274 analyzed
frames. Windows CPU snapshots independently check process CPU accounting.

The fixed noncombat scene gives Native/Python 120.56/120.39 average FPS,
79.36/78.52 low FPS, 36.92%/36.72% whole-machine CPU and 3.30/3.32 ms GameThread.
Its paired local intervals include zero; this does not distinguish an effect.
With 200 additional reflected rule queries per frame, Native/Python give
120.23/118.26 FPS, 71.29/66.44 low FPS, 37.28%/39.85% CPU and 4.54/8.25 ms
GameThread. The pressure test adds 3.71 ms to Python GameThread and 2.57 CPU
percentage points, reducing FPS by 1.64%. This is a separate synthetic workload,
not a normal gameplay or universal performance claim. CPP09's separate actual-window
input gate subsequently passed on 2026-11-05.
