"""Source-bound call/lifetime evidence for the exact original ability criterion.

Rechecks saved native reports only. Historical SDKs remain historical; this
tool cannot launch Unreal, accept packaged behavior, or accept all gameplay.
"""
import ast
import importlib.util
from pathlib import Path
import re
import subprocess

from audit_ability_identity_acceptance import (execute_gate, policy_modules,
    process_rows, report_dependency_guard, runtime_guards)
from audit_effects_match_acceptance import closure
from audit_ui_failure_cancellation_acceptance import report_pin, source_guard
from audit_ui_navigation_acceptance import index_hashes, key, read, sha

REQUIREMENT = ('Supported ability tasks, delegates, cancellation and latent boundaries '
               'have call/lifetime regressions; unsupported signatures fail explicitly.')
A, C, W = 'uep_lyra_abilities.', 'uep_lyra_characters.', 'uep_lyra_weapons.'
SPECS = (
    (19, 'Differential03'), (19, 'SharedWidget01'), (19, 'ADSStandalone01'), (19, 'Differential02'),
    (21, 'Differential05'), (23, 'Differential02'), (24, 'Differential03'),
    (26, 'PostFamily-pistol-Standalone01'), (26, 'PostFamily-rifle-Standalone01'),
    (26, 'PostFamily-shotgun-Standalone01'), (26, 'NetShooterStandalone01'),
    (32, 'Elimination03'), (32, 'ControlPoint01'), (33, 'Differential02'), (34, 'Differential01'),
    (36, 'Differential02'), (38, 'Lifecycle03'), (38, 'ResetDifferential02'),
    (54, 'Differential04'), (55, 'Differential02'), (56, 'Differential01'), (60, 'Differential04'),
    (66, 'Lifecycle03'), (66, 'Standalone04'), (68, 'Differential01'), (70, 'StandaloneRegression02'),
    (75, 'Differential03'), (78, 'Differential04'), (79, 'Differential04'), (80, 'Differential05'),
    (88, 'Differential02NativeTeams'), (92, 'Differential07NativeGASEnds'),
    (95, 'AbilityRuntime03NativeViewTarget'), (20, 'Network01'), (51, 'Network01'),
    (188, 'Death01Affected'), (82, 'Differential03'),
)
SPECIAL_POLICIES = {
    A + 'widget_contract': [A + 'widget_lifecycle'],
    A + 'auto_respawn_lifecycle_contract': [A + 'auto_respawn_activation_mixin'],
    A + 'auto_respawn_reset_contract': [A + 'auto_respawn_activation_mixin'],
    A + 'dash_tasks_lifecycle_contract': [A + 'dash_tasks_mixin'],
}
# Each production factory/latent/timer site must have its own related native run.
FAMILIES = (
    (A+'ads_mixin', (19,'ADSStandalone01'), ('AbilityTask_WaitInputRelease',)),
    (A+'autoreload_mixin', (23,'Differential02'), ('AbilityTask_WaitDelay',)),
    (A+'dash_tasks_mixin', (66,'Lifecycle03'), ('AbilityTask_ApplyRootMotionConstantForce','AbilityTask_PlayMontageAndWait')),
    (A+'death_mixin', (21,'Differential05'), ('AbilityTask_WaitDelay',)),
    (A+'emote_mixin', (19,'Differential03'), ('AbilityTask_PlayMontageAndWait',)),
    (A+'grenade_activation_mixin', (75,'Differential03'), ('AbilityTask_PlayMontageAndWait',)),
    (A+'hero_heal_mixin', (24,'Differential03'), ('AbilityTask_PlayMontageAndWait','AbilityTask_StartAbilityState','AbilityTask_WaitInputPress')),
    (A+'jump_mixin', (19,'Differential02'), ('AbilityTask_StartAbilityState','AbilityTask_WaitInputRelease')),
    (A+'melee_activation_mixin', (68,'Differential01'), ('AbilityTask_PlayMontageAndWait',)),
    (A+'melee_trace_mixin', (70,'StandaloneRegression02'), ('AbilityTask_ApplyRootMotionConstantForce',)),
    (A+'quickslot_mixin', (20,'Network01'), ('AbilityTask_WaitGameplayEvent',)),
    (A+'reload_magazine_mixin', (26,'PostFamily-pistol-Standalone01'), ('AbilityTask_PlayMontageAndWait','AbilityTask_WaitGameplayEvent')),
    (A+'spawn_effect_mixin', (33,'Differential02'), ('AbilityTask_PlayMontageAndWait','AbilityTask_WaitDelay')),
    (A+'widget_held_mixin', (32,'Elimination03'), ('AbilityTask_StartAbilityState','AbilityTask_WaitInputRelease','AsyncAction_PushContentToLayerForPlayer')),
    (A+'widget_pressed_mixin', (34,'Differential01'), ('AsyncAction_PushContentToLayerForPlayer',)),
    (C+'death_started_mixin', (60,'Differential04'), ('Delay',)),
    (C+'hero_default_death_mixin', (188,'Death01Affected'), ('Delay',)),
    (C+'inventory_wait_mixin', (54,'Differential04'), ('DelayUntilNextTick',)),
    (C+'possessed_mixin', (55,'Differential02'), ('AsyncAction_ExperienceReady',)),
    (C+'team_listener_mixin', (51,'Network01'), ('AsyncAction_ObserveTeamColors',)),
    (C+'visibility_mixin', (56,'Differential01'), ('DelayUntilNextTick',)),
    (W+'grenade_begin_mixin', (80,'Differential05'), ('K2_SetTimer',)),
    (W+'grenade_hit_mixin', (82,'Differential03'), ('K2_ClearAndInvalidateTimerHandle',)),
    (W+'netshooter_ability_mixin', (95,'AbilityRuntime03NativeViewTarget'), ('AbilityTask_PlayMontageAndWait',)),
    (W+'weapon_ability_fire_mixin', (92,'Differential07NativeGASEnds'), ('AbilityTask_PlayMontageAndWait','K2_SetTimer')),
    (W+'weapon_actor_begin_mixin', (88,'Differential02NativeTeams'), ('AsyncAction_ObserveTeamColors',)),
)
TIMING_APIS = {'Delay','RetriggerableDelay','DelayUntilNextTick','K2_SetTimer','K2_SetTimerDelegate',
               'K2_ClearTimer','K2_ClearAndInvalidateTimerHandle'}


def require(value, message):
    if not value:
        raise ValueError(message)


def source_inventory(sources):
    """Reject added factories/boundaries without an explicit native family."""
    actual = {}
    for module, source in sources.items():
        apis = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                match = re.search(r'(AbilityTask_\w+|AsyncAction_\w+)$', node.value)
                if match:
                    apis.add(match[1])
                elif node.value in TIMING_APIS:
                    apis.add(node.value)
        if apis:
            actual[module] = apis
    expected = {module:set(apis) for module, _, apis in FAMILIES}
    require(actual == expected, 'Unreviewed/missing ability factory,latent or timer site')
    return [dict(module=module, apis=sorted(actual[module]), native_spec=list(spec)) for module,spec,_ in FAMILIES]


def selected_record(migration, batch, name):
    path, = (migration/'Acceptance').glob(f'{batch:02}-*.json')
    ledger = read(path)
    records = [r for r in ledger.get('runs',ledger.get('native_runs',[]))
               if Path(r['directory']).name == name and (batch != 20 or '20261016-quickslot/' in r['directory'].replace('\\','/'))]
    require(len(records) == 1, 'One exact native lifetime record required')
    return path, ledger, records[0]


def contract_arguments(arguments, scripts):
    args = list(arguments)
    if len(args) > 1 and Path(args[1]).name == 'jump_contract.py':
        require(Path(args[1]).resolve() == (scripts/'uep_lyra_abilities/jump_contract.py').resolve(), 'Unexpected legacy Jump contract path')
        args = [args[0], '-m', A+'jump_contract', *args[2:]]
    require('-m' in args, 'An explicit pure lifecycle contract module is required')
    return args


def native_log(path):
    text = Path(path).read_text(encoding='utf-8-sig')
    require(not any(v in text for v in ('Traceback','Ensure condition failed','Fatal error')) and
            not re.search(r'Log\w+:\s*Error:', text), 'Unexpected native lifecycle diagnostic')
    require('Goodbye Python' in text and 'Log file closed' in text and
            text.index('Goodbye Python') < text.rindex('Log file closed'), 'Native lifecycle shutdown ordering differs')
    return dict(file=Path(path).name, sha256=sha(path), native_interpreter_and_log_closed=True)


def scope_provenance(repo, parent):
    rows = []
    for relative in ('Content/Scripts/uep_runtime/__init__.py','Content/Scripts/uep_runtime/subscriptions.py'):
        old = subprocess.check_output(['git','show',parent+':'+relative],cwd=repo)
        path = repo/relative
        require(old.decode('utf-8-sig').replace('\r\n','\n') == path.read_text(encoding='utf-8-sig').replace('\r\n','\n'),
                'Shared subscription scope differs from the native ledger parent')
        rows.append(dict(path=relative,current_sha256=sha(path),core_parent_commit=parent,
                         historical_native_file_hash_claimed=False,git_parent_source_matches=True))
    return rows


def generic_boundaries(repo, migration):
    rows = []
    for batch, name in ((257,'257-current-native-rpc-delegate-and-editor-latent-rejection.json'),
                        (258,'258-incremental-call-matrix-selection-and-current-delegate-signatures.json')):
        ledger_path = migration/'Acceptance'/name; ledger = read(ledger_path); record = ledger['native_run']
        folder = repo/record['directory']; summary_path = folder/'summary.json'; summary = read(summary_path)
        require(sha(summary_path) == record['summary_sha256'] and summary['status'] == 'passed', 'Pinned current generic boundary summary differs')
        for source in summary['input_hashes']:
            require(sha(source['path']) == source['sha256'].upper(), 'Current generic native input changed')
        if batch == 257:
            require(summary['process']['exit_code'] == summary['external_gate']['exit_code'] == 0, 'Actual native rejection/gate exit differs')
            require(sha(folder/'rejection.json') == record['report_sha256'] and sha(folder/'rejection.log') == record['log_sha256'], 'Pinned native rejection payload differs')
            contract = repo/'Validation/UEP58Host/Tests/mixin_rejection_contract.py'
            spec = importlib.util.spec_from_file_location('_uep_lifetime_rejection_gate',contract)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            result = module.validate(read(folder/'rejection.json'),(folder/'rejection.log').read_text(encoding='utf-8-sig'))
            processes = [summary['process']]
        else:
            require(summary['selected_test_names'] == ['delegate-broadcast','signature-standalone'] and
                    not summary['full_matrix_executed'] and len(summary['tests']) == 2, 'Exactly two current generic call cases required')
            require([r['name'] for r in summary['tests']] == summary['selected_test_names'], 'Generic native selection/report order differs')
            for test, pinned in zip(summary['tests'],record['tests']):
                path = Path(test['report']); report = read(path)
                require(test['status'] == report['status'] == 'passed' and test['process']['exit_code'] == 0 and
                        sha(path) == pinned['report_sha256'] and sha(path.with_suffix('.log')) == pinned['log_sha256'], 'Pinned generic native report/exit differs')
                native_log(path.with_suffix('.log'))
                if test['name'] == 'delegate-broadcast':
                    require(report['signals'] == [11,22,33] and all(report[k] for k in ('empty_delegate','rejected_parameter','recovery','no_late_delivery')),
                            'Actual native delegate delivery/unbind proof incomplete')
                else:
                    require(report['same_class'] and len(report['supported']) == 7 and
                            [r['profile'] for r in report['rejected']] == ['BadSignature','NonConstOutputs','StaticFunction'], 'Native supported/rejected signature matrix differs')
            result = dict(status='passed',native_delegate_delivery_and_unbind=True,supported_signature_cases=7,rejected_signature_profiles=3)
            processes = [r['process'] for r in summary['tests']]
        rows.append(dict(batch=batch,ledger=ledger_path.relative_to(repo).as_posix(),ledger_sha256=sha(ledger_path),
                         directory=record['directory'],summary_sha256=sha(summary_path),native_pids=[p['pid'] for p in processes],
                         referenced_native_processes=len(processes),semantic_gate=result))
    return rows


def inspect(repo, current, initial):
    repo = Path(repo).resolve(); migration = repo/'Demos/UEPLyraIntegration/Migration'; scripts = migration.parent/'Overlay/Content/Scripts'
    identity_path, = (migration/'Acceptance').glob('256-*.json'); identity = read(identity_path)['review']
    candidates = [r for r in initial['assets'] if r['version'] == '0.11.0']
    require(len(candidates) == 37 and [r['path'] for r in candidates] == [r['asset'] for r in identity['candidates']], 'Exact original ability/character/weapon scope differs')
    require([(r['path'],r['version']) for r in current['assets']] == [(r['path'],r['version']) for r in initial['assets']], 'Original candidate paths/versions changed')
    require(sha(repo/identity['source_candidate_guard']['path']) == identity['source_candidate_guard']['sha256'] and
            sha(repo/identity['native_class_census']['path']) == identity['native_class_census']['sha256'], 'Current native candidate census/source review changed')
    for candidate in identity['candidates']:
        for asset in candidate['asset_guards']:
            require(sha(asset['current_path']) == asset['current_sha256'], 'Current original class/typed transport package changed')
    sources = {r['module']:(scripts/Path(*r['module'].split('.')).with_suffix('.py')).read_text(encoding='utf-8-sig') for r in identity['source_boundary_checks']}
    inventory = source_inventory(sources)
    latent_job = next(j for j in identity['native_execution_runs'] if j['batch'] == 60)
    latent_summary = repo/latent_job['directory']/'summary.json'
    require(sha(latent_summary) == latent_job['summary_sha256'], 'Native shared latent allocator proof changed')
    latent_path = scripts/'uep_lyra_characters/latent_keys.py'; index = index_hashes(read(latent_summary)['hashes'])
    latent_proof = dict(directory=latent_job['directory'],summary_sha256=sha(latent_summary),**source_guard(latent_path,index[key(latent_path)]))
    macro = next(r for r in read(migration/'effects_match_acceptance.json')['review']['native_runs'] if r['contract'].endswith('macro_closure_contract'))
    contexts = dict(macro_native_directory=macro['directory'],macro_native_guard=sha(scripts/'uep_lyra_weapons/macro_policies.py'))
    jobs = []
    for batch, name in SPECS:
        ledger_path,ledger,record = selected_record(migration,batch,name); folder = repo/record['directory']; summary_path = folder/'summary.json'
        require(sha(summary_path) == record['summary_sha256'].upper(), 'Pinned native lifetime summary changed')
        summary = read(summary_path); processes,gates = process_rows(summary); require(len(gates) == 1, 'One independent lifetime gate required')
        args = contract_arguments(gates[0]['arguments'],scripts); contract = args[args.index('-m')+1]
        seeds = SPECIAL_POLICIES.get(contract,policy_modules(contract)); index = index_hashes(summary['hashes'])
        reports = [folder/(peer+'.json') for peer in summary['processes']] if '--directory' in args else [Path(args[args.index('--report')+1])]
        pins = []
        for path in reports:
            require(path.resolve().parent == folder.resolve() and sha(path) == report_pin(ledger,record,Path(record['directory']),path.name), 'Pinned native lifetime report changed')
            pins.append(dict(file=path.name,sha256=sha(path)))
        dependencies = [report_dependency_guard(module,path,index.get(key(path),[])) for module,path in sorted(closure(scripts,[contract]).items())]
        production = runtime_guards(repo,summary,seeds,contexts,latent_proof)
        logs = []
        for process in processes:
            path = Path(next(a.split('=',1)[1] for a in process['arguments'] if a.startswith('-abslog=')))
            require(path.resolve().parent == folder.resolve(), 'Native log escaped the selected lifetime folder')
            logs.append(native_log(path))
        jobs.append(dict(batch=batch,name=name,directory=record['directory'],ledger=ledger_path.relative_to(repo).as_posix(),ledger_sha256=sha(ledger_path),
                         summary_sha256=sha(summary_path),native_pids=[p['pid'] for p in processes],referenced_native_processes=len(processes),
                         report_pins=pins,log_pins=logs,contract=contract,current_gate_sha256=sha(scripts/Path(*contract.split('.')).with_suffix('.py')),
                         report_dependency_guards=dependencies,current_policy_guards=production,semantic_gate=execute_gate(args),
                         subscription_scope_provenance=scope_provenance(repo,ledger['core_parent_commit'])))
    by_spec = {(j['batch'],j['name']):j for j in jobs}
    for row in inventory:
        job = by_spec[tuple(row['native_spec'])]
        require(row['module'] in {p['module'] for p in job['current_policy_guards']}, 'Native lifecycle evidence does not freeze its factory policy')
        row['directory'] = job['directory']
    for module,spec in ((A+'auto_respawn_activation_mixin',(38,'Lifecycle03')),(A+'auto_respawn_listeners_mixin',(36,'Differential02')),
                        (A+'widget_lifecycle',(19,'SharedWidget01')),(C+'team_observer_mixin',(51,'Network01'))):
        require(module in {p['module'] for p in by_spec[spec]['current_policy_guards']}, 'Retained listener/handle lifetime policy missing')
    generic = generic_boundaries(repo,migration)
    return dict(schema_version=1,status='passed',version='0.11.0',criterion=REQUIREMENT,completion_proven=True,
                original_candidates=37,source_identity_ledger=dict(path=identity_path.relative_to(repo).as_posix(),sha256=sha(identity_path)),
                source_api_inventory=inventory,gas_task_classes=sorted({v for r in inventory for v in r['apis'] if v.startswith('AbilityTask_')}),
                direct_async_action_classes=sorted({v for r in inventory for v in r['apis'] if v.startswith('AsyncAction_')}),
                retained_boundaries=[
                    dict(kind='typed-native-message-proxy-and-long-short-delay',native_specs=[[38,'Lifecycle03'],[38,'ResetDifferential02']],message_class='AsyncAction_ListenForGameplayMessage',late_cancelled_continuations=0),
                    dict(kind='weak-native-health-and-EndPlay-function-bindings',native_specs=[[36,'Differential02']]),
                    dict(kind='original-Dash-Kismet-Delay-and-montage-root-task',native_specs=[[66,'Standalone04'],[66,'Lifecycle03']]),
                    dict(kind='native-UIExtension-handles-and-pending-widget-proxies',native_specs=[[19,'SharedWidget01'],[32,'Elimination03'],[32,'ControlPoint01'],[34,'Differential01']]),
                    dict(kind='native-weak-fire-montage-message-and-GAS-owned-timers',native_specs=[[92,'Differential07NativeGASEnds']],original_gas_timer_cleanup_cvar_behavior_preserved=True),
                    dict(kind='Actor-owned-fuse-cleanup-timer-and-weak-destroyed-team-target',native_specs=[[78,'Differential04'],[79,'Differential04'],[80,'Differential05'],[82,'Differential03'],[88,'Differential02NativeTeams']])],
                native_lifetime_runs=jobs,current_sdk_generic_boundaries=generic,native_lifetime_runs_revalidated=len(jobs),
                referenced_native_lifetime_processes=sum(j['referenced_native_processes'] for j in jobs),referenced_current_generic_processes=3,
                old_quickslot_standalone_missing_current_field_excluded=True,quickslot_actual_two_owner_network_lifetime_used=True,
                historical_sdk_versions_remain_historical=True,all_paths_rerun_on_current_sdk=False,new_native_processes_launched_by_review=0,
                production_policy_or_assets_changed=False,cooked_latent_metadata_rejection_accepted=False,
                cpp_compile_executed=False,cook_package_executed=False,full_regression_executed=False,
                full_version_acceptance=False,full_migration_acceptance_proven=False)


def verify_documentation(document, current, initial, repo):
    require(document.get('criterion') == REQUIREMENT and document.get('completion_proven') is True, 'Exact original task/delegate/cancellation/latent criterion required')
    expected = inspect(repo,current,initial)
    require(document['review'] == expected, 'Ability lifetime review differs from the current source-bound native records')
    return {name:expected[name] for name in ('status','criterion','original_candidates','native_lifetime_runs_revalidated',
        'referenced_native_lifetime_processes','referenced_current_generic_processes','new_native_processes_launched_by_review','full_migration_acceptance_proven')}
