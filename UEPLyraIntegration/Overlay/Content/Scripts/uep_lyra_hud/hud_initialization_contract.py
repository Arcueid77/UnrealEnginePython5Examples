"""Independent original/Python native initialization for five HUD candidates."""
import argparse
import json
from pathlib import Path

KINDS = ('action-base', 'action-mobile', 'dash', 'failure', 'progress')


def require(value, message):
    if not value:raise ValueError(message)


def validate(report):
    require(report['status'] == 'passed' and report['error'] is None, 'HUD initialization failed')
    require(report['selection_before_native_create'] and not report['profile_changed_after_create'] and
            not report['lifecycle_or_resume_replayed'], 'Independent native initialization provenance missing')
    require([r['kind'] for r in report['pairs']] == list(KINDS), 'All five original HUD candidates required')
    identities = set()
    for pair in report['pairs']:
        rows = pair['creations']
        require([r['profile'] for r in rows] == ['BlueprintFallback', 'Python'], 'Original/Python order differs')
        require(rows[0]['initial'] == rows[1]['initial'] and pair['mounted'][0] == pair['mounted'][1],
                'Independent original/Python initialization or mounted state differs: '+pair['kind'])
        for row in rows:
            python = row['profile'] == 'Python'
            require(row['effective_profile'] == row['profile'] and row['class'] == pair['class'], 'Native class/Profile differs')
            require(row['python_scope_open'] is python and row['original_proxy_active'] is (not python) and
                    row['python_scopes_created'] == int(python), 'Initialization entered the wrong policy/listener owner')
            require(row['widget'] not in identities, 'HUD initialization reused an existing native widget')
            identities.add(row['widget'])
    require(len(identities) == 10 and report['defaults_restored'] and report['released_roots'] == 10 and
            report['inactive_original_proxies'] == 5 and report['native_player_state_unchanged'], 'Native HUD cleanup/restore incomplete')
    for row in report['owned_cleanup']:
        require(row['active_before'] == row['active_after'], 'HUD test retained an owned subscription')
    for value in report['shutdown'].values():
        require(value['active_count'] == 0 and value['scopes_created'] == value['scopes_closed'] and
                value['errors'] == [], 'Production HUD scope survived interpreter shutdown')
    require(not report['full_acceptance'] and not report['network_acceptance'] and not report['packaged_runtime'],
            'Initialization proof cannot accept a version or another runtime mode')
    return dict(status='passed', independent_native_initialization=True, candidate_pairs=5, native_creations=10,
                full_acceptance=False, network_acceptance=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
