"""Recheck original pickup/device outcomes against source-bound native records."""
import ast
import contextlib
import importlib
import io
import json
import re
import runpy
import sys
from pathlib import Path

from audit_candidate_dispositions import verify_documentation as verify_candidates
from audit_effects_match_acceptance import closure, verify_source
from audit_static_scope_dispositions import relative_asset
from audit_ui_failure_cancellation_acceptance import ledger_record, log_gate, report_pin, source_guard
from audit_ui_navigation_acceptance import index_hashes, key, read, sha

REQUIREMENT = ('Pickup failure/success, cooldown/respawn and interaction effects match '
               "the baseline; two players cannot share another player's UI or claim state.")
BASE = '.build/LyraValidation/BlueprintPython/'
NETWORK = (
    (3, '20261013-batch2b/PadNetwork02', 'effect_pad', 'UEP_EFFECT_PAD_NETWORK', ('effect_pad_mixin',)),
    (11, '20261016-inventory-pad/Network03', 'inventory_pad', 'UEP_INVENTORY_NETWORK', ('inventory_pad_mixin',)),
    (12, '20261016-grant-ge-pad/Network04', 'grant_ge', 'UEP_GRANT_GE_NETWORK', ('grant_ge_pad_mixin',)),
    (13, '20261016-launchers/Network05', 'launcher', 'UEP_LAUNCHER_NETWORK', ('launcher_mixin',)),
    (14, '20261016-spawners/Network02', 'spawner', 'UEP_SPAWNER_NETWORK', ('spawner_mixin',)),
    (15, '20261016-teleporter/Network02', 'teleporter', 'UEP_TELEPORTER_NETWORK', ('teleporter_mixin',)),
    (18, '20261016-heal-ability/Network03', 'heal_ability', 'UEP_HEAL_NETWORK', ('heal_ability_mixin',)),
)
EFFECTS = (
    (119, 'Differential04DeferredSpawner', 'uep_lyra_weapons.small_burst_cue_contract'),
    (141, 'ConsumerTraversal01', 'uep_lyra_weapons.traversal_cue_contract'),
)


def require(value, message):
    if not value:
        raise ValueError(message)


def processes(summary, folder):
    require(summary['status'] == 'passed' and summary.get('error') is None, 'Native world group failed')
    require(not summary['cpp_compile_executed'] and not summary['cook_package_executed'], 'Expected reused native builds')
    rows = summary['processes']
    require(isinstance(rows, list) and len(rows) == 3, 'Three actual native world peers required')
    require({row['name'] for row in rows} == {'server', 'A', 'B0'}, 'Missing/duplicate native peer')
    require(len({row['pid'] for row in rows}) == 3 and all(row['pid'] > 0 and row['exit_code'] == 0 for row in rows),
            'Distinct native peer processes must all exit0')
    require(summary['validation']['exit_code'] == 0, 'Original independent network gate failed')
    for row in rows:
        args = row['arguments']
        require('-UEPLyraNetPeer=' + row['name'] in args, 'Native process/peer identity differs')
        require(('-server' in args) is (row['name'] == 'server'), 'Native authority/client mode differs')
        log = Path(next(a.split('=', 1)[1] for a in args if a.startswith('-abslog=')))
        require(log.resolve() == (folder / (row['name'] + '.log')).resolve(), 'Native peer log escaped its folder')
    return {row['name']: row for row in rows}


def network_log(text, marker):
    require(not any(v in text for v in ('Traceback', 'Ensure condition failed', 'Fatal error')) and
            not re.search(r'Log\w+:\s*Error:', text), 'Unexpected native world diagnostic')
    needles = (marker + '_PASSED', 'Goodbye Python', 'UEP_LYRA_HUD_SHUTDOWN_PASSED', 'Log file closed')
    require(all(n in text for n in needles), 'Native world completion/shutdown marker missing')
    positions = [text.index(n) if n != 'Log file closed' else text.rindex(n) for n in needles]
    require(positions == sorted(positions) and len(set(positions)) == 4, 'Native world shutdown order differs')


def owner_identity(reports):
    require(set(reports) == {'server', 'A', 'B0'}, 'Two native owners and authority required')
    require(reports['server']['hud']['construct_count'] == 0, 'Dedicated authority constructed local UI')
    for packet in reports['server']['cases']:
        roster = packet['roster']
        require(set(roster) == {'A', 'B0'}, 'Both original native owners required')
        for field in ('player_id', 'controller_path', 'pawn_path'):
            require(roster['A'][field] != roster['B0'][field], 'Native pickup owners share ' + field)
        require(all(r['net_mode'] == 'DedicatedServer' and r['server_authority'] for r in roster.values()),
                'Claims must originate on the actual authority')
        require(packet['client_worlds']['A'] != packet['client_worlds']['B0'], 'Client world identities were shared')


def execute_network_gate(path, folder):
    previous = sys.argv
    output = io.StringIO()
    try:
        sys.argv = [str(path), str(folder)]
        with contextlib.redirect_stdout(output):
            runpy.run_path(str(path), run_name='__main__')
    finally:
        sys.argv = previous
    result = json.loads(output.getvalue())
    require(result['status'] == 'passed' and result['clients'] == 2 and result['full_acceptance'] is False,
            'Current independent world gate rejected original raw reports')
    return result


def guard_assets(repo, scope, coverage, jobs):
    rows = {row['asset']: row for row in coverage['assets']}
    guards = []
    for candidate in scope:
        asset = candidate['path']
        row = rows[asset]
        modules = {(p.get('python_class') or '').rsplit('.', 1)[0] for p in row.get('profiles', {}).values()}
        selected = [job for job in jobs if modules.intersection(job['policy_modules'])]
        require(selected, 'Native interaction family missing for ' + asset)
        fingerprints = []
        for value in (asset, row.get('mixin_set')):
            if not value:
                continue
            relative = relative_asset(value, Path('F:/LyraStarterGame'))
            path = repo / 'Demos/UEPLyraIntegration/Overlay' / relative
            if not path.is_file():
                path = Path('F:/LyraStarterGame') / relative
            matches = []
            for job in selected:
                stage = Path(job['_processes']['server']['arguments'][0]).parent
                records = job['_index'].get(key(path), [])
                if not records:
                    records = [dict(r, path=str(path)) for r in job['_index'].get(key(stage / relative), [])]
                if not records:
                    continue
                try:
                    proof = source_guard(path, records)
                except ValueError:
                    continue
                matches.append(dict(directory=job['directory'], **proof))
            require(matches, 'Current device/transport differs from its native family record: ' + value)
            fingerprints.append(dict(asset=value, current_path=str(path), matching_native_fingerprints=matches))
        guards.append(dict(asset=asset, effective_policy_modules=sorted(m for m in modules if m), guards=fingerprints))
    return guards


def effect_jobs(repo, scripts):
    migration = scripts.parents[2] / 'Migration'
    document = read(migration / 'effects_match_acceptance.json')
    review = document.get('review', document)
    require(review['completion_proven'] and review['checkpoint_candidates'] == 63, 'Accepted effect checkpoint review required')
    macro = next(r for r in review['native_runs'] if r['contract'].endswith('macro_closure_contract'))
    contexts = dict(macro_native_directory=macro['directory'], macro_native_guard=sha(scripts / 'uep_lyra_weapons/macro_policies.py'))
    results = []
    for batch, name, contract in EFFECTS:
        recorded = next(r for r in review['native_runs'] if r['batch'] == batch and Path(r['directory']).name == name)
        folder = repo / recorded['directory']
        require(sha(folder / 'summary.json') == recorded['summary_sha256'], 'Pinned interaction-effect summary changed')
        summary = read(folder / 'summary.json')
        require(summary['status'] == 'passed' and summary['error'] is None and summary['process']['exit_code'] == 0 and
                summary['external_gate']['exit_code'] == 0, 'Native interaction-effect process/gate failed')
        report_path = folder / recorded['report_file']
        log_path = Path(next(a.split('=', 1)[1] for a in summary['process']['arguments'] if a.startswith('-abslog=')))
        require(sha(report_path) == recorded['report_sha256'] and sha(log_path) == recorded['log_sha256'], 'Pinned native effect output changed')
        for marker in recorded['markers']:
            log_gate(log_path.read_text(encoding='utf-8-sig'), marker)
        gate = importlib.import_module(contract).validate(read(report_path))
        index = index_hashes(summary['hashes'])
        contract_path = scripts / Path(*contract.split('.')).with_suffix('.py')
        contract_guard = source_guard(contract_path, index.get(key(contract_path), []))
        policies = verify_source(repo, summary, recorded['policy_modules'], contexts)
        assets = []
        for candidate in review['candidate_asset_guards']:
            if not set(candidate['effective_policy_modules']).intersection(recorded['policy_modules']):
                continue
            for row in candidate['guards']:
                path = Path(row['current_path'])
                fingerprints = [dict(path=str(path), sha256=r['native_sha256'])
                                for r in row['matching_native_fingerprints'] if r['directory'] == recorded['directory']]
                require(fingerprints, 'Native interaction Cue asset fingerprint missing')
                assets.append(dict(asset=row['asset'], current_path=str(path), **source_guard(path, fingerprints)))
        require(assets, 'Original interaction-effect asset family required')
        results.append(dict(batch=batch, directory=recorded['directory'], summary_sha256=sha(folder / 'summary.json'),
                            report_sha256=sha(report_path), log_sha256=sha(log_path), contract=contract,
                            contract_guard=contract_guard, semantic_gate=gate, current_policy_guards=policies, asset_guards=assets,
                            native_processes=1))
    return results


def combined_hud_job(repo, scripts):
    """The later HUD run freezes the current presenters, including owner UI."""
    from uep_lyra_weapon_protocol import validate_reports
    folder = repo / BASE / '20261016-device-color/CombinedNetwork01'
    migration = scripts.parents[2] / 'Migration'
    ledger_path = migration / 'Acceptance/11-inventory-pads.json'
    ledger = read(ledger_path)
    record = ledger_record(ledger, folder.relative_to(repo).as_posix())
    require(sha(folder / 'summary.json') == record['summary_sha256'], 'Pinned combined HUD summary changed')
    summary = read(folder / 'summary.json')
    peers = summary['processes']
    require(summary['status'] == 'passed' and summary['error'] is None and set(peers) == {'server', 'A', 'B0', 'B1'} and
            len({r['pid'] for r in peers.values()}) == 4 and all(r['pid'] > 0 and r['exit_code'] == 0 for r in peers.values()),
            'Combined native HUD peers did not all exit0')
    require(not summary['cpp_compile_executed'] and not summary['cook_package_executed'], 'Expected reused HUD native build')
    reports = {}
    pins = []
    for peer, process in peers.items():
        path = folder / (peer + '.json')
        require(sha(path) == report_pin(ledger, record, folder.relative_to(repo), path.name), 'Pinned combined HUD peer changed')
        log = Path(next(a.split('=', 1)[1] for a in process['arguments'] if a.startswith('-abslog=')))
        require(log.resolve() == (folder / (peer + '.log')).resolve(), 'Combined native HUD log escaped its folder')
        text = log.read_text(encoding='utf-8-sig')
        require(not any(v in text for v in ('Traceback', 'Ensure condition failed', 'Fatal error')) and
                not re.search(r'Log\w+:\s*Error:', text), 'Unexpected combined native HUD diagnostic')
        needles = ('Goodbye Python', 'UEP_LYRA_HUD_SHUTDOWN_PASSED', 'Log file closed')
        require(all(n in text for n in needles) and text.index(needles[0]) < text.index(needles[1]) < text.rindex(needles[2]),
                'Combined HUD native shutdown order differs')
        reports[peer] = read(path)
        pins.append(dict(peer=peer, pid=process['pid'], exit_code=0, report_sha256=sha(path), log_sha256=sha(log)))
    gate = validate_reports(reports, summary['run_id'], combat_hud=True, debug_spread=True, production_reticles=True,
                            reticle_hosts=True, ability_progress=True, ability_failure=True, dash_cooldown=True,
                            respawn_timer=True, quickbar_slots=True, nameplates=True)
    require(gate == summary['protocol_validation'] and gate['phase_count'] == 19 and gate['rejoin_tested'],
            'Original complete nineteen-phase native owner/HUD protocol differs')
    index = index_hashes(summary['input_hashes'])
    modules = ['uep_lyra_hud.healthbar_mixin', 'uep_lyra_hud.ability_failure_mixin',
               'uep_lyra_hud.quickbar_slot_mixin', 'uep_lyra_weapon_protocol']
    guards = [dict(module=module, **source_guard(path, index.get(key(path), [])))
              for module, path in sorted(closure(scripts, modules).items())]
    return dict(directory=folder.relative_to(repo).as_posix(), ledger=ledger_path.relative_to(repo).as_posix(),
                ledger_sha256=sha(ledger_path), summary_sha256=sha(folder / 'summary.json'), native_peers=pins,
                semantic_gate=gate, current_presenter_and_protocol_guards=guards, native_processes=4,
                _index=index, _processes=peers, policy_modules=modules)


def inspect(repo, current, initial):
    repo = Path(repo).resolve()
    migration = repo / 'Demos/UEPLyraIntegration/Migration'
    scripts = migration.parent / 'Overlay/Content/Scripts'
    candidate_path = migration / 'candidate_dispositions.json'
    candidate = read(candidate_path)
    census = verify_candidates(candidate, current, initial, repo)
    scope = [row for row in initial['assets'] if row['version'] == '0.10.0' and row['group'] == '拾取与场景机关']
    require(len(scope) == 12 and len({r['path'] for r in scope}) == 12, 'Exact twelve original interaction candidates required')
    native_ledger = read(repo / candidate['evidence_paths']['native_ledger'])
    coverage = read(repo / native_ledger['runs'][0]['directory'] / 'audit.json')
    jobs = []
    for batch, suffix, gate_name, marker, names in NETWORK:
        directory = BASE + suffix
        folder = repo / directory
        ledger_path = next((migration / 'Acceptance').glob(f'{batch:02}-*.json'))
        ledger = read(ledger_path)
        record = ledger_record(ledger, directory)
        require(sha(folder / 'summary.json') == record['summary_sha256'].upper(), 'Pinned world summary changed')
        summary = read(folder / 'summary.json')
        peers = processes(summary, folder)
        reports = {peer: read(folder / (peer + '.json')) for peer in peers}
        pins = []
        for peer in peers:
            path = folder / (peer + '.json')
            require(sha(path) == report_pin(ledger, record, Path(directory), path.name), 'Pinned world peer report changed')
            network_log((folder / (peer + '.log')).read_text(encoding='utf-8-sig'), marker)
            pins.append(dict(peer=peer, pid=peers[peer]['pid'], exit_code=0, report_sha256=sha(path), log_sha256=sha(folder / (peer + '.log'))))
        owner_identity(reports)
        path = migration.parent / 'Tools' / ('validate_' + gate_name + '_network_reports.py')
        require(any(Path(a).resolve() == path.resolve() for a in summary['validation']['arguments'] if a.endswith('.py')),
                'Original independent world gate differs')
        index = index_hashes(summary['hashes'])
        records = index.get(key(path), [])
        gate_guard = source_guard(path, records) if records else dict(current_sha256=sha(path),
            original_gate_tool_source_frozen=False, current_read_only_gate_reexecuted=True)
        gate = execute_network_gate(path, folder)
        policies = ['uep_lyra_world.' + name for name in names]
        guards = []
        gate_dependencies = [n.module for n in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig')))
                             if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith('uep_')]
        for module, source in sorted(closure(scripts, policies + gate_dependencies).items()):
            guards.append(dict(module=module, **source_guard(source, index.get(key(source), []))))
        jobs.append(dict(batch=batch, directory=directory, ledger=ledger_path.relative_to(repo).as_posix(), ledger_sha256=sha(ledger_path),
                         summary_sha256=sha(folder / 'summary.json'), native_peers=pins, semantic_gate=gate, gate_guard=gate_guard,
                         policy_modules=policies, current_policy_guards=guards, native_processes=3,
                         _processes=peers, _index=index))
    assets = guard_assets(repo, scope, coverage, jobs)
    effects = effect_jobs(repo, scripts)
    hud = combined_hud_job(repo, scripts)
    hud_paths = {'/Game/UI/Hud/W_Healthbar.W_Healthbar',
                 '/ShooterCore/UserInterface/HUD/W_AbilityFailureFeedback.W_AbilityFailureFeedback',
                 '/ShooterCore/UserInterface/HUD/W_QuickBarSlot.W_QuickBarSlot'}
    hud_scope = [r for r in current['assets'] if r['path'] in hud_paths]
    require(len(hud_scope) == 3, 'Original owner Health/failure/quickbar presenter assets required')
    hud_assets = guard_assets(repo, hud_scope, coverage, [hud])
    require(sum(j['semantic_gate']['cases'] for j in jobs) == 108, 'Full original two-owner interaction matrix required')
    for job in jobs:
        del job['_processes'], job['_index']
    del hud['_processes'], hud['_index']
    return dict(schema_version=1, status='passed', criterion=REQUIREMENT, completion_proven=True, version='0.10.0',
                interaction_candidates=12, original_version_candidates=32, network_case_rows=108,
                source_candidate_guard=dict(path=candidate_path.relative_to(repo).as_posix(), sha256=sha(candidate_path), **census),
                candidate_asset_guards=assets, native_network_runs=jobs, native_interaction_effect_runs=effects,
                owner_hud_run=hud, owner_hud_asset_guards=hud_assets,
                referenced_native_processes=27, new_native_processes_launched_by_review=0,
                current_sdk_used_for_every_historical_run=False, hardware_audio_output_tested=False,
                pixels_tested=False, packaged_runtime=False, native_ability_cost_commit_refusal_tested=False,
                all32_candidates_gameplay_accepted=False, cpp_compile_executed=False, cook_package_executed=False,
                full_regression_executed=False, full_version_acceptance=False, full_migration_acceptance_proven=False,
                limits=[
                    'Accepts the original pickup/device success/rejection,cooldown/respawn,interaction-effect and two-owner UI/claim criterion only. The other0.10 small-batch and teardown/travel/profile criteria remain separate.',
                    'Seven original authority-plus-two-client groups cover108 paired rows. Each owner has an independent native player/controller/Pawn/world;native inventory,Health,availability,failure message and local Health presentation must match the corresponding authority and preserve the other owner.',
                    'A separate four-process nineteen-phase original/Python HUD record freezes current Health,failure and quickbar presenters and their local-owner/protocol dependencies. It checks owner presentation against native state,foreign-owner stability,teardown and rejoin;older world runs alone are not used to certify later presenter source.',
                    'Full slots,duplicate-full-ammo,full Health and inactive reentry are pickup refusals. Native GAS cost/commit refusal inside GA_HealPickup is a separate still-open ability-path check;this review does not claim it or every activation branch.',
                    'Actual native10/15-second cooldowns,replicated availability/light/mesh state and unchanged policy/asset bytes are rechecked. Original pickup/heal and launcher/teleport effect families are independently revalidated against their accepted native parameter,spawn,Timeline and audio-component records.',
                    'The earlier spawner Differential03 policy fingerprint does not match current source and is deliberately excluded. Current spawner Network02 freezes the current policy and all36 owner/scenario/profile rows;no source-equivalence exception is inferred.',
                    'Historical native SDK/configurations remain explicit. No new UE process,build,cook/package,hardware audio or screenshot comparison occurs. This does not accept every data combination,grenade teleporter branch,authenticated service or all32 HUD/device candidates.'
                ])


def verify_documentation(document, current, initial, repo):
    require(document.get('criterion') == REQUIREMENT and document.get('completion_proven') is True, 'Exact original pickup/device criterion required')
    expected = inspect(repo, current, initial)
    require(document['review'] == expected, 'World interaction review differs from current native/source evidence')
    return {name: expected[name] for name in ('status', 'criterion', 'interaction_candidates', 'network_case_rows',
                                             'referenced_native_processes', 'new_native_processes_launched_by_review',
                                             'full_migration_acceptance_proven')}
