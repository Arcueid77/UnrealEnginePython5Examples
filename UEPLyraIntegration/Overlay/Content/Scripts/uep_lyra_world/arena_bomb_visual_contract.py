"""Independent standard-bomb material, array and native-fuse evidence gate."""
import argparse, json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

EXPECTED = [[], [[100., 0., 50.], [200., 0., 50.], [-100., 0., 50.], [0., 100., 50.], [0., 200., 50.], [0., -100., 50.]],
            [[100., 0., 50.], [200., 0., 50.]], [], [[0., 0., 50.]], [[-200., 300., 50.], [-400., 600., 50.]]]


def validate(report):
    require(report['status'] == 'passed' and report['error'] is None, 'bomb visual native validation failed')
    require(report['mode'] in ('Baseline', 'Python', 'BlueprintFallback'), 'unknown bomb visual mode')
    for key in ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested', 'audio_playback_tested', 'callbacks_replayed', 'native_fuse_replaced'):
        require(report[key] is False, 'bomb visual overclaim: '+key)
    require(report['cleanup_complete'], 'bomb visual owned cleanup missing')
    materials = report['materials']
    require(materials['same_mid_on_both_meshes'] and materials['lifespan'] == 2. and materials['real_time_bounded'], 'bomb construction MID/real-time/lifespan differs')
    require([row['positions'] for row in report['cases']] == EXPECTED, 'inclusive range/local reset/AddUnique/direction order differs')
    # The owned far-away fixtures are culled by the unmodified Niagara system.
    require([row['niagara_active'] for row in report['cases']] == [False]*6, 'original offscreen Niagara culling state differs')
    natural = report['natural']
    require(natural['fuse_was_lit'] and natural['fuse_extinguished'] and natural['radius_seen'] >= 1 and natural['destroyed'], 'native fuse/propagation/destruction path missing')
    require(.4 <= natural['elapsed_game_seconds'] <= 5., 'native minimum burn/propagation timing differs')
    if report['mode'] != 'Baseline':
        prefix = 'python_' if report['mode'] == 'Python' else 'fallback_'
        other = 'fallback_' if report['mode'] == 'Python' else 'python_'
        for key in ('construct', 'visuals'):
            require(report['counts'][prefix+key] > 0 and report['counts'][other+key] == 0, 'selected bomb visual Profile missing')
        require(report['natural_counts'][prefix+'visuals'] > 0, 'natural parent fuse never called child visual Profile')
    return dict(status='passed', mode=report['mode'], native_array_cases=len(EXPECTED), full_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
