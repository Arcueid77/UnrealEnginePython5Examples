"""Original/Python native widget creation; no post-create Profile substitution."""
import argparse
import json
from pathlib import Path

PROFILES = ('BlueprintFallback', 'Python')


def require(value, message):
    if not value:
        raise ValueError(message)


def validate(report):
    require(report['status'] == 'passed' and report['error'] is None, 'Native quickbar initialization failed')
    require(report['profile_selected_before_native_create'] is True and
            report['native_create_api'] == 'WidgetBlueprintLibrary.Create' and
            report['native_initialization_parity_tested'] is True, 'Native creation provenance missing')
    for flag in ('lifecycle_event_replayed', 'profile_changed_after_create', 'resume_entry_called',
                 'native_player_state_written', 'full_acceptance', 'network_acceptance', 'packaged_runtime'):
        require(report[flag] is False, 'Unsupported quickbar initialization claim: '+flag)
    require(report['original_defaults_restored'] and report['test_roots_released'] and
            report['owned_widgets_removed'] and report['native_player_state_unchanged'], 'Native cleanup/restore missing')
    require(len(report['pairs']) == 3, 'All three original slot configurations required')
    widgets = set()
    for index, pair in enumerate(report['pairs']):
        require(pair['slot_index'] == index and [r['profile'] for r in pair['creations']] == list(PROFILES),
                'Native slot/Profile creation matrix differs')
        require(pair['initial_states_equal'] and pair['mounted_states_equal'] and
                pair['creations'][0]['initial'] == pair['creations'][1]['initial'], 'Native initial states differ')
        require(pair['mounted'][0] == pair['mounted'][1], 'Native mounted slot states differ')
        require(pair['mounted'][0]['index'] == index and pair['mounted'][0]['empty'] is (index != 0),
                'Native equipped/empty slot context missing')
        for row in pair['creations']:
            python = row['profile'] == 'Python'
            require(row['class'] == '/ShooterCore/UserInterface/HUD/W_QuickBarSlot.W_QuickBarSlot_C' and
                    row['effective_profile'] == row['profile'] and row['initial']['index'] == index,
                    'Native class/Profile/slot configuration changed')
            require(row['selected_before_create'] is True and row['python_scope_open'] is python and
                    row['original_proxy_active'] == [not python, not python], 'OnInitialized selected the wrong owner')
            require(row['python_counter_delta'] == dict(slot_updates=int(python), scopes_created=int(python)),
                    'Original initialization entered Python or Python initialization fell through')
            require(row['widget'] not in widgets, 'Native widget creation reused an existing instance')
            widgets.add(row['widget'])
    cleanup = report['owned_cleanup']
    require(cleanup['python_active_after'] == cleanup['python_active_before'] and
            cleanup['original_proxies_inactive'] == 6 and cleanup['released_roots'] == 6,
            'Native test-owned subscription or root survived removal')
    final = report['shutdown']
    require(final['active_count'] == 0 and final['scopes_created'] == final['scopes_closed'] and
            final['errors'] == [] and final['pool_lifetime']['active_count'] == 0 and
            final['pool_lifetime']['ticker_active'] is False, 'Production quickbar subscriptions survived shutdown')
    return dict(status='passed', native_initialization_parity_tested=True, slot_pairs=3,
                native_widget_creations=6, full_acceptance=False, network_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--report', required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
