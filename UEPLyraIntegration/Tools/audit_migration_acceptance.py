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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--original-inventory', required=True)
    parser.add_argument('--roadmap', required=True)
    parser.add_argument('--result', required=True)
    parser.add_argument('--markdown')
    args = parser.parse_args()
    manifest = Path(args.manifest)
    report = inspect(json.loads(manifest.read_text(encoding='utf-8-sig')),
        json.loads(Path(args.original_inventory).read_text(encoding='utf-8-sig')),
        Path(args.roadmap).read_text(encoding='utf-8-sig'), acceptance_directory=manifest.parent/'Acceptance')
    report['inputs'] = [dict(path=str(Path(p).resolve()), sha256=digest(p))
                        for p in (args.manifest, args.original_inventory, args.roadmap)]
    Path(args.result).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if args.markdown:
        Path(args.markdown).write_text(markdown(report), encoding='utf-8')
    print(json.dumps(dict(status=report['status'], candidates=len(report['candidate_rows']),
        requirements=len(report['requirements']), explicitly_unverified=len(report['explicit_unverified_capabilities']),
        full_migration_acceptance_proven=False)))


if __name__ == '__main__':
    main()
