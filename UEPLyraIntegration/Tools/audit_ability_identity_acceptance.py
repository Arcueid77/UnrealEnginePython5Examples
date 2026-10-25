"""Source-bound original0.11 class identity and native execution boundaries."""
import ast
import contextlib
import io
import json
import re
import runpy
import sys
import warnings
from pathlib import Path

from audit_candidate_dispositions import verify_documentation as verify_candidates
from audit_effects_match_acceptance import closure, historical_source, shape, verify_source
from audit_static_scope_dispositions import relative_asset
from audit_ui_failure_cancellation_acceptance import report_pin, source_guard
from audit_ui_navigation_acceptance import index_hashes, key, read, sha

REQUIREMENT = ('No replacement changes UObject class identity or bypasses the required '
               'authority, prediction or replication checks.')
BATCHES = (19, 20, 21, 22, 23, 24, 25, 27, 29, 32, 33, 34, 38,
           *range(39, 62), 66, 70, 85, 88, 93, 97, 188, 219)
SPECIAL_RUNS = {29: 'Differential02', 70: 'Network09', 88: 'Differential02NativeTeams', 188: 'Network02'}
SPECIAL_POLICIES = {
    'validate_death_network_reports.py': ('uep_lyra_abilities.death_mixin',),
    'uep_lyra_characters.cosmetic_network_contract': ('uep_lyra_characters.cosmetics_mixin',),
    'uep_lyra_characters.death_replication_contract': ('uep_lyra_characters.death_started_mixin',),
    'uep_lyra_abilities.auto_respawn_reset_network_contract': ('uep_lyra_abilities.auto_respawn_activation_mixin',),
    'uep_lyra_weapons.grenade_flight_network_contract': ('uep_lyra_abilities.grenade_activation_mixin', 'uep_lyra_weapons.grenade_detonate_mixin'),
    'uep_lyra_weapons.netshooter_impact_network_contract': ('uep_lyra_weapons.netshooter_ability_mixin', 'uep_lyra_weapons.netshooter_actor_mixin'),
}
NATIVE_FIELDS = {'NetExecutionPolicy', 'NetSecurityPolicy', 'ReplicationPolicy', 'InstancingPolicy',
                 'bReplicates', 'bReplicateMovement', 'bReplicateInputDirectly',
                 'bServerRespectsRemoteAbilityCancellation', 'Role', 'RemoteRole', 'Class', 'SuperClass'}
NATIVE_CALLS = {'SetReplicates', 'SetReplicateMovement', 'SetAutonomousProxy', 'SetRole', 'SetRemoteRoleForBackwardsCompat'}
CLASS_FACTORIES = {'new_class', 'new_blueprint', 'create_blueprint', 'register_class', 'blueprint_create_variable', 'add_function'}


def require(value, message):
    if not value:
        raise ValueError(message)


def selected_runs(migration):
    selected = []
    seen = set()
    for batch in BATCHES:
        ledger_path = next((migration / 'Acceptance').glob(f'{batch:02}-*.json'))
        ledger = read(ledger_path)
        for record in ledger.get('runs', ledger.get('native_runs', [])):
            directory = record['directory'].replace('\\', '/')
            name = Path(directory).name
            if directory in seen or (batch != 19 and '20261016-emote' in directory):
                continue
            if batch in SPECIAL_RUNS:
                if name != SPECIAL_RUNS[batch]:
                    continue
            elif batch != 219 and 'Network' not in name:
                continue
            seen.add(directory)
            selected.append((batch, ledger_path, ledger, record, directory))
    require(len(selected) == 55, 'All fifty-five original native execution-boundary records required')
    return selected


def process_rows(summary):
    require(summary['status'] == 'passed' and summary.get('error') is None, 'Native identity/boundary run failed')
    require(not summary['cpp_compile_executed'] and not summary['cook_package_executed'], 'Expected reused native build records')
    peers = summary.get('processes')
    rows = list(peers.values()) if isinstance(peers, dict) and peers else [summary['process']]
    require(rows and len({row['pid'] for row in rows}) == len(rows) and
            all(row['pid'] > 0 and row['exit_code'] == 0 for row in rows), 'Native peer identities/exits differ')
    gates = list(summary.get('external_gates', {}).values())
    if not gates:
        gates = [summary.get('external_gate', summary.get('validation'))]
    require(gates and all(gate is not None and gate['exit_code'] == 0 for gate in gates), 'Original independent native gate failed')
    if any('--directory' in gate['arguments'] for gate in gates):
        require(isinstance(peers, dict) and set(peers) == {'server', 'A', 'B0'}, 'Actual authority and two native clients required')
    return rows, gates


def execute_gate(arguments):
    """Run only a recorded pure contract/report CLI, preserving caller state."""
    args = list(arguments)
    if args[:1] == ['-B']:
        args.pop(0)
    require(args and ((args[0] == '-m' and args[1].startswith('uep_') and args[1].endswith('_contract')) or
                     (Path(args[0]).name.startswith('validate_') and Path(args[0]).name.endswith('_reports.py'))),
            'Only an explicit pure native-report contract may execute')
    before = sys.argv
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output), warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*found in sys.modules after import of package.*', category=RuntimeWarning)
            if args[0] == '-m':
                sys.argv = [args[1], *args[2:]]
                runpy.run_module(args[1], run_name='__main__')
            else:
                sys.argv = args
                runpy.run_path(args[0], run_name='__main__')
    finally:
        sys.argv = before
    result = json.loads(output.getvalue())
    require(result['status'] == 'passed' and result.get('full_acceptance', False) is False, 'Current raw native contract failed/overclaimed')
    return result


def policy_modules(contract):
    if contract in SPECIAL_POLICIES:
        return list(SPECIAL_POLICIES[contract])
    return [contract.replace('_network_lifecycle_contract', '_mixin').replace('_network_contract', '_mixin').replace('_contract', '_mixin')]


def native_boundary_writes(module, source):
    tree = ast.parse(source)
    dynamic = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            require(not any(isinstance(t, ast.Attribute) and t.attr in NATIVE_FIELDS for t in targets),
                    'Unreviewed direct native execution/type field write: ' + module)
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else None
        require(name not in CLASS_FACTORIES, 'Runtime policy may not manufacture replacement native classes: ' + module)
        require(name not in NATIVE_CALLS, 'Unreviewed direct native execution/replication call: ' + module)
        if name == 'set_property' and node.args and isinstance(node.args[0], ast.Constant):
            require(node.args[0].value not in NATIVE_FIELDS, 'Unreviewed native execution/replication policy write: ' + module)
        elif name == 'set_property':
            dynamic.append(node.lineno)
        if name == 'call_function' and node.args and isinstance(node.args[0], ast.Constant):
            require(node.args[0].value not in NATIVE_CALLS, 'Unreviewed native execution/replication call: ' + module)
    return dict(module=module, native_class_factories=0, literal_execution_or_replication_policy_writes=0,
                dynamic_property_write_lines=dynamic, formal_dynamic_assignment_analysis=False)


def report_dependency_guard(module, source, rows):
    try:
        return dict(module=module, **source_guard(source, rows))
    except ValueError:
        require(rows and module.endswith(('_contract', '_protocol')), 'Unfrozen/changed non-contract report dependency: ' + module)
        return dict(module=module, current_sha256=sha(source), recorded_native_sha256=sorted({r['sha256'].upper() for r in rows}),
                    current_post_exit_contract_reexecuted=True, current_source_matches_historical_input=False,
                    production_runtime_source_equivalence_claimed=False)


def latent_key_extraction(before, after):
    """Only the private three-key allocation may move to the shared allocator."""
    old, new = ast.parse(before), ast.parse(after)
    imports = [n for n in old.body if isinstance(n, ast.Import) and [(a.name, a.asname) for a in n.names] == [('uuid', None)]]
    require(len(imports) == 1, 'One original private UUID import required')
    old.body.remove(imports[0])
    ready = [n for n in old.body if isinstance(n, ast.ImportFrom) and n.level == 1 and
             [(a.name, a.asname) for a in n.names] == [('inventory_ready_mixin', 'ready')]]
    require(len(ready) == 1, 'Original native readiness dependency changed')
    old.body.insert(old.body.index(ready[0]) + 1, ast.parse('from .latent_keys import allocate').body[0])
    expected = ast.parse('ids=set()\nwhile len(ids)<3:ids.add((uuid.uuid4().int & 0x7fffffff) or 1)\nvalues["uuids"]=list(ids)').body
    matches = [n for n in ast.walk(old) if isinstance(n, ast.If) and [shape(v) for v in n.body] == [shape(v) for v in expected]]
    require(len(matches) == 1, 'Exactly the original three private UUID statements required')
    matches[0].body = ast.parse('values["uuids"]=allocate(actor,"inventory-readiness",3)').body
    require(shape(old) == shape(new), 'Readiness changed beyond private Actor-local latent-key allocation')
    return 'same-class-native-calls-and-authority-prediction-replication-branches;only-private-three-key-allocation-extracted'


def runtime_guards(repo, summary, seeds, contexts, latent_proof):
    try:
        return verify_source(repo, summary, seeds, contexts)
    except ValueError:
        scripts = repo / 'Demos/UEPLyraIntegration/Overlay/Content/Scripts'
        files = closure(scripts, seeds)
        require('uep_lyra_characters.inventory_wait_mixin' in files, 'Unreviewed changed native-boundary family')
        index = index_hashes(summary['hashes'])
        proofs = []
        for module, path in sorted(files.items()):
            rows = index.get(key(path), [])
            if module == 'uep_lyra_characters.inventory_wait_mixin':
                before, history = historical_source(repo, path, rows)
                equivalence = latent_key_extraction(before, path.read_text(encoding='utf-8-sig'))
                proofs.append(dict(module=module, current_sha256=sha(path), **history, equivalence=equivalence,
                                   current_allocator_native_proof=latent_proof))
            elif module == 'uep_lyra_characters.latent_keys':
                require(sha(path) == latent_proof['current_sha256'], 'Separately native-tested latent allocator changed')
                proofs.append(dict(module=module, separately_frozen_native_proof=latent_proof))
            else:
                proofs.append(dict(module=module, **source_guard(path, rows)))
        return proofs


def class_rows(initial, coverage, dispositions):
    scope = [row for row in initial['assets'] if row['version'] == '0.11.0']
    require(len(scope) == 37 and len({row['path'] for row in scope}) == 37, 'Exact thirty-seven original0.11 candidates required')
    by_asset = {row['asset']: row for row in coverage['assets']}
    rows = []
    for candidate in scope:
        row = by_asset[candidate['path']]
        source_review = dispositions[candidate['path']]
        retained = source_review['disposition'] in ('retained-empty-native-parent-shell', 'retained-forwarder-inherited-python-parent')
        if retained:
            require(set(source_review['original_entry_dispositions']) <= {'direct-parent-forwarder-review', 'no-connected-execution-business'},
                    'Retained native shell/forwarder contains unreviewed business')
        expected = candidate['path'] + '_C'
        require(row['original_class'] == expected and row['class_identity_preserved'] is True and row['ancestry'][0] == expected,
                'Original native class identity/ancestry differs: ' + candidate['path'])
        router = row.get('native_router_class')
        require(router is None or router in row['ancestry'], 'Inherited router escaped the original native class hierarchy')
        rows.append(dict(asset=candidate['path'], original_class=expected, ancestry=row['ancestry'], native_router_class=router,
                         retained_forwarder=row['retained_forwarder'], class_identity_preserved=True,
                         source_disposition=source_review['disposition'], source_reviewed_retention=retained,
                         effective_policy_modules=sorted({p['python_class'].rsplit('.', 1)[0] for p in row.get('profiles', {}).values()}),
                         mixin_set=row.get('mixin_set')))
    return rows


def inspect(repo, current, initial):
    repo = Path(repo).resolve()
    integration = repo / 'Demos/UEPLyraIntegration'
    migration = integration / 'Migration'
    scripts = integration / 'Overlay/Content/Scripts'
    candidate_path = migration / 'candidate_dispositions.json'
    candidate = read(candidate_path)
    census = verify_candidates(candidate, current, initial, repo)
    census_ledger = read(repo / candidate['evidence_paths']['native_ledger'])
    coverage_path = repo / census_ledger['runs'][0]['directory'] / 'audit.json'
    classes = class_rows(initial, read(coverage_path), {r['asset']: r for r in candidate['candidates']})
    census_stage = Path(read(coverage_path.parent / 'summary.json')['process']['arguments'][0]).parent
    effects = read(migration / 'effects_match_acceptance.json')['review']
    macro = next(r for r in effects['native_runs'] if r['contract'].endswith('macro_closure_contract'))
    contexts = dict(macro_native_directory=macro['directory'], macro_native_guard=sha(scripts / 'uep_lyra_weapons/macro_policies.py'))
    runs = selected_runs(migration)
    _, _, _, latent_record, latent_directory = next(r for r in runs if r[0] == 60)
    latent_summary_path = repo / latent_directory / 'summary.json'
    require(sha(latent_summary_path) == latent_record['summary_sha256'], 'Native death-delay/allocator record changed')
    latent_index = index_hashes(read(latent_summary_path)['hashes'])
    latent_path = scripts / 'uep_lyra_characters/latent_keys.py'
    latent_proof = dict(directory=latent_directory, summary_sha256=sha(latent_summary_path),
                        **source_guard(latent_path, latent_index.get(key(latent_path), [])))
    jobs = []
    for batch, ledger_path, ledger, record, directory in runs:
        folder = repo / directory
        require(sha(folder / 'summary.json') == record['summary_sha256'].upper(), 'Pinned native execution summary changed')
        summary = read(folder / 'summary.json')
        processes, gates = process_rows(summary)
        index = index_hashes(summary['hashes'])
        results = []
        seeds = set()
        report_pins = []
        for gate in gates:
            args = gate['arguments']
            contract = args[args.index('-m') + 1] if '-m' in args else Path(args[1]).name
            seeds.update(policy_modules(contract))
            if '--directory' in args:
                require(Path(args[args.index('--directory') + 1]).resolve() == folder.resolve(), 'Native gate directory differs')
                paths = [folder / (peer + '.json') for peer in summary['processes']]
            else:
                paths = [Path(args[args.index('--report') + 1])]
            for path in paths:
                require(path.resolve().parent == folder.resolve() and sha(path) == report_pin(ledger, record, Path(directory), path.name),
                        'Pinned native execution report differs')
                report_pins.append(dict(file=path.name, sha256=sha(path)))
            path = scripts / Path(*contract.split('.')).with_suffix('.py') if '-m' in args else integration / 'Tools' / contract
            dependency_modules = [contract] if '-m' in args else [node.module for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig')))
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('uep_')]
            dependencies = [report_dependency_guard(module, source, index.get(key(source), []))
                            for module, source in sorted(closure(scripts, dependency_modules).items())]
            results.append(dict(contract=contract, current_gate_sha256=sha(path), report_dependency_guards=dependencies, semantic_gate=execute_gate(args)))
        production = runtime_guards(repo, summary, sorted(seeds), contexts, latent_proof)
        logs = []
        for process in processes:
            path = Path(next(a.split('=', 1)[1] for a in process['arguments'] if a.startswith('-abslog=')))
            require(path.resolve().parent == folder.resolve(), 'Native execution log escaped its folder')
            text = path.read_text(encoding='utf-8-sig')
            require('Traceback' not in text and 'Fatal error' not in text and 'Goodbye Python' in text and 'Log file closed' in text and
                    text.index('Goodbye Python') < text.rindex('Log file closed'), 'Native interpreter/log shutdown or diagnostic failed')
            diagnostics = re.findall(r'[^\r\n]*(?:Ensure condition failed|Log\w+:\s*Error:)[^\r\n]*', text)
            if diagnostics:
                require(batch == 97 and sha(path) == report_pin(ledger, record, Path(directory), path.name),
                        'Unexpected/unpinned native diagnostic')
            logs.append(dict(file=path.name, sha256=sha(path), accepted_original_template_diagnostic_count=len(diagnostics)))
        jobs.append(dict(batch=batch, directory=directory, ledger=ledger_path.relative_to(repo).as_posix(), ledger_sha256=sha(ledger_path),
                         summary_sha256=sha(folder / 'summary.json'), native_processes=len(processes),
                         native_pids=[p['pid'] for p in processes], report_pins=report_pins, log_pins=logs,
                         policy_modules=sorted(seeds), current_policy_guards=production, independent_gates=results,
                         _index=index, _project=Path(processes[0]['arguments'][0]).parent))
    asset_rows = []
    modules = set()
    for candidate_row in classes:
        roots = candidate_row['effective_policy_modules']
        related = [j for j in jobs if set(roots).intersection(g['module'] for g in j['current_policy_guards'])]
        if roots:
            require(related, 'Native execution-boundary proof missing for candidate: ' + candidate_row['asset'])
            modules.update(closure(scripts, roots))
        else:
            require(candidate_row['source_reviewed_retention'], 'Unrouted original business requires an explicit retained disposition')
        guards = []
        for asset in (candidate_row['asset'], candidate_row['mixin_set']):
            if not asset:
                continue
            relative = relative_asset(asset, Path('F:/LyraStarterGame'))
            path = integration / 'Overlay' / relative
            if not path.is_file():
                path = Path('F:/LyraStarterGame') / relative
            matches = []
            for job in related:
                rows = job['_index'].get(key(path), [])
                if not rows:
                    rows = [dict(row, path=str(path)) for row in job['_index'].get(key(job['_project'] / relative), [])]
                if not rows:
                    continue
                try:
                    proof = source_guard(path, rows)
                except ValueError:
                    continue
                matches.append(dict(directory=job['directory'], **proof))
            retained_package = candidate_row['source_reviewed_retention'] and asset == candidate_row['asset']
            if retained_package:
                require(sha(path) == sha(Path('F:/LyraStarterGame') / relative) == sha(census_stage / relative),
                        'Retained empty/parent-forwarder class/stage differs from original')
            else:
                require(matches, 'Current native class/transport differs from all related execution records: ' + asset)
            guards.append(dict(asset=asset, current_path=str(path), current_sha256=sha(path), native_matches=matches,
                               retained_original_package=retained_package))
        asset_rows.append(dict(**candidate_row, asset_guards=guards, execution_boundaries=[j['directory'] for j in related]))
    source_checks = [native_boundary_writes(module, (scripts / Path(*module.split('.')).with_suffix('.py')).read_text(encoding='utf-8-sig'))
                     for module in sorted(modules)]
    for job in jobs:
        del job['_index'], job['_project']
    return dict(schema_version=1, status='passed', criterion=REQUIREMENT, completion_proven=True, version='0.11.0',
                original_candidates=37, original_native_class_identities_preserved=37,
                source_candidate_guard=dict(path=candidate_path.relative_to(repo).as_posix(), sha256=sha(candidate_path), **census),
                native_class_census=dict(path=coverage_path.relative_to(repo).as_posix(), sha256=sha(coverage_path)),
                candidates=asset_rows, native_execution_runs=jobs, source_boundary_checks=source_checks,
                native_execution_runs_revalidated=len(jobs), referenced_native_execution_processes=sum(j['native_processes'] for j in jobs),
                new_native_processes_launched_by_review=0, production_policy_or_assets_changed=False,
                all_historical_runs_use_current_sdk=False, original_netshooter_component_defect_preserved=True,
                full_component_replication_correctness_accepted=False, all_gameplay_and_lifetime_paths_accepted=False,
                cpp_compile_executed=False, cook_package_executed=False, full_regression_executed=False,
                full_version_acceptance=False, full_migration_acceptance_proven=False)


def verify_documentation(document, current, initial, repo):
    require(document.get('criterion') == REQUIREMENT and document.get('completion_proven') is True, 'Exact original native identity/execution-boundary criterion required')
    expected = inspect(repo, current, initial)
    require(document['review'] == expected, 'Ability identity/native-boundary review differs from current pinned evidence')
    return {name: expected[name] for name in ('status', 'criterion', 'original_candidates', 'original_native_class_identities_preserved',
                                             'native_execution_runs_revalidated', 'referenced_native_execution_processes',
                                             'new_native_processes_launched_by_review', 'full_migration_acceptance_proven')}
