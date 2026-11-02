"""Close read-only CPP-016..018 evidence; proposals do not count as migration."""
import argparse
import json
from pathlib import Path
import re
from collect_native_message_acceptance import REPO,load,sha,evidence,require


def collect(root,output):
    root,output=root.resolve(),output.resolve()
    require(root.is_relative_to(REPO/'.build') and not output.exists(),'owned preflight and fresh review ledger required')
    summary=load(root/'summary.json');assets=load(root/'assets.json')
    require(summary['status']=='passed' and summary['error'] is None and assets['status']=='passed','closed read-only preflight failed')
    require(not summary['runtime_acceptance'] and not summary['cpp_compile_executed'] and not summary['assets_saved'] and assets['asset_hashes_unchanged'],'preflight overclaims or authored assets')
    require(not assets['missing_native_parent_tags'],'incomplete native-parent metadata')
    for row in summary['hashes']:require(sha(Path(row['path']))==row['sha256'],'frozen preflight input changed')
    for row in assets['source_assets']:
        require(sha(Path(row['path']))==row['sha256'],'staged definition changed')
        if row['reference_exists']:require(sha(Path(row['reference_path']))==row['reference_sha256'],'official definition changed')
    definitions={row['asset']:row for key in ('items','abilities') for row in assets[key]}
    fragments=[]
    for row in assets['target_fragments']:
        export=definitions[row['owner']]['cdo_export'];p=Path(export['path']);require(sha(p)==export['sha256'],'exported definition changed')
        raw=p.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
        lines=[line for line in text.splitlines() if line.strip().startswith('InitialItemStats=')];require(len(lines)==1,'one initial-stat map per selected definition required')
        values=[dict(tag=tag,count=int(count)) for tag,count in re.findall(r'\(\(TagName="([^"]+)"\),\s*(-?\d+)\)',lines[0])]
        require(values,'native stat map export missing')
        fragments.append({k:v for k,v in row.items() if k!='map_read_error'}|dict(native_exported_initial_stats=values,definition_scope=definitions[row['owner']]['definition_scope']))
    paths=['Inventory/InventoryFragment_SetStats.h','Inventory/InventoryFragment_SetStats.cpp','Inventory/LyraInventoryItemDefinition.h','Inventory/LyraInventoryItemDefinition.cpp','Inventory/LyraInventoryManagerComponent.cpp',
        'AbilitySystem/Abilities/LyraAbilityCost.h','AbilitySystem/Abilities/LyraAbilityCost_ItemTagStack.h','AbilitySystem/Abilities/LyraAbilityCost_ItemTagStack.cpp','AbilitySystem/Abilities/LyraAbilityCost_PlayerTagStack.h','AbilitySystem/Abilities/LyraAbilityCost_PlayerTagStack.cpp',
        'AbilitySystem/Abilities/LyraGameplayAbility.h','AbilitySystem/Abilities/LyraGameplayAbility.cpp','Equipment/LyraGameplayAbility_FromEquipment.h','Equipment/LyraGameplayAbility_FromEquipment.cpp','Inventory/LyraInventoryItemInstance.h','Inventory/LyraInventoryItemInstance.cpp','Player/LyraPlayerState.h','Player/LyraPlayerState.cpp']
    inventory=load(REPO/'Demos/UEPLyraIntegration/Migration/cpp_source_inventory.json');expected={r['path']:r['sha256'] for key in ('runtime_cpp_files','supporting_declarations') for r in inventory[key]}
    sources=[]
    for relative in paths:
        relative='Source/LyraGame/'+relative;p=Path('F:/LyraStarterGame')/relative;digest=sha(p);require(digest==expected[relative],'reviewed source differs from original census')
        sources.append(dict(relative=relative,sha256=digest))
    tracker=load(REPO/'Demos/UEPLyraIntegration/Migration/cpp_batches.json')
    result=dict(schema_version=1,status='preflight_complete_plan_for_review',review_date='2026-11-02',candidates=['CPP-016','CPP-017','CPP-018'],implementation_started=False,accepted=False,runtime_acceptance=False,
        existing_cpp_scope=dict(approved_candidates=tracker['approved_candidates'],implemented_candidates=tracker['implemented_candidates'],accepted_candidates=tracker['accepted_candidates'],cpp09_actual_input_pending=True),
        counts=assets['counts'],registry_blueprints=assets['registry_blueprints'],missing_native_parent_tags=0,original_definition_count=assets['counts']['original_item_definitions']+assets['counts']['original_ability_definitions'],stage_fixture_definition_count=assets['counts']['item_definitions']+assets['counts']['ability_definitions']-assets['counts']['original_item_definitions']-assets['counts']['original_ability_definitions'],
        stat_fragments=fragments,item_and_player_costs=assets['target_costs'],all_selected_asset_hashes_unchanged=True,original_sources_match_census=True,sources=sources,
        binding_findings=[dict(type='TMap<FGameplayTag,int32>',direct_read_supported=False,observed_failures=len(assets['read_failures']),cause='UScriptStruct keys are unhashable; get_property also returns SystemError after the underlying TypeError',planned_solution='copy native map iteration into a typed array of Tag/Count entries; no mutable struct dictionary keys'),
            dict(type='instanced native fragment and cost objects',direct_blueprint_mixin_assumption_validated=False,planned_solution='prototype policy events on existing item-definition and ability Blueprint owners; retain instanced objects and data'),
            dict(type='ActorInfo/spec handles and scalable quantities',expose_raw_pointers=False,planned_solution='native context extraction/evaluation and typed value snapshots; native authority checks and writeback')],
        proposed_batches=[dict(batch='CPP10',candidates=['CPP-016'],scope='initial item-stat application',owner='ULyraInventoryItemDefinition Blueprint owner',native_entry='FLyraInventoryList::AddEntry -> Fragment::OnInstanceCreated',readiness='owner-event prototype and typed stat adapter required before replacement',runtime_examples=['Pistol','Rifle','Shotgun'],retained_examples=['HealthPickup_Unused','NetShooter_PROTO']),
            dict(batch='CPP11',candidates=['CPP-017'],scope='item tag-stack cost decisions',owner='existing ULyraGameplayAbility Blueprint instances',native_entry='ULyraGameplayAbility::CheckCost/ApplyCost -> AdditionalCosts virtual calls',readiness='preserve existing Blueprint policy profiles; explicit native/Python selection before mutation',runtime_examples=['Pistol','Rifle','Shotgun'],retained_examples=['HealthPickup_Unused','NetShooter_PROTO']),
            dict(batch='CPP12',candidates=['CPP-018'],scope='player tag-stack cost capability',owner='dedicated staged LyraGameplayAbility fixture',readiness='no configured consumer found in the selected definition census; fixture acceptance must be distinguished from production replacement',production_replacement_acceptance_available=False)],
        invariants=['Preserve original Fragments and AdditionalCosts object identities, order and values.','Keep Super::CheckCost, fail-fast ordering and hit-only filtering in the original native caller.','Evaluate curves/ability levels and FMath::TruncToInt with native semantics.','CheckCost may run for prediction; only native authority applies tag-stack writes.','Item cost failure tags apply only to insufficient valid items, when the optional output exists and FailureTag is valid. Player cost and missing targets add no new failure tag.','Choose NativeFallback before any business side effects; never execute the native body after a Python business failure.','Keep previously accepted Blueprint Python methods fixed in the C++ comparison.'],
        planned_checks=['real inventory creation through AddItemDefinition and initial tag-stack replication','repeat creation and empty/zero/negative stat fixtures','native/Python cost comparison at below/equal/above quantity','fractional/zero/negative quantities, ability levels and curve-backed fixtures','missing/wrong equipment and missing PlayerState','optional/invalid failure tags and existing caller fail-fast ordering','authority-only deduction, prediction, hit-only and duplicate-input checks','two actual client owners, owner isolation, Pawn replacement and cleanup'],
        stage_policy=dict(preserve_cpp09_stage=True,proposed_independent_stage='.build/LyraValidation/CppGameplayExtended/Stage/Lyra',independent_copies_required=True,hardlinks_allowed=False,cpp_compile_executed=False,cook_package_executed=False),
        retained_attempts=['Preflight01: UE inspection passed; wrapper incorrectly expected an atexit marker before the in-script commandlet marker. Preflight02 checks marker -> successful commandlet -> Python shutdown -> log close.'],
        evidence=[evidence(root/'summary.json'),evidence(root/'assets.json'),evidence(root/'assets.log')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status=result['status'],counts=result['counts'],accepted=False,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.output),indent=2))
