"""Recheck the original 0.10 lifetime criterion, preserving each fixture's scope."""
import ast
from pathlib import Path

from audit_ability_lifetime_acceptance import selected_record, scope_provenance
from audit_effects_match_acceptance import closure
from audit_static_scope_dispositions import relative_asset
from audit_ui_failure_cancellation_acceptance import report_pin, source_guard
from audit_ui_navigation_acceptance import index_hashes, key, read, sha
from audit_world_interaction_acceptance import (combined_hud_job, execute_network_gate,
    network_log, processes)

REQUIREMENT = ('Widget and Actor lifetime tests leave no owned subscriptions after '
               'teardown, travel or profile switching.')
BASE = '.build/LyraValidation/BlueprintPython/20261026-widget-actor-lifetime'
HUD = 'uep_lyra_hud.'
OWNED = {HUD + name + '_mixin' for name in (
    'action_touch', 'nameplate_manager', 'nameplate_source', 'nameplate', 'dash_cooldown',
    'respawn_timer', 'ability_failure', 'ability_progress', 'quickbar_slot',
    'reticle_ammo', 'reticle_host', 'weapon_reticle')} | {'uep_lyra_world.heal_ability_mixin'}
NO_PYTHON_SUBSCRIPTIONS = {HUD + name + '_mixin' for name in ('open_menu', 'fire_button', 'debug_spread')} | {
    'uep_lyra_world.' + name + '_mixin' for name in (
        'effect_pad', 'grant_ge_pad', 'inventory_pad', 'launcher', 'spawner', 'teleporter')}
OWNING_CALLS = {'SubscriptionScope', 'subscribe', 'bind_event', 'bind_delegate',
                'add_ticker', 'set_timer', 'add_listener', 'add_callable'}


def require(value, message):
    if not value:
        raise ValueError(message)


def balanced(value, created='scopes_created', closed='scopes_closed', *, exercised=False):
    require(value.get('active_count') == 0 and value.get('errors') == [], 'Owned lifetime leak/error')
    require(type(value.get(created)) is int and type(value.get(closed)) is int and
            value[created] == value[closed] and value[created] >= int(exercised),
            'Missing/unbalanced native lifetime counters')
    for field in ('active_widgets', 'active_sources', 'active_abilities'):
        require(not value.get(field), 'Owned object survived cleanup: ' + field)


def ownership(sources):
    require(set(sources) == OWNED | NO_PYTHON_SUBSCRIPTIONS, 'Original 22 policy families required')
    result = []
    for module, source in sorted(sources.items()):
        calls = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else (
                    node.func.attr if isinstance(node.func, ast.Attribute) else '')
                if name in OWNING_CALLS:
                    calls.add(name)
        require(bool(calls) is (module in OWNED), 'Unreviewed/missing owned subscription factory: ' + module)
        result.append(dict(module=module, owns_python_subscriptions=bool(calls), factories=sorted(calls),
                           native_gameinstance_async_push=(module == HUD + 'open_menu_mixin')))
    return result


def combined_cleanup(reports):
    """Require exercised owning families, not only empty dedicated-server totals."""
    groups = ('weapon_reticle_observers', 'reticle_host_observers', 'ability_progress_observers',
              'ability_failure_observers', 'dash_cooldown_observers', 'respawn_timer_observers',
              'quickbar_slot_observers')
    rows = []
    for peer, report in sorted(reports.items()):
        final = report['shutdown']
        require(final['status'] == 'passed', 'Native HUD shutdown failed')
        for group in groups:
            value = final[group]
            balanced(value, exercised=peer != 'server')
            pool = value.get('pool_lifetime')
            if pool is not None:
                balanced(pool, 'registered', 'unregistered', exercised=peer != 'server')
                require(pool['ticker_active'] is False, 'UIExtension pool sampler survived shutdown')
        observer = final['weapon_observer']
        balanced(observer, 'scope_created', 'scope_closed', exercised=peer != 'server')
        require(observer['subscribed'] == observer['unsubscribed'] and
                observer['active_scopes'] == 0 and observer['ticker_active'] is False,
                'Native weapon observer retained callbacks/ticker')
        for name in ('sources', 'managers', 'widgets'):
            value = final['nameplate_observers'][name]
            balanced(value, exercised=peer != 'server')
            if name == 'widgets':
                require(value['team_proxies_created'] == value['team_proxies_cancelled'] and
                        value['init_bound'] == value['init_unbound'] + value['init_owner_released'],
                        'Nameplate native team/init-state lease leaked')
            else:
                require(value['helpers_rooted'] == value['helpers_unrooted'], 'Nameplate helper root leaked')
        rows.append(dict(peer=peer, owning_groups=len(groups) + 4, active_owned_subscriptions=0))
    return rows


def source_guards(scripts, modules, summary):
    index = index_hashes(summary.get('input_hashes', summary.get('hashes')))
    guards = [dict(module=module, **source_guard(path, index.get(key(path), [])))
              for module, path in sorted(closure(scripts, modules).items())]
    return index, guards


def action_touch_job(repo, migration, scripts):
    folder = repo / BASE / 'TouchNetwork01'; summary = read(folder / 'summary.json')
    peers = processes(summary, folder); pins = []
    for peer in peers:
        report = folder / (peer + '.json'); log = folder / (peer + '.log')
        network_log(log.read_text(encoding='utf-8-sig'), 'UEP_ACTION_TOUCH_NETWORK')
        value = read(report)
        balanced(value['shutdown']['action_touch_observers'], exercised=peer != 'server')
        pins.append(dict(peer=peer, pid=peers[peer]['pid'], exit_code=0,
                         report_sha256=sha(report), log_sha256=sha(log)))
    gate_path = repo / 'Demos/UEPLyraIntegration/Tools/validate_action_touch_network_reports.py'
    gate = execute_network_gate(gate_path, folder)
    require(gate == summary['protocol'], 'Original native driver touch gate differs')
    require(all(sha(row['path']) == row['sha256'] for row in summary['hashes']), 'Fresh frozen touch input changed')
    index, guards = source_guards(scripts, [HUD+'action_touch_mixin', HUD+'action_touch_network_validation',
                                            HUD+'action_touch_network_protocol'], summary)
    source_guard(gate_path, index.get(key(gate_path), []))
    return dict(directory=folder.relative_to(repo).as_posix(), summary_sha256=sha(folder/'summary.json'),
                native_peers=pins, semantic_gate=gate, current_source_guards=guards, native_processes=3,
                frozen_native_inputs=len(summary['hashes']),
                lifetime_boundaries=['unmount', 'reconstruct', 'profile-round-trip', 'shutdown'],
                actual_travel_tested=False, physical_touch_tested=False,
                _index=index, _stage=Path(peers['server']['arguments'][0]).parent)


def heal_job(repo, scripts):
    from uep_lyra_world.heal_ability_contract import validate
    folder = repo / BASE / 'HealStandalone01'; summary = read(folder/'summary.json')
    require(summary['status'] == 'passed' and summary['error'] is None and
            summary['process']['exit_code'] == 0 and summary['process']['pid'] > 0 and
            not summary['cpp_compile_executed'] and not summary['cook_package_executed'],
            'Fresh native heal lifetime process failed')
    arguments = summary['process']['arguments']
    require('-game' in arguments and '-server' not in arguments and
            any(a.startswith('-UEPHealAbilityResult=') for a in arguments), 'Actual heal Standalone mode required')
    report = folder/'launcher.json'; log = folder/'launcher.log'
    text = log.read_text(encoding='utf-8-sig')
    from audit_ui_failure_cancellation_acceptance import log_gate
    log_gate(text, 'UEP_HEAL_ABILITY')
    value = read(report); gate = validate(value)
    balanced(value['policy_shutdown'], exercised=True)
    original_gate = read(folder/'report-gate-stdout.log')
    require(original_gate == gate, 'Native driver pure gate output differs')
    require(not (folder/'report-gate-stderr.log').read_text(encoding='utf-8-sig').strip(), 'Native driver pure gate error')
    # This new closed capture can still check all frozen inputs; historical
    # captures below use selected current-source guards instead of mutable stage.
    require(all(sha(row['path']) == row['sha256'] for row in summary['hashes']), 'Fresh frozen native input changed')
    index, guards = source_guards(scripts, ['uep_lyra_world.heal_ability_mixin',
        'uep_lyra_world.heal_ability_validation', 'uep_lyra_world.heal_ability_contract'], summary)
    return dict(directory=folder.relative_to(repo).as_posix(), summary_sha256=sha(folder/'summary.json'),
                native_peers=[dict(peer='Standalone', pid=summary['process']['pid'], exit_code=0,
                    report_sha256=sha(report), log_sha256=sha(log))], semantic_gate=gate,
                current_source_guards=guards, frozen_native_inputs=len(summary['hashes']), native_processes=1,
                lifetime_boundaries=['montage-end', 'native-cancel', 'native-interrupt', 'native-timer',
                    'paused-world-time', 'active-profile-switch', 'external-native-end', 'shutdown'],
                actual_travel_tested=False, _index=index, _stage=Path(arguments[0]).parent)


def owned_assets(repo, scope, coverage, dispositions, jobs):
    rows = {r['asset']:r for r in coverage['assets']}; result = []
    for candidate in scope:
        asset = candidate['path']; disposition = dispositions[asset]
        module = (disposition.get('effective_python_class') or '').rsplit('.', 1)[0]
        if module not in OWNED:
            continue
        guards = []
        for value in (asset, rows[asset].get('mixin_set')):
            if not value:
                continue
            relative = relative_asset(value, Path('F:/LyraStarterGame'))
            path = repo/'Demos/UEPLyraIntegration/Overlay'/relative
            if not path.is_file():path = Path('F:/LyraStarterGame')/relative
            matches = []
            for job in jobs:
                records = job['_index'].get(key(path), []) or [dict(r, path=str(path))
                    for r in job['_index'].get(key(job['_stage']/relative), [])]
                try:proof = source_guard(path, records)
                except ValueError:continue
                matches.append(dict(directory=job['directory'], **proof))
            require(matches, 'Owned current class/Mixin package differs from native lifetime inputs: '+value)
            guards.append(dict(asset=value, current_path=str(path), matching_native_fingerprints=matches))
        result.append(dict(asset=asset, policy_module=module, guards=guards))
    require(len(result) == 16, 'All 16 original subscription-owning candidates required')
    return result


def census_scope(repo, migration, scope, document):
    """Bind only these32 classes to the already accepted source/census review."""
    identity_path, = (migration/'Acceptance').glob('256-*.json')
    identity = read(identity_path)['review']
    for pin in (identity['source_candidate_guard'], identity['native_class_census']):
        require(sha(repo/pin['path']) == pin['sha256'], 'Accepted candidate/census source pin changed')
    ledger_path = repo/document['evidence_paths']['native_ledger']; ledger = read(ledger_path)
    record, = ledger['runs']; folder = repo/record['directory']; summary = read(folder/'summary.json')
    require(sha(folder/'summary.json') == record['summary_sha256'] and summary['status'] == 'passed' and
            summary['process']['exit_code'] == 0, 'Native census process/summary differs')
    coverage_path = folder/'audit.json'
    require(sha(coverage_path) == report_pin(ledger, record, folder.relative_to(repo), 'audit.json'),
            'Pinned native census report differs')
    coverage = read(coverage_path); rows = {r['asset']:r for r in coverage['assets']}
    index = index_hashes(summary.get('input_hashes', summary.get('hashes')))
    stage = Path(summary['process']['arguments'][0]).parent
    guards = []; bindings = {r['asset']:r['sha256'] for r in document['current_binding_assets']}
    for candidate in scope:
        row = rows[candidate['path']]
        require(row['class_identity_preserved'] is True, 'Lifetime candidate class identity changed')
        for asset in (candidate['path'], row.get('mixin_set')):
            if not asset:continue
            relative = relative_asset(asset, Path('F:/LyraStarterGame'))
            path = repo/'Demos/UEPLyraIntegration/Overlay'/relative
            if not path.is_file():path = Path('F:/LyraStarterGame')/relative
            if asset == row.get('mixin_set'):
                require(asset in bindings and sha(path) == bindings[asset], 'Accepted current Mixin binding changed')
                guards.append(dict(asset=asset, path=str(path), current_sha256=sha(path),
                    provenance='accepted-source-disposition-binding-asset'))
            else:
                records = index.get(key(path), []) or [dict(r, path=str(path)) for r in index.get(key(stage/relative), [])]
                guards.append(dict(asset=asset, path=str(path), **source_guard(path, records)))
    return coverage, dict(status='passed', candidate_document_sha256=sha(migration/'candidate_dispositions.json'),
        accepted_source_review=dict(path=identity_path.relative_to(repo).as_posix(), sha256=sha(identity_path)),
        native_census_directory=record['directory'], summary_sha256=sha(folder/'summary.json'),
        report_sha256=sha(coverage_path), original_candidates=32, current_class_and_transport_guards=guards,
        unrelated_gameplay_semantic_gates_reexecuted=False)


def inspect(repo, current, initial):
    repo = Path(repo).resolve(); migration = repo/'Demos/UEPLyraIntegration/Migration'
    scripts = migration.parent/'Overlay/Content/Scripts'
    scope = [r for r in initial['assets'] if r['version'] == '0.10.0']
    require(len(scope) == 32 and [r['path'] for r in scope] ==
        [r['path'] for r in current['assets'] if r['version'] == '0.10.0'], 'Original 32 lifetime candidates required')
    path = migration/'candidate_dispositions.json'; document = read(path)
    coverage, census_gate = census_scope(repo, migration, scope, document)
    dispositions = {r['asset']:r for r in document['candidates']}
    modules = sorted({dispositions[r['path']]['effective_python_class'].rsplit('.',1)[0]
        for r in scope if dispositions[r['path']]['effective_python_class']})
    inventory = ownership({m:(scripts/Path(*m.split('.'))).with_suffix('.py').read_text(encoding='utf-8-sig') for m in modules})
    combined = combined_hud_job(repo, scripts)
    folder = repo/combined['directory']; native = read(folder/'summary.json')
    _, guards = source_guards(scripts, modules, native)
    combined['current_source_guards'] = guards
    combined['lifetime_cleanup'] = combined_cleanup({peer:read(folder/(peer+'.json')) for peer in native['processes']})
    combined['lifetime_boundaries'] = ['two-actual-travels', 'pawn-replacement', 'client-exit', 'rejoin', 'shutdown']
    combined['actual_travel_tested'] = True
    combined['_stage'] = Path(native['processes']['server']['arguments'][0]).parent
    jobs = [combined, action_touch_job(repo, migration, scripts), heal_job(repo, scripts)]
    preflight_path = repo/BASE/'preflight.json'; preflight = read(preflight_path)
    require(preflight['status'] == 'passed' and all(sha(row['path']) == row['sha256']
        for row in preflight['binary_source_guards']), 'Fresh SDK/game/official-source preflight differs')
    assets = owned_assets(repo, scope, coverage, dispositions, jobs)
    retained = [dispositions[r['path']] for r in scope if not dispositions[r['path']]['effective_python_class']]
    require(len(retained) == 2 and all(r['disposition'] == 'retained-native-cpp-touch-parent-forwarder' and
            r['original_entry_dispositions'] == {'direct-parent-forwarder-review':3} for r in retained),
            'Touch parent-only retention changed')
    provenance = []
    for batch, name in ((11,'CombinedNetwork01'), (17,'Network02')):
        _, ledger, _ = selected_record(migration, batch, name)
        provenance.extend(scope_provenance(repo, ledger['core_parent_commit']))
    for job in jobs:
        for field in list(job):
            if field.startswith('_'):del job[field]
    return dict(status='passed', criterion=REQUIREMENT, completion_proven=True,
        original_candidates=32, subscription_owning_candidates=16, source_reviewed_no_python_subscription_candidates=14,
        retained_native_parent_forwarders=retained, source_ownership_inventory=inventory,
        current_candidate_census=census_gate, candidate_document_sha256=sha(path),
        current_native_build_preflight=dict(path=preflight_path.relative_to(repo).as_posix(),
            sha256=sha(preflight_path), binary_source_guards=preflight['binary_source_guards']),
        current_policy_dependency_guards=guards, shared_scope_git_provenance=provenance,
        native_lifetime_runs=jobs, native_lifetime_runs_revalidated=3, referenced_lifetime_processes=8,
        fresh_native_processes=4, owned_candidate_asset_guards=assets,
        cpp_compile_executed=False, cook_package_executed=False, full_regression_executed=False,
        full_version_acceptance=False, full_migration_acceptance_proven=False,
        limits=[
            'The eight native processes cover distinct lifetime boundaries,not every asset/scenario combination. Touch tests use mounted same-class pairs and local typed messages;they do not claim actual touch-widget travel,physical touch or production placement.',
            'The complete nineteen-phase HUD record includes actual map changes and rejoin. Scope,delegate,team/init-state helper roots and pool/weapon sampler cleanup are checked from original raw reports using current frozen source.',
            'Fourteen candidates own no Python subscriptions in their frozen policy source. OpenMenu activates a native GameInstance-owned async action without Python callbacks;native GAS,timers,overlap transport and native C++ touch behavior retain their authored ownership.',
            'The two touch-region shells retain only three direct native-parent forwarders each. Current census/source retention evidence is reused without claiming their native C++ was migrated.',
            'Fresh current-SDK heal and touch captures replace the old unpinned heal Standalone report and the old touch observer with a changed imported fixture. Heal supplies seven original/Python pairs,including active Profile switch,native cancellation,end and timer cleanup. Touch supplies eight synchronized two-owner phases.',
            'Only this original lifetime criterion is accepted. Each-small-batch behavior/no-fallthrough,pixels,audio,hardware input,packaged and full Experience/version/release acceptance remain separate.'])


def verify_documentation(document, current, initial, repo):
    require(document.get('criterion') == REQUIREMENT and document.get('completion_proven') is True,
            'Exact original Widget/Actor lifetime criterion required')
    review = inspect(repo, current, initial)
    require(document.get('review', document) == review, 'Recorded Widget/Actor lifetime evidence differs from current proof')
    return dict(status='passed', criterion=REQUIREMENT, original_candidates=32,
                native_lifetime_runs_revalidated=3, referenced_lifetime_processes=8,
                fresh_native_processes=4, cpp_compile_executed=False, cook_package_executed=False)
