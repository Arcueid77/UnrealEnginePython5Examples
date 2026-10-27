"""Recheck controlled reload, repeated PIE/GC and actual two-client travel cleanup."""
import re
import sys
from pathlib import Path

from audit_call_lifecycle_matrix_acceptance import SDK, pie_gate
from audit_ui_navigation_acceptance import read, sha

REQUIREMENT = ('The controlled reload and cleanup tests pass across repeated PIE, GC and travel; '
               'state, callbacks and router restoration are checked after teardown.')
BASE = '.build/LyraValidation/BlueprintPython/20261028-reload-cleanup'
PIE = '.build/LyraValidation/BlueprintPython/20261027-call-lifecycle-matrix/PIE01'
ASSETS = ('W_WeaponAmmoAndName', 'W_AmmoCounter_Pistol',
          'W_AmmoCounter_Rifle', 'W_AmmoCounter_Shotgun')


def require(value, message):
    if not value:
        raise ValueError(message)


def cleanup(value, *, exercised):
    for created, closed in (('subscribed', 'unsubscribed'), ('scope_created', 'scope_closed')):
        require(type(value.get(created)) is int and type(value.get(closed)) is int and
                value[created] == value[closed] and value[created] >= int(exercised),
                'Missing or unbalanced exercised subscriptions/scopes')
    require(value.get('active_count') == 0 and value.get('active_scopes') == 0 and
            value.get('ticker_active') is False and value.get('active_widgets') == [] and
            value.get('errors') == [], 'Owned weapon callback, object or sampler survived teardown')


def weapon_gate(report):
    require(report.get('status') == 'passed' and report.get('class_identity_preserved') is True and
            report.get('persisted_declarations_used') is True and report.get('restored_classes') == 4,
            'Original four class routers/identity not restored')
    expected = [(asset, scenario) for asset in ASSETS for scenario in
        ('initialized', 'ammo-5', 'ammo-4', 'ammo-3', 'ammo-2', 'ammo-1', 'ammo-0', 'ammo-30', 'weapon-switch') +
        (('empty-slot', 'slot-restored', 'reload-input-dispatch') if asset == ASSETS[0] else ('brush-helper',))]
    require([(r['asset'], r['scenario']) for r in report['cases']] == expected,
            'Original weapon state comparison incomplete')
    for case in report['cases']:
        if case['scenario'] == 'brush-helper':
            require(case['resource_matches_argument'] is True and case['counter_style_preserved'] is True,
                    'Native brush-helper state differs')
            continue
        if case['scenario'] == 'reload-input-dispatch':
            require(case['native_input_intent_only'] is True and case['python_calls'].get('ReloadClicked') == 1 and
                    case['python_calls'].get('Tick', 0) > 0, 'Native reload intent not dispatched')
            continue
        require(case['baseline'] == case['python'] and case['python_calls'].get('Tick', 0) > 0,
                'State differs or Python path unexercised')
    signal = report['subscription_scope']
    require(signal == dict(status='passed', native_message_callbacks=1, cancel_verified=True,
                           payload_access=False), 'Native callback/cancel boundary incomplete')
    require([r['asset'] for r in report['profile_switches']] == list(ASSETS), 'Missing live profile switch')
    for switch in report['profile_switches']:
        require(switch['status'] == 'passed' and switch['without_reconstruct'] is True and
                switch['observer_count_restored'] == 4, 'Profile switch replayed Construct or lost observers')
    require(len(report['reload_cycles']) == 3, 'Three controlled reload cycles required')
    for cycle in report['reload_cycles']:
        require(all(cycle.get(k) is True for k in ('new_widget', 'native_gc_collected',
                'python_housekeeper_gc_executed')) and cycle['status'] == 'passed' and
                cycle['before']['active_count'] == 1 and cycle['before']['active_scopes'] == 1,
                'Controlled new-widget/native-GC reload was not exercised')
        cleanup(cycle['after'], exercised=True)
    cleanup(report['observer_cleanup'], exercised=True)
    require(report['shutdown'] == dict(phase='python_atexit', owned_resources_closed_before_exit=True),
            'Cleanup must precede interpreter exit')


def log_gate(text, marker, shutdown):
    require(not any(v in text for v in ('Traceback', 'Ensure condition failed', 'Fatal error')) and
            not re.search(r'Log\w+:\s*Error:', text), 'Unexpected native error')
    markers = dict.fromkeys((marker, 'Goodbye Python', shutdown, 'Log file closed'))
    pattern = '.*'.join(re.escape(v) for v in markers)
    require(re.search(pattern, text, re.S), 'Native completion/cleanup/closed-log ordering incomplete')


def network_cleanup(reports):
    require(set(reports) == {'server', 'A', 'B0', 'B1'}, 'Authority, two clients and rejoin required')
    result = []
    for peer, report in sorted(reports.items()):
        final = report['shutdown']
        require(report['status'] == 'passed' and final['status'] == 'passed', 'Network shutdown failed')
        observer = final['weapon_observer']
        cleanup(observer, exercised=peer != 'server')
        hud = final['hud']
        require(hud['errors'] == [] and hud['active_widget_count'] == 0 and
                hud['live_widget_reference_count'] == 0, 'Travel left HUD references/errors')
        for created, closed in (('construct_count', 'destruct_count'),
                                ('controller_bind_count', 'controller_unbind_count'),
                                ('health_bind_count', 'health_unbind_count')):
            require(hud[created] == hud[closed] and hud[created] >= int(peer != 'server'),
                    'Native HUD lifecycle/callback imbalance')
        result.append(dict(peer=peer, subscriptions_closed=observer['unsubscribed'],
            scopes_closed=observer['scope_closed'], native_signals=observer['native_signals'],
            active_owned_resources=0))
    require(all(reports[p]['shutdown']['weapon_observer']['scope_closed'] >= 3 for p in ('A', 'B0')),
            'Both original clients must exercise travel scopes')
    require(sum(r['native_signals'] for r in result) > 0, 'Native owner/slot signals were never exercised')
    return result


def frozen(summary, digest):
    rows = summary.get('input_hashes', []) + summary.get('source_hashes', []) + summary.get('binary_hashes', [])
    require(rows, 'Frozen native inputs absent')
    for row in rows:
        require(digest(Path(row['path'])) == row['sha256'].upper(), 'Frozen runtime/source input changed: ' + row['path'])
    for row in summary.get('native_source_hashes', []):
        for name in ('source', 'target'):
            require(digest(Path(row[name])) == row['sha256'].upper(), 'Native stage/source parity changed')
    sdks = {r['sha256'].upper() for r in rows if Path(r['path']).name == 'UnrealEditor-UnrealEnginePython.dll'}
    require(sdks == {SDK}, 'Current SDK236 required')
    return len(rows)


def inspect(repo, current, initial):
    repo = Path(repo)
    require(len(initial['assets']) == 246 and [(r['path'], r['version']) for r in current['assets']] ==
            [(r['path'], r['version']) for r in initial['assets']], 'Original migration inventory changed')
    cache = {}
    def digest(path):
        name = str(path.resolve()).casefold()
        if name not in cache:
            cache[name] = sha(path)
        return cache[name]
    rows = []
    for directory in (BASE + '/Weapon01', BASE + '/WeaponNetwork01', PIE):
        folder = repo / directory; summary = read(folder / 'summary.json')
        require(summary['status'] == 'passed' and summary.get('error') is None and
                summary['cpp_compile_executed'] is False and summary['cook_package_executed'] is False,
                'Expected completed incremental native validation')
        count = frozen(summary, digest)
        rows.append(dict(directory=directory, summary_sha256=sha(folder / 'summary.json'),
                         current_frozen_inputs=count))
    folder = repo / BASE / 'Weapon01'; summary = read(folder / 'summary.json')
    require(summary['process']['exit_code'] == 0 and summary['process']['pid'] > 0, 'Weapon process not cleanly terminal')
    weapon_gate(read(folder / 'weapon.json'))
    log_gate((folder / 'weapon.log').read_text(encoding='utf-8-sig'),
             'UEP_WEAPON_HUD_DIFFERENTIAL_PASSED', 'UEP_WEAPON_HUD_SHUTDOWN_PASSED')
    rows[0].update(pid=summary['process']['pid'], exit_code=0, report_sha256=sha(folder/'weapon.json'),
                   log_sha256=sha(folder/'weapon.log'))
    folder = repo / BASE / 'WeaponNetwork01'; summary = read(folder / 'summary.json')
    require(set(summary['processes']) == {'server', 'A', 'B0', 'B1'} and
            len({r['pid'] for r in summary['processes'].values()}) == 4 and
            all(r['pid'] > 0 and r['exit_code'] == 0 for r in summary['processes'].values()),
            'Four actual completed network processes required')
    scripts = repo / 'Demos/UEPLyraIntegration/Overlay/Content/Scripts'
    sys.path.insert(0, str(scripts))
    from uep_lyra_weapon_protocol import validate_reports
    reports = {p:read(folder/(p+'.json')) for p in summary['processes']}
    protocol = validate_reports(reports, summary['run_id'], combat_hud=True)
    require(protocol == summary['protocol_validation'] and protocol['phase_count'] == 19 and
            protocol['rejoin_tested'] is True, 'Two-travel/rejoin protocol proof differs')
    cleanup_rows = network_cleanup(reports)
    peers = []
    for peer, process in sorted(summary['processes'].items()):
        require('-UEPLyraNetPeer=' + peer in process['arguments'] and
                ('-server' in process['arguments']) is (peer == 'server'), 'Native peer/authority identity differs')
        # These fixtures emit their final success markers from Python atexit.
        text = (folder/(peer+'.log')).read_text(encoding='utf-8-sig')
        log_gate(text, 'Goodbye Python', 'UEP_LYRA_HUD_SHUTDOWN_PASSED')
        peers.append(dict(peer=peer, pid=process['pid'], exit_code=0,
                          report_sha256=sha(folder/(peer+'.json')), log_sha256=sha(folder/(peer+'.log'))))
    rows[1].update(native_peers=peers, protocol=protocol, cleanup=cleanup_rows)
    folder = repo / PIE; summary = read(folder/'summary.json')
    require(summary['process']['pid'] > 0 and summary['process']['exit_code'] == 0, 'PIE process not terminal')
    pie_gate(read(folder/'pie.json'))
    text = (folder/'pie.log').read_text(encoding='utf-8-sig')
    require(re.search(r'UEP_MIXIN_PIE_PASSED.*Preparing to exit.*UEP_MIXIN_PIE_SHUTDOWN_PASSED.*Goodbye Python.*Log file closed',
                      text, re.S) and 'Attaching UnrealEnginePython to the existing CPython interpreter' in text,
            'Actual shared-interpreter PIE shutdown/router restoration missing')
    require(not any(s in text for s in ('Traceback', 'Ensure condition failed', 'Fatal error')) and
            not re.search(r'Log\w+:\s*Error:', text), 'Unexpected PIE error')
    rows[2].update(pid=summary['process']['pid'], exit_code=0, report_sha256=sha(folder/'pie.json'),
                   log_sha256=sha(folder/'pie.log'), reused_without_reexecution=True)
    return dict(status='passed', criterion=REQUIREMENT, completion_proven=True,
        runs=rows, controlled_new_widget_reload_cycles=3, live_profile_round_trips=4,
        weapon_scenarios=42, paired_state_comparisons=38, same_editor_pie_sessions=3, real_network_phases=19,
        server_travels=2, client_rejoin=True, current_sdk_sha256=SDK,
        fresh_native_processes=5, reused_native_pie_processes=1,
        cpp_compile_executed=False, cook_package_executed=False, full_regression_executed=False,
        full_migration_acceptance_proven=False,
        limits=['Controlled unregister/reload/re-register creates NEW widgets; arbitrary state migration/recompile remains unsupported.',
                'The three-session current-SDK PIE run is reused after exact frozen source/binary verification.',
                'Editor game network runtime only; no packaged networking, hardware input or complete visual/audio parity claim.',
                'Rendered network images include TapIDs/invalid-tap warnings in the NoSound fixture; visual acceptance remains open.',
                'Only the exact original reload/cleanup criterion is accepted.'])


def verify_documentation(document, current, initial, repo):
    require(document.get('criterion') == REQUIREMENT and document.get('completion_proven') is True,
            'Exact original controlled reload/cleanup requirement required')
    expected = inspect(repo, current, initial)
    require(document.get('review') == expected, 'Recorded reload/cleanup evidence differs')
    return {k:expected[k] for k in ('status', 'criterion', 'controlled_new_widget_reload_cycles',
        'live_profile_round_trips', 'same_editor_pie_sessions', 'real_network_phases', 'server_travels')}
