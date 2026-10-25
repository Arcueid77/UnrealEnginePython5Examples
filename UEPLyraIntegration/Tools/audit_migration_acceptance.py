"""Index original migration requirements; candidate status is never acceptance proof."""
import argparse
import hashlib
import json
from pathlib import Path
import re

COUNTS = (246, 182, 63, 11)
VERSIONS = {'0.9.0': 5, '0.10.0': 32, '0.11.0': 37, '0.12.0': 75, '0.13.0': 57, '0.14.0': 40}
CAPABILITIES = {'network_acceptance', 'packaged_runtime', 'packaged_runtime_verified',
    'pixels_tested', 'audio_playback_tested', 'audible_playback_accepted',
    'natural_animation_dispatch_tested', 'physical_input_tested', 'physical_touch_tested',
    'physical_shotgun_pickup_tested', 'real_elimination_gameplay_tested',
    'healthbar_specific_precompiled_caller_tested', 'production_placement_tested',
    'explicit_native_dead_actor_variant_tested', 'context_array_order_native_direct_tested',
    'spawn_failure_native_tested', 'commit_race_failure_native_tested',
    'normal_locomotion_input_state_machine_tested'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def requirements(text):
    """Read the original version checklists, retaining their exact source location."""
    version = None
    result = []
    for line_number, line in enumerate(text.splitlines(), 1):
        heading = re.match(r'^## (\d+\.\d+\.\d+)(?:\s|\s*[—-])', line)
        if heading:
            version = heading.group(1) if heading.group(1) in VERSIONS else None
        elif line.startswith('## '):
            version = None
        check = re.match(r'^- \[([ xX])\] (.+)', line)
        if version and check:
            result.append(dict(version=version, roadmap_line=line_number,
                original_checked=check.group(1).lower() == 'x', text=check.group(2),
                evidence_state='historical_claim_needs_source_and_evidence_review' if check.group(1).lower() == 'x' else 'unproven',
                completion_proven=False))
        elif version and result and result[-1]['version'] == version and line.startswith('  ') and not line.startswith('   '):
            result[-1]['text'] += ' '+line.strip()
    return result


def unverified(value, path=''):
    result = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = path+'.'+key if path else key
            if key in CAPABILITIES and item is False:
                result.append(dict(manifest_field=child, capability=key,
                    state='explicitly_unverified', mandatory_scope='requires_requirement_or_support_matrix_review'))
            elif key == 'replica_readiness_issue' and isinstance(item, dict) and item.get('status') == 'open_not_fixed':
                result.append(dict(manifest_field=child, capability='replica_readiness', state='unresolved_observation',
                    details=item, mandatory_scope='correctness_stability_review'))
            elif key != 'assets':
                result.extend(unverified(item, child))
    return result


def inspect(current, original, roadmap, *, acceptance_directory):
    counts = tuple(current[k] for k in ('runtime_candidates', 'configuration_only', 'retained', 'scope_review_candidates'))
    if counts != COUNTS:
        raise ValueError('original static scope changed')
    paths = [row['path'] for row in current['assets']]
    if len(paths) != 246 or len(set(paths)) != 246 or paths != [row['path'] for row in original['assets']]:
        raise ValueError('original 246 candidate paths/order changed')
    versions = {v: sum(row['version'] == v for row in current['assets']) for v in VERSIONS}
    if versions != VERSIONS:
        raise ValueError('original version assignment counts changed')
    if [row['version'] for row in current['assets']] != [row['version'] for row in original['assets']]:
        raise ValueError('original candidate version assignments changed')
    if current.get('migration_complete') is not False:
        raise ValueError('full migration completion is not proven by this index')
    checklists = requirements(roadmap)
    if set(row['version'] for row in checklists) != set(VERSIONS):
        raise ValueError('each original migration version needs its actual roadmap checklist')
    rows = []
    for asset in current['assets']:
        ledger = asset.get('evidence_ledger')
        rows.append(dict(path=asset['path'], version=asset['version'], status=asset['status'],
            declared_methods=asset.get('implemented_helpers', []), scope_review=asset.get('scope_review'),
            declared_evidence_run=asset.get('evidence_run'), declared_evidence_ledger=ledger,
            declared_ledger_exists=(acceptance_directory/ledger).is_file() if ledger else None,
            evidence_semantics_verified_by_this_audit=False, completion_proven=False))
    recorded_animation = current.get('footstep_pilot', {}).get('natural_animation_dispatch_tested') is True
    recorded_locomotion = current.get('footstep_pilot', {}).get('normal_locomotion_input_state_machine_tested') is True
    recorded_floor_pixels = current.get('footstep_pilot', {}).get('pixels_tested') is True
    next_task = ('Review remaining supported surface/lighting visual coverage, audible output, physical keyboard and multiplayer/package/version checklists. Bounded original-floor render attribution and actual-player Enhanced Input/AnimBP locomotion are already recorded separately.'
                 if recorded_locomotion and recorded_floor_pixels else
                 'Review visible footprint pixels, audible output, physical keyboard and remaining supported multiplayer/package/version checklists. Controlled animation and actual-player Enhanced Input/AnimBP locomotion are already recorded separately.'
                 if recorded_locomotion else
                 'Review normal movement-input/AnimBP locomotion, visible footprint pixels, audible output and the remaining original version checklists. Controlled native animation playback is already recorded separately.'
                 if recorded_animation else
                 'Inspect unchanged locomotion sequences and prove actual native animation playback reaches the migrated footstep policy through the original Notify/interface chain.')
    return dict(schema_version=1, status='passed', scope_check_passed=True,
        static_counts=list(COUNTS), version_counts=versions, original_paths_and_order_preserved=True,
        candidate_rows=rows, candidate_rows_not_accepted=sum(row['status'] == 'not_accepted' for row in rows),
        requirements=checklists, explicit_unverified_capabilities=unverified(current),
        full_migration_acceptance_proven=False, native_runtime_executed_by_this_tool=False,
        next_evidence_task=next_task,
        notes=['Candidate rows include implementations and explicit retained dispositions.',
               'A declared path, status, true flag or old checked box is an evidence lead, not a new runtime pass.',
               'False capability flags require scope review; prohibited behavior such as callback replay is not a missing test.',
               'RC tags, publication, additional configurations and game-project C++ remain separate scope.'])


def markdown(report):
    lines = ['# Migration acceptance review', '',
        'The original 246 candidate paths, order and version assignments are preserved.',
        'Zero `not_accepted` rows records bounded dispositions; full migration acceptance remains unproven.',
        'This index does not execute or semantically revalidate the referenced runtime evidence.', '',
        '| Version | Original candidates | Checklist requirements |', '| --- | ---: | ---: |']
    for version, count in report['version_counts'].items():
        lines.append(f"| {version} | {count} | {sum(r['version'] == version for r in report['requirements'])} |")
    lines.extend(['', '## Original checklist requirements', ''])
    for row in report['requirements']:
        lines.append(f"- `{row['version']}` — {row['text']} (ROADMAP.md:{row['roadmap_line']}; {row['evidence_state']}).")
    lines.extend(['', '## Explicit unverified capabilities', '',
        'These are recorded flags requiring requirement and platform review, not automatic new scope.', ''])
    groups = {}
    for row in report['explicit_unverified_capabilities']:
        groups.setdefault(row['manifest_field'].split('.')[0], []).append(row['capability'])
    for group, fields in groups.items():
        lines.append(f"- `{group}`: {', '.join(dict.fromkeys(fields))}.")
    lines.extend(['', '## Next evidence work', '', report['next_evidence_task'], '',
        'Recorded capabilities still need their linked semantic/source evidence reviewed; this index',
        'does not rerun them. Continue unresolved readiness observations and the original version scope.', ''])
    return '\n'.join(lines)


def attach_ui_failure_review(report,current,initial,repo,path):
    from audit_ui_failure_cancellation_acceptance import REQUIREMENT,verify_documentation
    path=Path(path);document=json.loads(path.read_text(encoding='utf-8-sig'))
    verified=verify_documentation(document,current,initial,repo)
    targets=[row for row in report['requirements'] if row['version']=='0.13.0' and row['text']==REQUIREMENT]
    if len(targets)!=1:raise ValueError('Exact original UI failure/cancellation criterion required')
    targets[0].update(completion_proven=True,evidence_state='native_ui_failure_and_cancellation_evidence_and_current_source_verified',
        evidence_artifact=str(path.resolve()),native_runtime_reexecuted=False,full_version_acceptance=False)
    report['ui_failure_cancellation_review']=verified
    report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))
    return verified


def attach_ui_lifetime_review(report,repo,path):
    from audit_ui_travel_lifetime_acceptance import REQUIREMENT,verify_documentation
    path=Path(path);verified=verify_documentation(json.loads(path.read_text(encoding='utf-8-sig')),repo)
    target=[row for row in report['requirements'] if row['version']=='0.13.0' and row['text']==REQUIREMENT]
    if len(target)!=1:raise ValueError('Exact original UI lifetime requirement required')
    target[0].update(completion_proven=True,evidence_state='paired_native_reopen_travel_state_and_callback_restoration_verified',evidence_artifact=str(path.resolve()),full_version_acceptance=False)
    report['ui_travel_lifetime_review']=verified;report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))

def attach_ui_navigation_review(report,current,initial,repo,path):
    from audit_ui_navigation_acceptance import REQUIREMENT,verify_documentation
    path=Path(path);verified=verify_documentation(json.loads(path.read_text(encoding='utf-8-sig')),current,initial,repo)
    target=[row for row in report['requirements'] if row['version']=='0.13.0' and row['text']==REQUIREMENT]
    if len(target)!=1:raise ValueError('Exact original navigation/settings/session/replay requirement required')
    target[0].update(completion_proven=True,evidence_state='native_navigation_settings_sessions_replay_comparisons_and_current_sources_verified',evidence_artifact=str(path.resolve()),full_migration_acceptance_proven=False)
    report['ui_navigation_review']=verified;report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))

def attach_ai_lifetime_review(report,current,initial,repo,path):
    from audit_ai_lifetime_acceptance import REQUIREMENT,verify_documentation
    path=Path(path);verified=verify_documentation(json.loads(path.read_text(encoding='utf-8-sig')),current,initial,repo)
    target=[row for row in report['requirements'] if row['version']=='0.12.0' and row['text']==REQUIREMENT]
    if len(target)!=1:raise ValueError('Exact original AI outcome/cancellation/lifetime requirement required')
    target[0].update(completion_proven=True,evidence_state='native_ai_eqs_outcomes_and_pawn_world_cancellation_with_collection_verified',evidence_artifact=str(path.resolve()),full_migration_acceptance_proven=False)
    report['ai_lifetime_review']=verified;report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))

def attach_effects_match_review(report,current,initial,repo,path):
    from audit_effects_match_acceptance import REQUIREMENT,verify_documentation
    path=Path(path);verified=verify_documentation(json.loads(path.read_text(encoding='utf-8-sig')),current,initial,repo)
    target=[r for r in report['requirements'] if r['version']=='0.12.0' and r['text']==REQUIREMENT]
    if len(target)!=1:raise ValueError('Exact original effects/audio/phase/scoring/notification requirement required')
    target[0].update(completion_proven=True,evidence_state='native_effect_audio_phase_scoring_notification_checkpoints_and_current_sources_verified',evidence_artifact=str(path.resolve()),full_migration_acceptance_proven=False)
    report['effects_match_review']=verified;report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))

def attach_match_network_review(report,repo,path):
    from audit_match_network_acceptance import REQUIREMENT,verify_documentation
    path=Path(path);verified=verify_documentation(json.loads(path.read_text(encoding='utf-8-sig')),repo)
    target=[r for r in report['requirements'] if r['version']=='0.12.0' and r['text']==REQUIREMENT]
    if len(target)!=1:raise ValueError('Exact original multi-client score/phase/notification requirement required')
    target[0].update(completion_proven=True,evidence_state='native_multi_client_score_phase_local_notification_cleanup_and_current_sources_verified',evidence_artifact=str(path.resolve()),full_migration_acceptance_proven=False)
    report['match_network_review']=verified;report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))

def attach_playable_startup_review(report,repo,path):
    from audit_playable_startup_acceptance import REQUIREMENT,verify_documentation
    path=Path(path);verified=verify_documentation(json.loads(path.read_text(encoding='utf-8-sig')),repo)
    target=[r for r in report['requirements'] if r['version']=='0.9.0' and r['text']==REQUIREMENT]
    if len(target)!=1:raise ValueError('Exact original normal-startup/explicit-probe requirement required')
    target[0].update(completion_proven=True,evidence_state='native_normal_no_probe_observation_and_focused_rendered_probe_cleanup_and_sources_verified',evidence_artifact=str(path.resolve()),full_migration_acceptance_proven=False)
    report['playable_startup_review']=verified;report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))

def attach_world_interaction_review(report,current,initial,repo,path):
    from audit_world_interaction_acceptance import REQUIREMENT,verify_documentation
    path=Path(path);verified=verify_documentation(json.loads(path.read_text(encoding='utf-8-sig')),current,initial,repo)
    targets=[row for row in report['requirements'] if row['version']=='0.10.0' and row['text']==REQUIREMENT]
    if len(targets)!=1:raise ValueError('Exact original pickup/device interaction requirement required')
    targets[0].update(completion_proven=True,evidence_state='native_pickup_rejection_cooldown_interaction_effects_and_two_owner_ui_claim_sources_verified',
        evidence_artifact=str(path.resolve()),full_migration_acceptance_proven=False)
    report['world_interaction_review']=verified;report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))


def attach_ability_identity_review(report,current,initial,repo,path):
    from audit_ability_identity_acceptance import REQUIREMENT,verify_documentation
    path=Path(path);verified=verify_documentation(json.loads(path.read_text(encoding='utf-8-sig')),current,initial,repo)
    targets=[row for row in report['requirements'] if row['version']=='0.11.0' and row['text']==REQUIREMENT]
    if len(targets)!=1:raise ValueError('Exact original UObject identity/native execution-boundary requirement required')
    targets[0].update(completion_proven=True,evidence_state='native_original_class_identity_authority_prediction_replication_boundaries_and_current_sources_verified',
        evidence_artifact=str(path.resolve()),full_migration_acceptance_proven=False)
    report['ability_identity_review']=verified;report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--original-inventory', required=True)
    parser.add_argument('--roadmap', required=True)
    parser.add_argument('--result', required=True)
    parser.add_argument('--markdown')
    parser.add_argument('--static-scope-review', help='Verify per-asset exclusion reasons;never accepts migrated gameplay')
    parser.add_argument('--candidate-dispositions', help='Verify current per-candidate source/retention coverage;does not accept gameplay or the whole migration')
    parser.add_argument('--ui-failure-cancellation-review',help='Recheck pinned native UI failure/cancel evidence;accepts only that exact original criterion')
    parser.add_argument('--ui-travel-lifetime-review',help='Recheck paired native reopen/travel callbacks and state;accepts only the original lifetime criterion')
    parser.add_argument('--ui-navigation-review',help='Recheck original UI navigation,settings stores,session results and replay controls against source-bound native evidence')
    parser.add_argument('--ai-lifetime-review',help='Recheck original AI/EQS outcomes and real native cancellation/collection on Pawn destruction and world travel')
    parser.add_argument('--effects-match-review',help='Recheck all original non-AI0.12 effect/audio/phase/scoring/notification checkpoints against pinned native evidence and current source')
    parser.add_argument('--match-network-review',help='Recheck original two-client score/phase/local notifications and cleanup for TDM and physical control-point capture')
    parser.add_argument('--playable-startup-review',help='Recheck original no-test-flag startup observation and explicit rendered weapon probe timeout/cleanup boundary')
    parser.add_argument('--world-interaction-review',help='Recheck original pickup/device success,rejection,cooldown,effect and two-owner UI/claim evidence against current source')
    parser.add_argument('--ability-identity-review',help='Recheck all original0.11 UObject identities and required native authority,prediction,replication boundaries')
    args = parser.parse_args()
    manifest = Path(args.manifest)
    current = json.loads(manifest.read_text(encoding='utf-8-sig'))
    initial = json.loads(Path(args.original_inventory).read_text(encoding='utf-8-sig'))
    report = inspect(current, initial,
        Path(args.roadmap).read_text(encoding='utf-8-sig'), acceptance_directory=manifest.parent/'Acceptance')
    report['inputs'] = [dict(path=str(Path(p).resolve()), sha256=digest(p))
                        for p in (args.manifest, args.original_inventory, args.roadmap)]
    if args.static_scope_review:
        from audit_static_scope_dispositions import verify_documentation
        path = Path(args.static_scope_review)
        verified = verify_documentation(json.loads(path.read_text(encoding='utf-8-sig')), current, initial)
        target = [row for row in report['requirements'] if row['version'] == '0.14.0' and row['text'] ==
            'Configuration-only BP shells and animation/editor/test exclusions have documented reasons. Game-project C++ migration stays a separate phase.']
        if len(target) != 1:
            raise ValueError('Exact original configuration/exclusion reason requirement required')
        target[0].update(completion_proven=True, evidence_state='per_asset_reasons_and_current_reference_stage_copies_verified',
            evidence_artifact=str(path.resolve()), runtime_acceptance=False)
        report['static_scope_reason_review'] = verified
        report['inputs'].append(dict(path=str(path.resolve()), sha256=digest(path)))
    if args.candidate_dispositions:
        from audit_candidate_dispositions import verify_documentation as verify_candidates, REQUIREMENT
        path = Path(args.candidate_dispositions)
        verified = verify_candidates(json.loads(path.read_text(encoding='utf-8-sig')), current, initial, manifest.resolve().parents[3])
        target = [row for row in report['requirements'] if row['version']=='0.14.0' and row['text']==REQUIREMENT]
        if len(target)!=1:
            raise ValueError('Exact original candidate disposition requirement required')
        target[0].update(completion_proven=True,evidence_state='current_candidate_source_binding_retention_and_named_issue_dispositions_verified',
            evidence_artifact=str(path.resolve()),runtime_acceptance=False)
        report['candidate_disposition_review']=verified
        report['inputs'].append(dict(path=str(path.resolve()),sha256=digest(path)))
        report['next_evidence_task']='Review the remaining original0.9-0.14 gameplay,presentation,lifecycle,network and package requirements against their actual native evidence. The named Pawn/ASC readiness issue remains open;inventory disposition does not close these requirements.'
    if args.ui_failure_cancellation_review:
        attach_ui_failure_review(report,current,initial,manifest.resolve().parents[3],args.ui_failure_cancellation_review)
    if args.ui_travel_lifetime_review:
        attach_ui_lifetime_review(report,manifest.resolve().parents[3],args.ui_travel_lifetime_review)
    if args.ui_navigation_review:
        attach_ui_navigation_review(report,current,initial,manifest.resolve().parents[3],args.ui_navigation_review)
    if args.ai_lifetime_review:
        attach_ai_lifetime_review(report,current,initial,manifest.resolve().parents[3],args.ai_lifetime_review)
    if args.effects_match_review:
        attach_effects_match_review(report,current,initial,manifest.resolve().parents[3],args.effects_match_review)
    if args.match_network_review:
        attach_match_network_review(report,manifest.resolve().parents[3],args.match_network_review)
    if args.playable_startup_review:
        attach_playable_startup_review(report,manifest.resolve().parents[3],args.playable_startup_review)
    if args.world_interaction_review:
        attach_world_interaction_review(report,current,initial,manifest.resolve().parents[3],args.world_interaction_review)
    if args.ability_identity_review:
        attach_ability_identity_review(report,current,initial,manifest.resolve().parents[3],args.ability_identity_review)
    Path(args.result).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if args.markdown:
        Path(args.markdown).write_text(markdown(report), encoding='utf-8')
    print(json.dumps(dict(status=report['status'], candidates=len(report['candidate_rows']),
        requirements=len(report['requirements']), requirements_proven=sum(r['completion_proven'] for r in report['requirements']),
        explicitly_unverified=len(report['explicit_unverified_capabilities']),
        full_migration_acceptance_proven=False)))


if __name__ == '__main__':
    main()
