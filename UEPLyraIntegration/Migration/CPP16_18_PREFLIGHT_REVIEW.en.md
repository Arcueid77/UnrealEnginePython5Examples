[English](CPP16_18_PREFLIGHT_REVIEW.en.md) | [简体中文](CPP16_18_PREFLIGHT_REVIEW.md)

<a id="cpp-016018-接入口预检与分批方案"></a>

# CPP-016～018 Access entrance pre-check and batch plan

2026-11-02. In this round, the entrance, dependencies and verification conditions will be checked first; the game business has not been replaced yet and will not be counted in the migration acceptance. The implementation of the first round of 15group, the acceptance of 14group and the actual input of CPP09 to be accepted shall remain the original records.

The plans and restrictions for pre-checking are retained below. Then the user replied "Go ahead" and these three groups have been selected. The actual execution status can be found in [Phase 2 Progress](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/cpp_extended_batches.json). CPP10 has passed inventory creation, boundary and dual-client acceptance; CPP11’s original item consumption has passed production replacement acceptance; CPP12 has passed independent fixture, dual-client and real rebirth/Pawn replacement capability verification. CPP-018 There are no original configured consumers and are still not counted as production replacements.

<a id="已实际检查的内容"></a>

## What has actually been checked

Reuse the native binary of CPP09 and run the read-only UE command line preflight in the original isolation project. Check the native parent tags of 577 blueprints under the five project content roots, and filter out 46 item/skill definitions: The original Lyra contains 7 items, 37 skills, and 2 previous test fixtures. There are no missing parent tags. This demonstrates configuration coverage, not operational reachability in actual matches.

| candidate | Configure live | Conditions to deal with first |
| --- | --- | --- |
| CPP-016 Initial properties | Each of the 5 item definitions has 1 and SetStats fragments | Native embedded fragments do not directly assume Mixin; GameplayTag as a TMap key cannot be directly converted into a Python dictionary |
| CPP-017 Item consumption | Each of the 5 skill definitions has 1 and ItemTagStack consumption objects. | Native virtual entry, ActorInfo, failed tag writeback and authority deduction require narrow interfaces |
| CPP-018 Player consumption | The PlayerTagStack configuration was not found in this definition scan. | First use independent skill fixtures to verify capabilities; when there are no producers and consumers, they cannot sign for production replacement. |

The 5 group corresponds to Pistol, Rifle, Shotgun, and HealthPickup_Unused, NetShooter_PROTO. The latter two retain their original unused/prototype positioning and will not be counted as normal game acceptance due to the existence of configurations. The consumption configurations of 5 are currently magazine ammunition, quantity 1, no curve, and will be deducted only after non-hit, and the failure label is `Ability.ActivateFail.Cost`. Additional branches must be verified with explicit fixtures and cannot be pretended to be covered by the configuration.

| Items | Magazine capacity/initial ammunition/spare ammunition |
| --- | --- |
| Pistol | 12 / 12 / 48 |
| Rifle | 30 / 30 / 60 |
| Shotgun | 8 / 8 / 16 |
| NetShooter_PROTO | 1 / 1 / 2 |
| HealthPickup_Unused | 1 / 1 / 0 |

The above values are from the native CDO export. 5 direct reads of `TMap<FGameplayTag,int32>` all resulted in a structural key not hashable error, which subsequently exposed `get_property`’s SystemError. The preflight retains the original errors; this round does not mix general binding repairs into business replacement, and priority is given to adding the Tag/Count typed array that maintains the native iteration order.

<a id="建议接入方式"></a>

## Recommended access method

Do not batch replace native embedded objects in existing `Fragments` and `AdditionalCosts` with Blueprint sub-objects. Priority is given to establishing strategy events on existing blueprint owners: item definitions are responsible for initializing strategies, and skill instances are responsible for consuming strategies. The native callback must actually go through the event, and ordinary C++ virtual will not be replaced because Python has a method with the same name.

CPP-016 The real entrance is the inventory `AddEntry(ItemDef)` Called fragment by fragment after creating the instance `OnInstanceCreated`. Get the item definition from the instance, passing the target instance and typed attribute snapshot to the strategy entry that defines the blueprint. Define the class as Const, first verify the constant profile selector and const event bearer, and do not directly assume that variable profile members can be added. The solution has not yet been compiled or run, and needs to be prototyped before the implementation batch.

The real entry of CPP-017/018 is the AdditionalCosts traversal of `ULyraGameplayAbility`. Keep the original signature and ActorInfo/ability handle, parse the target, level, curve and original integer truncation in the native layer, and transfer the value snapshot to the skill blueprint. Python Determine payment and consumption rules, and natively complete the authoritative write-back of legal goals. Native /Python routing is determined before any business side effects; Python Native business must not be executed after failure during execution. The original C++ path is retained as explicit NativeFallback.

Item consumption is only tagged when the target is valid, the quantity is insufficient, the caller provides a failure tag output, and the configuration tag is valid. Missing items are not tagged, and the original implementation of PlayerTagStack does not add a failure tag; both cannot be rewritten uniformly. `Super::CheckCost`. Stop when encountering the first failure. Fees will be deducted only after a hit. Prediction and server permissions will continue to be borne by the original call chain.

<a id="建议分批"></a>

## Recommended in batches

1. **CPP10 / CPP-016**: First verify the event bearer and typed attribute array defined by the Const item, and then replace the initialization loop. Verify initial value and replication with real AddItemDefinition, duplicate creation, empty/zero/negative fixtures and dual clients.
2. **CPP11 / CPP-017**: Integrate consumption decisions on actual weapon skills. Keep the previously accepted blueprint Python method, and only switch to add new C++ rules; check insufficient/equal/sufficient margin, failure label, quantity truncation, hit condition and only deduct once.
3. **CPP12 / CPP-018**: Verification with independent player consumption skill PlayerState, missing target, respawn /Pawn replacement, dual client and authoritative writeback. The ledger distinguishes between "Capacity Fixture Pass" and "Production Replacement", the latter of which currently has no configured consumers.

The original configuration has no curves, quantity boundaries, and hit limits, so these branches are covered by a single column of fixtures. The existing original version restriction of "incorporation of existing item instances into packages has not been implemented" is still listed separately, and this will not be used to expand the initial migration scope.

<a id="工程与回归边界"></a>

## Engineering and Returning to the Boundary

For subsequent prototypes and implementations, use a new independent project copy, and the recommended directory is `.build/LyraValidation/CppGameplayExtended/Stage/Lyra`. Keep the source code, resources and accurate binary of CPP09 so that you can continue the real input and acceptance after unlocking; do not use hard links to share changeable files. Check the actual disk margin when copying, and apply the patch after completing independence and fingerprint verification.

Only incrementally compile modules/units where the compiler dependency report hits. Only the matching binary is reused when changing Python. Return to existing weapons, inventory, and actual affected skills; no routine full builds or Cook. After each batch passes, first submit the push Examples, then submit the push main warehouse and Demos pointer, and check the remote ends of the two warehouses.

Preflight did not save or modify any inspected assets, did not compile C++, did not Cook, did not operate the desktop. The 18 related documents of the official reference source code are consistent with the 10month31day ledger fingerprint. For evidence and complete configuration, see [Pre-inspection ledger](https://github.com/Arcueid77/UnrealEnginePython5Examples/blob/dev/release-1.0.0/UEPLyraIntegration/Migration/NativeGameplay/CPP16-18-preflight.json). The reproducible entrance is the main warehouse `Validation/Run-UEP58NativeStatsCostPreflight.ps1`.
