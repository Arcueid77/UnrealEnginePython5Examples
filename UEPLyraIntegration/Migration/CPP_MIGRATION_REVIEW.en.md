[English](CPP_MIGRATION_REVIEW.en.md) | [简体中文](CPP_MIGRATION_REVIEW.md)

<a id="lyra-c-业务迁移确认清单"></a>

# Lyra C++ business migration confirmation checklist

Shortlist date: 2026-10-31. 2026-11-01 Users confirm to submit existing changes first, and then implement them step by step in the recommended order.

This round of execution includes **CPP-001 to CPP-015, with a total of 15 candidate function groups divided into 9batch **. CPP-016 to CPP-030 are the other 15 candidates who need to verify the entrance or operating conditions first; 2026-11-02 has been selected CPP-016～018, see the second phase progress. Subsequently, user requirements continued to be advanced until all were completed. CPP-019～030 have all been selected. See the progress of the third phase. Candidates here are counted by business function group, and the same C++ file can contain multiple candidates; other implementations in the file continue to assume native responsibilities.

See [C++ Batch Progress](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/cpp_batches.json) for the current execution scope, batch status and acceptance ledger. The unified status of the three phases and subsequent verification can be found in [Completion status and evidence index] (completion_status.json): 30 candidates have been implemented and accepted according to the confirmation scope: 29 production replacement, 1 proficiency verification. After 2026-11-05 users unlock the screen, CPP09 passes 14 real Escape inputs, 7 menu switches, 2 map switches and interface/input recovery. For complete records and representative screenshots, see [CPP09 Acceptance] (NativeGameplay/CPP09-acceptance.json). Unified indexing reviews all referenced files; two early compilation intermediate files retain historical and subsequent batch fingerprints. The following staged records retain the scope of that time. The source code ledger retains the initial status and fingerprint of the candidate proposal on 10month31; the actual implementation status is subject to the batch progress. The original 246 blueprint candidates and 22 acceptance records will be retained and will be counted independently in the new phase.

<a id="扫描范围"></a>

## Scan range

The reference source code is native `F:/LyraStarterGame`. This round plans to support UE 5.8.1, CPython 3.11, Win64 and Development.

| module | path abbreviation | C++ implementation files | header file | Build rules |
| --- | --- | ---: | ---: | ---: |
| LyraGame | LG | 225 | 232 | 1 |
| ShooterCoreRuntime | SC | 12 | 14 | 1 |
| TopDownArenaRuntime | TA | 5 | 5 | 1 |
| total | | **242** | **251** | **3** |

LG refers to `Source/LyraGame`; SC refers to `Plugins/GameFeatures/ShooterCore/Source/ShooterCoreRuntime`; TA refers to `Plugins/GameFeatures/TopDownArena/Source/TopDownArenaRuntime`. ShooterExplorer and ShooterMaps do not have separate Source directories. The 26 source code and build files of LyraEditor, and the 18 source code and build files of ShooterTestsRuntime are reserved according to the editor or test module. Engine and common plug-ins such as CommonGame, CommonUser, GameplayMessageRouter, GameSettings continue to provide native capabilities.

[Source Code Account](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/cpp_source_inventory.json) records the path, SHA256, line number, candidate ownership and retention reasons file by file, and locates 30 candidate 65 function symbols. Among the 242 implementation files, 13 contains candidates recommended for execution first, 14 only contains conditional candidates, and 215 is classified as native reserved by module responsibility.

This is a complete scanning of specified module files and location of candidate functions. Other files use module responsibility classification, not a complete semantic audit on a function-by-function basis. The actual call entry, reachability and parameter transfer are confirmed in the corresponding batch; "Keep native" does not mean that these files can never continue to be separated from the rules.

<a id="接口使用规则"></a>

## Interface usage rules

Already UFUNCTION is called directly from Python when the parameters and return values are supported. Existing overritable events are reused first. For ordinary UFUNCTION C++ direct calls and non-reflected functions, you need to confirm the real call point, and add events or adapters with clear types at the business boundary if necessary. Simply adding the UFUNCTION tag does not allow native direct calls to automatically enter Python.

Existing Mixin is hosted via the persistence blueprint class. Existing configuration blueprints can be reused; native instances or non-blueprintable types need to first determine thin blueprint subclasses, instance events, or other clear adaptation methods. Pure primitive types cannot apply this assumption directly. The newly added access port must actually pass through the original call chain, and then use real operation to prove Python execution and native fallback path.

Static functions, RPC, delegate signatures, latent functions, and mutable references maintain their respective documented boundaries. When it is necessary to migrate its business, use ordinary instance events or clear non-RPC business entries; native replication, prediction, and scheduling responsibilities continue to be retained. By default, the existing UEP binding is reused; when it is really necessary to supplement the general capabilities, API changes and affected regressions will be listed separately in this batch.

<a id="建议先执行的15个候选"></a>

## 15candidates recommended for execution first

| No. | Native function group | Python Responsible | Access and native responsibilities |
| --- | --- | --- | --- |
| CPP-001 | SC `UElimStreakProcessor::OnEliminationMessage` | Accumulation of consecutive kills for non-suicide kills, selection of reward tags, and clearing of consecutive kills for those killed | Native listening callbacks add event entries with clear types; message listening and logout retention |
| CPP-002 | SC `UElimChainProcessor::OnEliminationMessage` | Reset or accumulate combos according to the actual configured time window, and select reward messages | Retain the native server clock source; add event entry; time window comparison and boundaries are consistent with the original version |
| CPP-003 | SC `UAssistProcessor::OnDamageMessage`、`OnEliminationMessage` | Cumulative damage contribution by target, excluding killers, generating assist results and clearing the target record | Retain native damage and kill message sources, and connect two business callbacks to Python; broadcast reuses existing type adapters |
| CPP-004 | LG `ULyraTeamCreationComponent::ServerChooseTeamForPlayer`、`GetLeastPopulatedTeamID` | Spectator branch, effective team number statistics, minimum number of people and number selection when the number of people is the same | Natively continue to set team identity, create team objects and copy status; provide read-only input and selection result entrance for decision-making |
| CPP-005 | LG `ULyraBotCreationComponent::ServerCreateBots_Implementation` | Default number, editor override and priority of URL parameters, build loop | Reuse the existing BlueprintNativeEvent; the native SpawnOneBot continues to create and initialize Controller/Pawn. Client placeholder branches for serverless code retained |
| CPP-006 | Selection segment of LG `ULyraBotCreationComponent::CreateBotName`, `RemoveOneBot` | Name pool, naming after exhaustion, selection of robots to be removed | Add access points for naming and selection; retain UE random source, RemoveAtSwap semantics and native self-destruction, destruction order and original behavior restrictions |
| CPP-007 | SC `UTDM_PlayerSpawningManagmentComponent::OnChoosePlayerStart` | Select the spawn point based on enemy distance, spawn point occupancy and alternate routes | The original one is responsible for occupation, collision and actual rebirth; the original signature contains a variable array reference, and the access port passes a controlled read-only snapshot and returns the selection result. |
| CPP-008 | Rule segments for LG `ULyraPlayerSpawningManagerComponent::ChoosePlayerStart`, `GetFirstRandomUnoccupiedPlayerStart` | Bystander selection, available candidate grouping, randomization and fallback order | Native reserved cache maintenance, Play From Here, occupancy query and TryClaim; Python do not directly overwrite the native candidate cache |
| CPP-009 | LG `ULyraQuickBarComponent::CycleActiveSlotForward`、`CycleActiveSlotBackward`、`GetNextFreeItemSlot` | Skip empty slots, forward and reverse loops, and select the first empty slot | Query and call existing UFUNCTION; confirm all production call points. SetActiveSlotIndex Continue to use the native server RPC, and keep the equipment and copy |
| CPP-010 | LG `UPickupableStatics::AddPickupToInventory` | The traversal order, quantity, and package arrangement of templates and existing instances | GetPickupInventory, AddItemDefinition, AddItemInstance continue to use the native interface. Static function does not serve Mixin target; migrate caller or add explicit instance entry |
| CPP-011 | Business segments of LG `ALyraWeaponSpawner::AttemptPickUpWeapon_Implementation`, `ResetCoolDown`, `OnCoolDownTimerComplete` | Picking conditions, available status process after successful release, arrangement of cooling end and re-inspection | Reuse existing events; provide a narrow interface for necessary operations that are not reflected. Native retention timer handles, scheduling, copying, OnRep, collisions and mesh updates |
| CPP-012 | Rule segments for SC `ULyraAccoladeHostWidget::OnNotificationMessage`, `OnRegistryLoadCompleted` | Target channel and player filtering, request number, rules for loading results into the queue | DataRegistry, assets are loaded asynchronously and retained; the callback is completed to deliver typed results with a clear life cycle, and non-reflected fields cannot be read using reflection |
| CPP-013 | SC `ULyraAccoladeHostWidget::ConsiderLoadedAccolades`、`ProcessLoadedAccolade`、`DisplayNextAccolade`、`PopDisplayedAccolade` | Sequential display, position label, cancel label, queue advancement and display duration selection | Reuse CreateAccoladeWidget/DestroyAccoladeWidget event; natively retain resource loading, timer and necessary object ownership; clear data export to complete non-reflected fields such as serial number |
| CPP-014 | Arrangement segment of LG `ULyraGameplayAbility_Interact::UpdateInteractions`, `TriggerInteraction` | Default or dedicated indicator selection, addition and deletion order, current selection, and first selection | There is already UFUNCTION used for calling; the real replacement requires processing the native call entry. Scan tasks, native interface CustomizeInteractionEventData, ActorInfo constructs and GAS triggers remain within the explicit adapter |
| CPP-015 | LG `ULyraHUDLayout::HandleEscapeAction` | Escape menu selection and push request to UI layer | Native retention of CommonUI input binding and asynchronous interface loading; verification of real input entry Python, input recovery and control destruction |

CPP-011 is the arrangement of the native refresh station parent class, CPP-012/013 is the rule of the native reward host, CPP-014 is the option arrangement of the native interactive skills. The originally migrated refresh station blueprint business, reward control blueprint and interactive skill blueprint continue to be used as dependent tests and cannot be counted repeatedly as new migration completions.

<a id="建议批次及对照验证"></a>

## Recommended batches and control verification

Batches are organized by common call chains and shared access points. After entering each batch, first locate the actual class, CDO, production caller and interface, and then freeze the function scope of the batch. When it needs to be split, keep the original numbers and corresponding relationships, and record the new sub-items and reasons.

| batch | candidate | primary control | results that must be maintained |
| --- | --- | --- | --- |
| CPP01 | CPP-001 to CPP-003 | Actual damage and kills generate native messages; dedicated servers, dual clients and native bots | Kill streak accumulation and death clearing; actual CDO branches before, equal to, and after the combo time window; assist damage accumulation, killer exclusion, and target record clearing; only broadcast once each time; native /Python results and ownership consistent |
| CPP02 | CPP-004 | Existing players, new players, spectators, disconnection and reconnection; dual client | No team, empty team, same number of players, invalid and inactive players; the selection result is consistent with the original team copy |
| CPP03 | CPP-005、CPP-006 | Default and coverage quantities, name pool exhaustion, adding or removing robots, and cutting images | Cover priority, random call and exchange removal semantics, Controller/Pawn consistent initialization and destruction order; retain original baseline restrictions such as death animation interruption |
| CPP04 | CPP-007、CPP-008 | Empty, partially occupied, full, claimed birth point; enemy or friend, bystander, rebirth after real death | Return candidates, fallback order and native claim behavior are consistent; contention for the same birth point and actual landing point are correct |
| CPP05 | CPP-009、CPP-010 | Empty slots, full slots, positive and negative switching, repeated picking, templates and instances into packages; dual clients | Native RPC, equipment switching, quantity, ownership and copy are consistent; the real call chain is only executed once |
| CPP06 | CPP-011 | Failed/successful issuance, re-entry during the cooling period, end of cooling, re-checking on the refresh table, destruction; dual client | Available marking, timing, re-picking, copying and performance are consistent; the native timer is cleaned correctly, and the refresh station blueprint has been returned and passed |
| CPP07 | CPP-012、CPP-013 | Different players/channels/locations, asynchronous reordering, failure, unlabeling, continuous display, destruction and reconstruction | The display order, cancellation relationship, quantity, and duration are consistent with the object life cycle; there is no repeated monitoring, repeated display, or post-destination callbacks, and the return of reward controls has passed. |
| CPP08 | CPP-014 | No options, single/multiple options, default/specified controls, target customization payload, actual interaction; dual clients | Options, indicators, event targets, predictions, and authoritative results are consistent; existing Explorer interactive regression passes |
| CPP09 | CPP-015 | Actual Escape input, opening/closing menus, repeat requests, cutting and rebuilding | UI The layer, input pause/resume, trigger times and cleanup are consistent; the native interface is still loading normally |

The default design of the first batch is to retain the native message registration and logout of the three processors, and add event entries with clear types in the four business callbacks of consecutive kills, combos, assist damage, and assist kills. The native implementation is retained as an explicit comparison mode, and the Python mode takes over the rules and their status. Exceptions are recorded as failures, and native rules cannot be executed after exceptions to cause repeated settlement. In the initial stage, an independent process is used to compare the two modes, and the stateful switching rules during operation are not included in the default acceptance.

<a id="另外15个需要先验证入口或运行条件的候选"></a>

## In addition 15candidates who need to verify the entry or operating conditions first

The following candidates are not eligible for the 9 batch above. You can select all or specified numbers when confirming; once selected, the entrance prototype and applicable scenario verification are the work within the candidate batch. When the entrance is not established, the failure evidence and specific reasons for the obstruction are retained.

| No. | Native function group and proposed migration rules | Problems to solve first | Compare key points |
| --- | --- | --- | --- |
| CPP-016 | Initial attribute table application for LG `UInventoryFragment_SetStats::OnInstanceCreated` | Fragments are Instanced native objects, and the current base class does not declare Blueprintable; first confirm the event carrying method and CDO fragment replacement range | Actual instance creation, individual tag stacks, duplicate creation, rigging and copying; definition data remains |
| CPP-017 | Consumption rules for LG `ULyraAbilityCost_ItemTagStack::CheckCost`, `ApplyCost` | Original signature contains ActorInfo pointer, capability handle, and mutable failure tag; requires context snapshot, explicit results, and native writeback | Adequacy/insufficiency of actual equipment skills, quantity truncation, failure label, prediction, and server deduction only once |
| CPP-018 | Consumption rules for LG `ULyraAbilityCost_PlayerTagStack::CheckCost`, `ApplyCost` | Same as above, and confirm PlayerState access and native authority deduction entrance | Player Tag Stack, Dead Player, Respawn, Replacement Pawn, Dual Client Results |
| CPP-019 | Native orchestration of LG `ULyraGameplayAbility_Jump::CanActivateAbility`, `CharacterJumpStart`, `CharacterJumpStop` | Distinguish the existing jump blueprint logic from the native parent class; first verify the native virtual, GAS context and end entry | True input, landing, cancellation, death/rebirth and prediction; mobile components continue to be implemented natively |
| CPP-020 | Arrangement of LG `ULyraGameplayAbility_Death::ActivateAbility`, `EndAbility`, `StartDeath`, `FinishDeath` | Native GAS The callback sequence of termination, blocking, cancellation and health components must be observed and compared first | Real damage to death, self-destruction, repeated notifications, cancellation, rebirth, dual clients; cannot just look at Python callback times |
| CPP-021 | LG `ULyraGameplayAbility_Reset::ActivateAbility` Reset Process | native virtual and actual Reset call chain, capability end and Pawn destruction sequence | Player and bot resets, protected abilities, retriggers, actual new Pawn and ownership |
| CPP-022 | LG `ULyraFrontendStateComponent`’s OnExperienceLoaded, FlowStep and other startup decisions | FControlFlowNodeRef, account initialization and session callback cannot be directly assumed to be reflective; retain the native asynchronous handle and cancellation mechanism | Offline startup, initialization success/failure, joining session success/failure, cancellation, control destruction; online service results are recorded separately |
| CPP-023 | LG `ULyraControllerComponent_CharacterParts`’s Add/Remove, OnPossessedPawnChanged arrangement | Part handles and source enumerations require clear interfaces; distinguish production parts from cheat/development configurations | Pawn Replace, same as Pawn Notify, add, delete, duplicate and destroy; component Actor, grid and copy retained |
| CPP-024 | Mode selection for LG `ULyraHeroComponent::DetermineCameraMode` | Currently, it is the native delegation entrance; the skill owner handle and camera mode life cycle are kept in the native layer first. | Skill Camera Priority, Default Mode, Missing Pawn/Data, End Recovery; does not migrate per-frame camera blends and collisions |
| CPP-025 | LG `ULyraHUDLayout` controller disconnection prompt strategy | Platform user ID, device ID and device mapping require native snapshots; real hardware input requires applicable operating environment | Own/other player devices, re-pairing, multi-controllers, repeated notifications, disconnect/recovery and prompt destruction; simulated testing separate from hardware results |
| CPP-026 | LG `ULyraReplaySubsystem`’s CleanupLocalReplays, OnEnumerateStreamsCompleteForDelete, OnDeleteReplay Retention Policy | Native StreamInfo, asynchronous streams and deletion callbacks need to be adapted; only use dedicated temporary test recordings | Keep marks, sorting, recording, quantity boundaries, re-query after deletion once, stop on failure; do not operate the user's existing recordings |
| CPP-027 | Selection rules for LG `ULyraAudioMixEffectsSubsystem::ApplyDynamicRangeEffectsChains`, `ApplyOrRemoveLoadingScreenMix` | Native bus, Submix, World life cycle retention; confirm change events and resource delivery | HDR/LDR Overlapping items, loading interface switching, repeated applications, missing resources and destruction; parameter checking is separated from actual sound verification |
| CPP-028 | LG `ULyraTeamSubsystem::CanCauseDamage`’s self-damage/team/no-team rules | There is currently no UFUNCTION mark. It is necessary to provide a clear query/decision entry, and let the native damage call chain actually pass through this entrance; clarify the boundaries of performance and authority | Self, same team, enemy team, no team and with/without ASC, invalid target, actual damage and prediction are consistent |
| CPP-029 | Attribute constraints of TA `UTopDownArenaAttributeSet::ClampAttribute` | Occurred in GAS attribute change, the original signature contains variable float reference; first verify the read-only input, numerical return and native write-back entry | Bomb quantity/capacity/range, movement speed upper and lower bounds, capacity changes, real bomb consumption refund and dual local players |
| CPP-030 | LG `ALyraGameMode::GetPawnDataForController`, `GetDefaultPawnClassForController_Implementation`, `ControllerCanRestart` Selection/Permission Section | Coupled with Experience ready, native parent class and Pawn initialization; only dismantle the rules and retain the real generation and initialization | PlayerState Data priority, Experience default and AssetManager Default fallback, not ready/missing data, real person/robot, rebirth permission and actual implementation |

<a id="保留的原生职责"></a>

## Reserved native responsibilities

The following responsibilities continue to be called by Python. For specific documents, please see the reason for each item in the source code ledger.

| Responsibilities | reserved range |
| --- | --- |
| Engine and Binding | UObject/Reflection, GC, CPython Embedding and Transformation, Common Plugin Infrastructure |
| Online with GAS | RPC shell, replication and FastArray, sub-object replication, prediction, capability and task scheduling, attribute storage and execution base |
| Roles and real-time computing | Movement, Collision, Physics, Animation, Per-Frame Camera Solving, Ray/Spread/Hit, Per-Frame Input Correction and Aim Assist |
| Loading and object management | Experience/asset asynchronous loading, timer and native handle, component Actor and equipment instance creation, invalidation and destruction mechanism |
| Interface and platform | UMG Layout, Slate Rendering, CommonUI Infrastructure, device/account/setting persistence and video streaming implementation |
| sound and performance | Audio rendering and assets, Niagara, animation and mesh implementation; migrated BP orchestration continues |
| Statements and tools | Data assets, interfaces, enumerations/structures, tags, module entries, Editor, testing and development/cheating tools |

Conditional candidates can break out specific rules, but the entire native system cannot be counted as a migration scope. Multi-platform, Shipping/DebugGame, any dynamic class replacement and stronger hot reload independent planning are not included in this default list.

The following placeholders or unenabled implementations are also not considered migration results:

- The business entity of `LyraAbilityCost_InventoryItem.cpp` is located at `#if 0`, and CheckCost currently returns false.
- Returns true after `ULyraPlayerSpawningManagerComponent::ControllerCanRestart` is currently TODO; it is different from the GameMode method for CPP-030.
- `UTDM_PlayerSpawningManagmentComponent::OnFinishRestartPlayer` is currently empty.
- Empty module entry points, type/configuration-only source code, and declaration shells will continue to be retained.

<a id="确认后的执行流程"></a>

## Execution process after confirmation

1. Establish new phase progress and `CppAcceptance` ledgers according to the confirmation number, and freeze each batch of functions, configurations, dependencies and target environments. Preserve the original source code fingerprint of this manifest. Append numbers and reasons when additional candidates are found, and do not silently expand confirmed batches.
2. Apply versioned patches or adapters to tagged isolation projects. Lyra Dedicated C++, Python, blueprint generator and ledger belong to Examples, and the main library saves necessary general binding changes, verification entries and Demos pointers. The official Lyra and Engine reference source code remain intact.
3. First verify the interface and the original result, then replace the rules, perform targeted Python inspection and actual UE native /Python comparison. Record native messages, parameters/returns, authoritative results, replication, timing and exit cleanup; failure records and corresponding inputs are retained. Behaviors or life cycle conditions that the original version does not meet are listed as native baseline issues, and the comparison results are not rewritten, nor are they mixed into rule migration sign-offs.
4. When the native declaration or implementation changes, incrementally compile the affected modules, retaining the exact source code and binary correspondence; only reuse the matching binary when changing Python. Only one UE/build verification process is run at a time, and the frozen input is not changed while the native process is alive.
5. Each batch of regressions affects callers, inheritance, configuration and existing blueprint dependencies. Shared interface changes are expanded to the affected matrix; when a version or stage is completed, the corresponding actual packaging, visible operation, and life cycle acceptance are performed. Full builds or Cook are not routinely performed.
6. After passing the actual running acceptance, submit and push the Examples, and then submit and push the verification entry and Demos pointer of the main library. Check the remote submission and the matching of the two warehouses. The original 6 address updates have been submitted and pushed according to this round of instructions, corresponding to Examples `3e9c68f` and the main database `d00bee7`.
7. Use the candidates who actually passed the new stage to count the degree of completion. When only passing source code inspection, entry prototype or test simulation, the status remains as partially completed; the original 246 blueprint candidates and 22 acceptance items will not be rewritten.

The existing quarantined Lyra Hero initialization patch continues to be a recorded prerequisite; the native NetShooter difference remains as recorded and is not mixed with the rule migration in this list.

<a id="当前执行范围"></a>

## current execution scope

Confirmed CPP-001 to CPP-015, advancing in order from CPP01 to CPP09. 2026-11-02 After the user replies “Go ahead”, CPP-016～018 are included in the second phase, see [Phase 2 Progress] (cpp_extended_batches.json). Subsequently, user requirements continued to advance, and CPP-019~030 were all included and completed, see [Remaining Batch Acceptance Progress] (cpp_remaining_batches.json). Ordinary interface adaptation, directional verification and submission push of this batch are continuously executed according to the confirmed scope.

2026-11-02 has completed the read-only entry and asset pre-check of CPP-016～018, see [Next round batch plan] (CPP16_18_PREFLIGHT_REVIEW.md) and [Pre-check evidence] (NativeGameplay/CPP16-18-preflight.json). The GameplayTag structure key read restriction of the initial attribute table was found, and there is no player tag consumption configuration in this definition scan. This pre-inspection is not equivalent to business replacement or operational acceptance, and does not change the confirmed scope and completion count of the first round.

Related records:

- [File-by-file source code and candidate function ledger](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/cpp_source_inventory.json)
- [C++ Batch Progress](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/cpp_batches.json)
- [Completed original blueprint migration acceptance](ACCEPTANCE_REVIEW.md)
- [Original Blueprint List and Incremental Regression Agreement](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/batches.json)
- [Existing Mixin Call and Lifecycle Boundaries](https://github.com/Arcueid77/UnrealEnginePython5/blob/dev/release-1.0.0/docs/Mixin_Call_Lifecycle_Matrix.md)
- [Existing message adaptation and subscription rules](https://github.com/Arcueid77/UnrealEnginePython5/blob/dev/release-1.0.0/docs/Runtime_Subscriptions_API.md)
- [Existing Isolated Hero Initialization Patch](NativeFixes/README.md)

2026-11-02 The three selected groups in the second phase have been completed: CPP-016 Initialization, CPP-017 Item consumption is replaced and accepted according to production; CPP-018 Player consumption is accepted according to the independent fixture and network life cycle capabilities. The original configuration consumer is 0 and is not counted as production replacement. See [CPP11 Ledger](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP11-acceptance.json) and [CPP12 Ledger](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP12-acceptance.json). In the first stage, CPP09 still retains the real window Escape/Menu input to be accepted, and CPP-019～030 to continue to be selected.

2026-11-02 The user clearly requested “continue to advance until all are completed”, and the remaining CPP-019~030 all enter the execution scope, see [Remaining Batch Progress] (cpp_remaining_batches.json). CPP13 jumps have passed 12 context boundaries and dual-client 28 native input/prediction/landing verifications. The death/rebirth linkage verification is reserved for the following CPP14 and will not be counted in advance for full acceptance of the group. The user has chosen not to operate the desktop yet, so actual window input for CPP09 remains pending while the rest of the migration continues.

2026-11-02 CPP13～15 Accepted: Jump's death cancellation/new Pawn linkage 4 example, death matrix 20 example, self-destruction and protected ability 4 example, original Arena death two strategies, and native Reset network12 cases all passed. Native classes cannot be directly hooked to the current mixin. Reset uses the blueprint strategy object managed by World; retains the native GAS context, event load, asynchronous tasks and replication. The remaining CPP-022~030 continue to execute, and the CPP09 desktop input continues to be done according to the user's selection.

2026-11-03 CPP16～18 has been accepted and set as default: front-end 70 group, appearance 28 group, camera 8 group parameter check, native /Python actual operation and default startup all passed. The appearance is supplemented by dual client 4 native resets, 8 independent mesh/part observations, and the client is released after restoring the original parts; the camera verifies the real skills and completes the recovery. The front-end online service results have not been measured, and the success/failure and cancellation strategies are retained as parameters and native callback fixture evidence. The remaining CPP-025~030 continue to be executed.

2026-11-03 CPP19～24 has been accepted and set as default, covering the last CPP-025～030:

- Device prompts: 56Group parameter boundaries, native /Pythonactual device callbacks, user filtering, duplicate notification merging and next frame processing. The callback parameters are provided by the fixture, and the real handle is not plugged in or out; the native weak reference, dialog box and delegate life cycle continue to be retained.
- Recording retention: 132 group parameter boundary, 0/1/2/5 retained number of temporary memory streams, re-query after native deletion, failure stop and cleanup. The reserved/recording flag is checked according to parameter boundaries; it does not touch the user's existing recordings and does not claim actual gameplay recording or playback. Python explicitly rejects negative numbers to preserve configuration. The remaining 5.8.0 memory stream module in the current engine directory is not loaded or registered, and only a compilation unit of the current 5.8.1 source code is built into the isolation project; the Engine manifest and binary remain intact.
- Audio selection: 52 group parameter boundaries, native HDR/LDR and loaded mix calls, repeat call status and resource array checks. Audible sound output has not been measured.
- Team damage: 256Group parameter boundary, native /Pythonactual damage of the same team and the enemy team, 4no blood deducted for the same team and 10points deducted for the enemy team in online comparisons, dual client 8 independent blood volume observation. The final default configuration was also observed through the original pistol's 4 client predicted shots, consistent prediction key/hit data, and 8 damage copies.
- Arena attributes: 48 group parameter boundaries; native, Python and final default three runs each include two local players, 16 real GAS attribute clamping and original bomb input, repeated input will not be deducted, and will be destroyed and returned. The fixture first writes and restores attributes, and then verifies the original input phase separately; in-process Slate user initialization does not count desktop input.
- Generate permission: 56Group parameter boundaries, player data priority, Experience fallback, real person/robot license native /Python Actual results are consistent; 4Network native Reset provides dual client 8 independent new Pawn classes and ownership observation.

A total of 600sets of boundary inspections, 4authoritative tests for each of the two groups of networks, and 16independent client observations passed. Finally, the default front-end, generation, dual local player input and original pistol cross-return passed; 51 startup selection check passed. The incremental build only involves three compilation units of LyraGame, one compilation unit of TopDownArena and the LyraGame reflection head; the successful header file and the first two compilation units are reused when correcting the fixture implementation. SDK, bridge library, Engine and reserved CPP09 verify that the project has not been rebuilt or modified, and 972 protected input fingerprints are reviewed consistently. No full engine build, Cook/packaging, multi-platform or real sound/device acceptance has been performed.

At the end of the above third phase, it has been confirmed that all items 30 have been implemented, and the real input of CPP09 still needs to be accepted. The final gap was filled in 2026-11-05; currently, 30 items are accepted according to their respective scopes, among which CPP-018 is the capability acceptance of consumers with zero original configuration. The six sets of independent ledgers are shown in [CPP19](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP19-acceptance.json) to [CPP24](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP24-acceptance.json).
