"""Recheck all original0.10 small batches and their current business routing."""
import ast
from collections import Counter
import math
from pathlib import Path
import re

from audit_ability_lifetime_acceptance import selected_record
from audit_effects_match_acceptance import closure
from audit_static_scope_dispositions import relative_asset
from audit_ui_failure_cancellation_acceptance import ledger_record, report_pin, source_guard
from audit_ui_navigation_acceptance import index_hashes, key, read, sha
from audit_widget_actor_lifetime_acceptance import census_scope, source_guards
from audit_world_interaction_acceptance import (NETWORK, combined_hud_job, execute_network_gate,
    network_log, owner_identity, processes)

REQUIREMENT = 'Each small batch passes original-BP/Python comparison without BP fallthrough.'
BASE = '.build/LyraValidation/BlueprintPython/20261027-small-batch-comparison'
H = 'uep_lyra_hud.'
COMBINED = {H+n+'_mixin' for n in ('nameplate_manager','nameplate_source','nameplate','dash_cooldown',
    'respawn_timer','ability_failure','ability_progress','debug_spread','quickbar_slot','reticle_ammo','reticle_host','fire_button')}
PARENT_CALLS = {H+'ability_failure_mixin', H+'respawn_timer_mixin'}


def require(value, message):
    if not value:raise ValueError(message)


def no_original_business(sources, python_classes, coverage):
    """Original calls in reference Profiles remain separate from Python policy."""
    rows=[]; parent_calls=[]
    for module, name in sorted(python_classes):
        tree=ast.parse(sources[module]);classes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name]
        require(len(classes)==1 and name.endswith('PythonProfile') and not classes[0].bases, 'One concrete Python policy class required')
        for owner in tree.body:
            for call in ast.walk(owner):
                if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Attribute) or call.func.attr!='call_mixin_original':continue
                if isinstance(owner,ast.ClassDef) and owner.name!=name and owner.name.endswith('BlueprintFallbackProfile'):continue
                methods=[m for m in classes[0].body if isinstance(m,ast.FunctionDef) and call in list(ast.walk(m))]
                require(module in PARENT_CALLS and len(methods)==1 and methods[0].name=='OnAnimationFinished' and
                    ast.dump(call,include_attributes=False)==ast.dump(ast.parse('self.call_mixin_original("OnAnimationFinished", Animation)').body[0].value,include_attributes=False),
                    'Python business falls through to original Blueprint: '+module)
                parent_calls.append(module)
        rows.append(dict(module=module,python_class=name,original_bp_business_calls=0))
    require(set(parent_calls)==PARENT_CALLS and len(parent_calls)==2, 'Exact two inherited native parent calls required')
    for row in coverage['assets']:
        selected=(row.get('profiles',{}).get('Python',{}).get('python_class') or '').rsplit('.',1)[0]
        if selected not in PARENT_CALLS:continue
        require(not any(e['entry']=='OnAnimationFinished' for e in row['staged_wired_entries']) and
            all(a.startswith('/Script/') for a in row['ancestry'][1:]), 'Native animation parent call reaches authored BP logic')
    return rows


def entry_routes(entries, coverage, scope, source_reviews):
    paths={r['path'] for r in scope};rows={r['asset']:r for r in coverage['assets']};counts=Counter();result=[]
    selected=[r for r in entries['entrypoints'] if r['version']=='0.10.0']
    require(len(selected)==140 and {r['asset'] for r in selected}==paths, 'All140 original0.10 entries required')
    for entry in selected:
        row=rows[entry['asset']];kind=entry['disposition'];counts[kind]+=1
        if kind=='python-routed':
            binding=next((b for b in row['all_ancestor_bindings'] if b['target_class']==entry['native_router']),None)
            require(binding and binding['default_profile']=='Python' and
                    entry['staged_entry']['entry'] in binding['profiles'].get('Python',[]), 'Original entry is not owned by the default Python Profile')
        elif kind=='staged-script-dispatch-forwarder-review':
            dispatch=entry['staged_entry']['calls_python_dispatch']
            methods={m for b in row['all_ancestor_bindings'] for m in b['profiles'].get('Python',[])}
            require(dispatch and set(dispatch)<=methods, 'World dispatch continuation has no Python handler')
        elif kind=='direct-parent-forwarder-review':
            require(entry['node_classes'] and set(entry['node_classes'])=={'K2Node_CallParentFunction'}, 'Retained shell contains local BP business')
        elif kind=='no-connected-execution-business':
            require(entry['reachable_execution_nodes']==0, 'Unreachable/empty entry now has BP business')
        elif kind=='unrouted-business-review':
            matches=[r for r in source_reviews['entries'] if (r['asset'],r['graph'],r['entry'])==
                (entry['asset'],entry['graph'],entry['entry'])]
            require(len(matches)==1 and matches[0]['kind'] in ('typed-native-client-rpc','native-gas-teardown'),
                    'Unreviewed retained BP business entry')
        else:raise ValueError('Unclassified original small-batch entry')
        result.append(dict(asset=entry['asset'],graph=entry['graph'],entry=entry['entry'],disposition=kind))
    require(dict(counts)=={'python-routed':93,'direct-parent-forwarder-review':10,
        'staged-script-dispatch-forwarder-review':28,'no-connected-execution-business':7,'unrouted-business-review':2},
        'Original entry disposition counts changed')
    return dict(original_entries=140,counts=dict(counts),entries=result)


def world_jobs(repo, migration, scripts):
    jobs=[]
    for batch,suffix,gate_name,marker,names in NETWORK:
        directory='.build/LyraValidation/BlueprintPython/'+suffix;folder=repo/directory
        ledger_path=next((migration/'Acceptance').glob(f'{batch:02}-*.json'));ledger=read(ledger_path);record=ledger_record(ledger,directory)
        require(sha(folder/'summary.json')==record['summary_sha256'],'Pinned native world summary differs')
        summary=read(folder/'summary.json');peers=processes(summary,folder);raw={p:read(folder/(p+'.json')) for p in peers};pins=[]
        for peer in peers:
            path=folder/(peer+'.json');log=folder/(peer+'.log')
            require(sha(path)==report_pin(ledger,record,Path(directory),path.name),'Pinned world comparison report differs')
            network_log(log.read_text(encoding='utf-8-sig'),marker)
            pins.append(dict(peer=peer,pid=peers[peer]['pid'],exit_code=0,report_sha256=sha(path),log_sha256=sha(log)))
        owner_identity(raw);gate_path=migration.parent/'Tools'/('validate_'+gate_name+'_network_reports.py')
        modules=['uep_lyra_world.'+name for name in names]
        dependencies=[n.module for n in ast.walk(ast.parse(gate_path.read_text(encoding='utf-8-sig')))
            if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('uep_')]
        index,guards=source_guards(scripts,modules+dependencies,summary)
        jobs.append(dict(directory=directory,summary_sha256=sha(folder/'summary.json'),native_peers=pins,
            policy_modules=modules,current_source_guards=guards,semantic_gate=execute_network_gate(gate_path,folder),
            native_processes=3,_index=index,_stage=Path(peers['server']['arguments'][0]).parent))
    require(sum(j['semantic_gate']['cases'] for j in jobs)==108,'All108 original world comparison rows required')
    return jobs


def menu_gate(report):
    require(report['status']=='passed' and report['error'] is None and
        [r['profile'] for r in report['cases']]==['Python','BlueprintFallback','Python'],'Native menu round-trip incomplete')
    require(not report['menu_class_loaded_before'] and not report['class_preloaded_by_probe'] and
        report['python_clicks']==1 and report['cases'][0]['visible_after_transition'] and
        not report['full_acceptance'] and not report['physical_touch_tested'],'Native lazy menu/reference behavior differs')
    for row in report['cases']:
        require(row['menu_class']=='W_LyraGameMenu_C' and row['same_button_class']=='W_OpenMenuTouchButton_C' and
            row['active'] and row['native_async_layer_push'] and row['native_deactivated'],'Native menu push/pop differs')
    return dict(status='passed',profile_round_trip=3,lazy_native_push_pop=True)


def reticle_gate(report):
    require(report['status']=='passed' and report['error'] is None and len(report['cases'])==6 and len(report['message_cases'])==3,
            'All six native reticle layout/context comparisons required')
    require(Counter(r['kind'] for r in report['cases'])==dict(Pistol=2,Rifle=2,Shotgun=2),'Reticle family missing')
    for row in report['cases']:
        require(row['bp']==row['python']==row['native'] and row['same_class'] and row['automatic_python_ticks']>0,
                'Native/original/Python reticle state or scheduling differs')
        require(all(math.isfinite(v) for v in row['native'].values()), 'Non-finite native reticle state')
    for row in report['message_cases']:
        require(all(row[k] for k in ('local_ads_received','foreign_ads_ignored','ads_animation_noop_preserved','elimination_triggered')),
                'Reticle typed-message comparison incomplete')
    require(report['real_ads_input_tested'] and report['real_equipped_shotgun_tested'] and
        report['native_shotgun_ammo_after']<report['native_shotgun_ammo_before'] and report['repeated_elimination_and_suicide_filter'],
        'Actual native ADS/Shotgun or original elimination branches missing')
    require(not any(report[k] for k in ('full_acceptance','network_acceptance','real_elimination_gameplay_tested','inventory_or_weapon_spread_written')),
            'Reticle comparison claims an unsupported runtime path')
    final=report['reticle_shutdown'];require(final['active_count']==0 and final['scopes_created']==final['scopes_closed'] and not final['errors'],
        'Reticle scope survived native exit')
    return dict(status='passed',layout_context_pairs=6,message_families=3,actual_native_ads_and_shotgun=True)


def closed_job(repo, scripts, directory, report_name, modules, validate, marker):
    folder=repo/directory;summary=read(folder/'summary.json');process=summary['process']
    require(summary['status']=='passed' and process['pid']>0 and process['exit_code']==0 and
        not summary['cpp_compile_executed'] and not summary['cook_package_executed'], 'Native comparison process failed')
    path=folder/report_name;log=path.with_suffix('.log');text=log.read_text(encoding='utf-8-sig')
    require(marker in text and 'Goodbye Python' in text and 'Log file closed' in text and
        not re.search(r'Log\w+:\s*Error:|Traceback|Ensure condition failed|Fatal error',text),'Native comparison diagnostic/shutdown failed')
    index,guards=source_guards(scripts,modules,summary)
    return dict(directory=directory,summary_sha256=sha(folder/'summary.json'),native_processes=1,
        native_peers=[dict(peer='Standalone',pid=process['pid'],exit_code=0,report_sha256=sha(path),log_sha256=sha(log))],
        policy_modules=[m for m in modules if m.endswith('_mixin')],current_source_guards=guards,
        semantic_gate=validate(read(path)),_index=index,_stage=Path(process['arguments'][0]).parent)


def candidate_matrix(scope, dispositions, jobs):
    result=[]
    for candidate in scope:
        row=dispositions[candidate['path']];cls=row['effective_python_class']
        if cls:
            module=cls.rsplit('.',1)[0];related=[j['directory'] for j in jobs if module in j['policy_modules']]
            require(related,'Original candidate has no actual native comparison family: '+candidate['path'])
            result.append(dict(asset=candidate['path'],policy_module=module,native_comparison_directories=related))
        else:
            require(row['disposition']=='retained-native-cpp-touch-parent-forwarder','Unreviewed non-Python candidate')
            result.append(dict(asset=candidate['path'],retained_native_parent_forwarder=True))
    require(len(result)==32 and sum('policy_module' in r for r in result)==30,'All30 Python candidates and two retained shells required')
    return result


def inspect(repo,current,initial):
    repo=Path(repo).resolve();migration=repo/'Demos/UEPLyraIntegration/Migration';scripts=migration.parent/'Overlay/Content/Scripts'
    scope=[r for r in initial['assets'] if r['version']=='0.10.0']
    require(len(scope)==32 and [r['path'] for r in scope]==[r['path'] for r in current['assets'] if r['version']=='0.10.0'],
        'Exact original32 candidate paths/order required')
    document=read(migration/'candidate_dispositions.json');coverage,census=census_scope(repo,migration,scope,document)
    dispositions={r['asset']:r for r in document['candidates']}
    classes={tuple(dispositions[r['path']]['effective_python_class'].rsplit('.',1)) for r in scope if dispositions[r['path']]['effective_python_class']}
    sources={module:(scripts/Path(*module.split('.'))).with_suffix('.py').read_text(encoding='utf-8-sig') for module,_ in classes}
    require(len(classes)==len(sources)==22, 'All22 original Python policy families required')
    policies=no_original_business(sources,classes,coverage)
    entry_ledger=read(repo/document['evidence_paths']['entrypoint_ledger'])
    entry_pin,=[r for r in entry_ledger['input_hashes'] if Path(r['path']).name=='original-entrypoints01.json']
    entry_path=repo/entry_pin['path'];require(sha(entry_path)==entry_pin['sha256'],'Original entrypoint census changed')
    source_reviews_path=repo/document['evidence_paths']['entrypoint_reviews']
    source_review_pin,=[r for r in entry_ledger['input_hashes'] if Path(r['path']).name==source_reviews_path.name]
    require(sha(source_reviews_path)==source_review_pin['sha256'], 'Retained native source review changed')
    routes=entry_routes(read(entry_path),coverage,scope,read(source_reviews_path))
    engine=Path('F:/UnrealEngine/Engine/Source/Runtime/UMG');cpp=engine/'Private/UserWidget.cpp';header=engine/'Public/Blueprint/UserWidget.h'
    require(len(re.findall(r'void UUserWidget::OnAnimationFinished_Implementation\(const UWidgetAnimation\* Animation\)\s*\{\s*\}',cpp.read_text(encoding='utf-8-sig')))==1,
        'Inherited native animation parent implementation changed')
    jobs=world_jobs(repo,migration,scripts)
    combined=combined_hud_job(repo,scripts);combined['current_source_guards']=source_guards(scripts,sorted(sources),read(repo/combined['directory']/'summary.json'))[1]
    combined['policy_modules']=sorted(COMBINED);combined['_stage']=Path(combined['_processes']['server']['arguments'][0]).parent
    jobs.append(combined)
    from audit_widget_actor_lifetime_acceptance import action_touch_job,heal_job
    touch=action_touch_job(repo,migration,scripts);touch['policy_modules']=[H+'action_touch_mixin'];jobs.append(touch)
    heal=heal_job(repo,scripts);heal['policy_modules']=['uep_lyra_world.heal_ability_mixin'];jobs.append(heal)
    from uep_lyra_hud.quickbar_initialization_contract import validate as quickbar_validate
    jobs.append(closed_job(repo,scripts,'.build/LyraValidation/BlueprintPython/20261026-quickbar-initialization/Native03','initialization.json',
        [H+'quickbar_slot_mixin',H+'quickbar_initialization_contract',H+'quickbar_initialization_validation'],quickbar_validate,'UEP_QUICKBAR_INIT_DIFFERENTIAL_PASSED'))
    jobs.append(closed_job(repo,scripts,BASE+'/OpenMenu01','menu.json',[H+'open_menu_mixin',H+'open_menu_validation'],menu_gate,'UEP_OPEN_MENU_DIFFERENTIAL_PASSED'))
    jobs.append(closed_job(repo,scripts,BASE+'/WeaponReticles01','reticles.json',[H+'weapon_reticle_mixin',H+'weapon_reticle_validation'],reticle_gate,'UEP_WEAPON_RETICLE_DIFFERENTIAL_PASSED'))
    from uep_lyra_hud.hud_initialization_contract import validate as hud_validate
    jobs.append(closed_job(repo,scripts,BASE+'/HUDInitialization02','initialization.json',
        [H+n+'_mixin' for n in ('action_touch','dash_cooldown','ability_failure','ability_progress')]+[H+'hud_initialization_contract',H+'hud_initialization_validation'],
        hud_validate,'UEP_HUD_INIT_DIFFERENTIAL_PASSED'))
    matrix=candidate_matrix(scope,dispositions,jobs);assets=[];native_rows={r['asset']:r for r in coverage['assets']}
    for row in matrix:
        if 'policy_module' not in row:continue
        pins=[]
        for value in (row['asset'],native_rows[row['asset']].get('mixin_set')):
            if not value:continue
            relative=relative_asset(value,Path('F:/LyraStarterGame'));path=migration.parent/'Overlay'/relative
            if not path.is_file():path=Path('F:/LyraStarterGame')/relative
            matched=[]
            for job in jobs:
                if job['directory'] not in row['native_comparison_directories']:continue
                records=job['_index'].get(key(path),[]) or [dict(r,path=str(path)) for r in job['_index'].get(key(job['_stage']/relative),[])]
                try:proof=source_guard(path,records)
                except ValueError:continue
                matched.append(dict(directory=job['directory'],**proof))
            require(matched,'Current candidate/transport has no matching executed comparison input: '+value)
            pins.append(dict(asset=value,path=str(path),native_input_guards=matched))
        assets.append(dict(asset=row['asset'],guards=pins))
    for job in jobs:
        for field in list(job):
            if field.startswith('_'):del job[field]
    require(len(jobs)==14 and sum(j['native_processes'] for j in jobs)==33,'Complete original small-batch native evidence set differs')
    return dict(schema_version=1,status='passed',criterion=REQUIREMENT,completion_proven=True,original_candidates=32,
        candidate_census=census,current_python_policy_classes=policies,original_entry_routes=routes,
        retained_source_review=dict(path=source_reviews_path.relative_to(repo).as_posix(),sha256=sha(source_reviews_path)),
        native_parent_callback_source=[dict(path=str(p),sha256=sha(p)) for p in (cpp,header)],
        candidate_comparison_matrix=matrix,current_candidate_asset_guards=assets,native_comparison_runs=jobs,
        native_comparison_runs_revalidated=14,referenced_native_processes=33,new_native_comparison_processes=3,
        world_comparison_rows=108,independent_initialization_candidates=6,cpp_compile_executed=False,cook_package_executed=False,
        full_regression_executed=False,full_version_acceptance=False,full_migration_acceptance_proven=False)


def verify_documentation(document,current,initial,repo):
    require(document.get('criterion')==REQUIREMENT and document.get('completion_proven') is True,'Exact original small-batch criterion required')
    expected=inspect(repo,current,initial);require(document.get('review')==expected,'Recorded small-batch evidence differs from current proof')
    return {k:expected[k] for k in ('status','criterion','original_candidates','native_comparison_runs_revalidated','referenced_native_processes')}
