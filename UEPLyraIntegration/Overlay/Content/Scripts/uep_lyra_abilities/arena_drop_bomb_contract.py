"""Original Arena grid, GAS cost/occupancy denial and native spawn lifecycle gate."""
import argparse, json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

GRID = [[0., 0., 0.], [0., 0., 0.], [100., 0., 0.], [200., -100., 0.], [-100., 100., 0.], [-200., 300., 0.]]
FAILURE = 'Ability.ActivateFail.CellAlreadyContainsBomb'


def validate(report):
    require(report['status'] == 'passed' and report['error'] is None and report['mode'] in ('Baseline', 'Python', 'BlueprintFallback'), 'drop bomb native validation failed')
    for key in ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested', 'audio_playback_tested', 'physical_input_tested', 'callbacks_replayed', 'native_tasks_replaced', 'spawn_failure_native_tested', 'commit_race_failure_native_tested'):
        require(report[key] is False, 'drop ability overclaim: '+key)
    require(report['cleanup_complete'], 'drop ability owned cleanup missing')
    require(report['grid_cases'] == GRID, 'native grid snap tie/negative/Z projection differs')
    require(report['free_query'] == dict(allowed=True, tags=[]), 'free native cell query differs')
    require(report['occupied_query'] == dict(allowed=False, tags=[FAILURE]), 'original occupied-cell failure tag missing')
    require(len(report['drops']) == 2, 'native successful reactivation missing')
    for row in report['drops']:
        require(row['request_accepted'] and row['new_bomb_count'] == 1 and row['original_standard_class'] and row['expected_location'] and row['original_instigator'], 'original server native spawn task differs')
        require(row['remaining_before'] == 1. and row['remaining_after'] == 0. and not row['ability_active_after_spawn'], 'native cost or spawn-success ability end differs')
        require(row['montage_keeps_playing_after_end'], 'original bStopWhenAbilityEnds=false behavior differs')
    require(not report['cost_denial']['request_accepted'] and report['cost_denial']['new_bomb_count'] == 0 and report['cost_denial']['remaining'] == 0., 'native empty-cost denial differs')
    require(not report['occupancy_denial']['request_accepted'] and report['occupancy_denial']['new_bomb_count'] == 0 and report['occupancy_denial']['remaining'] == 1., 'native occupied-cell denial changed cost/spawn')
    require(report['natural']['both_bombs_destroyed'] and report['natural']['remaining_after_refund'] == 1. and report['natural']['first_destroy_seconds'] >= 1.8, 'natural original fuse/destruction/refund missing')
    require(report['native_request_entry'] == 'ASC.TryActivateAbilityByClass', 'activation callback must not be replayed')
    if report['mode'] != 'Baseline':
        prefix = 'python_' if report['mode'] == 'Python' else 'fallback_'
        other = 'fallback_' if report['mode'] == 'Python' else 'python_'
        for key in ('location', 'can', 'activate', 'spawn_end'):
            require(report['counts'][prefix+key] > 0 and report['counts'][other+key] == 0, 'selected drop ability Profile missing')
        require(report['counts'][prefix+'activate'] == report['counts'][prefix+'spawn_end'] == 2, 'denied requests must not activate native tasks')
    return dict(status='passed', mode=report['mode'], native_grid_cases=6, native_successful_drops=2, full_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
