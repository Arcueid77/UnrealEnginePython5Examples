"""Bounded original bomb collision, latent lifecycle and inherited Profile gate."""
import argparse, json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require


def validate(report):
    require(report['status'] == 'passed' and report['error'] is None, 'base bomb native validation failed')
    require(report['mode'] in ('Baseline', 'Python', 'BlueprintFallback'), 'unknown base bomb mode')
    for key in ('full_acceptance', 'network_acceptance', 'packaged_runtime', 'pixels_tested', 'audio_playback_tested', 'callbacks_replayed', 'native_delays_replaced', 'global_rng_replaced'):
        require(report[key] is False, 'base bomb overclaim: '+key)
    require(report['cleanup_complete'], 'base bomb owned cleanup missing')
    cases = report['collision_cases']
    require([r['name'] for r in cases] == ['empty', 'static', 'destructible', 'pickup', 'asc'], 'native collision matrix incomplete')
    require([r['space_blocked'] for r in cases] == [False, True, True, True, False], 'original collision blocking precedence differs')
    require([r['spawned'] for r in cases] == [True, False, True, True, True], 'static-only fireball suppression differs')
    require([r['instance_delta'] for r in cases] == [1, 0, 1, 1, 1], 'native ISM instance outcome differs')
    require(cases[2]['target_destroyed'] and cases[3]['target_destroyed'], 'destructible/pickup destruction missing')
    require(cases[4]['native_query_contains_pawn'] and cases[4]['health_after'] <= cases[4]['health_before'], 'native ASC collision/GE outcome missing')
    require(report['snapshot']['found'] and report['snapshot']['radius'] == int(report['snapshot']['attribute']), 'native BombRange attribute snapshot differs')
    require(report['snapshot']['missing_keeps_radius'] == 7, 'missing BombRange must keep prior radius')
    require(report['bonus']['zero_count'] == 0 and report['bonus']['guaranteed_count'] == 1 and report['bonus']['original_effect_class'] and report['bonus']['original_location'], 'native bonus strict chance/class/location differs')
    require(report['authority_rep_does_not_update_visuals'], 'authority repnotify must not run remote visuals')
    require(report['overlap']['ignored_initially'] and report['overlap']['restored_after_native_end'], 'native end-overlap collision restoration missing')
    require(report['short_arrays']['blocked_length'] == 0 and report['short_arrays']['radius_length'] == 0, 'Array_Set false must not resize arrays')
    natural = report['natural']
    require(natural['main_destroyed'] and natural['chain_destroyed'] and natural['main_radius_seen'] == 2 and natural['chain_radius_seen'] == 1, 'native fuse/chain propagation/destruction incomplete')
    require(natural['chain_fuse_extinguished'] and natural['chain_minimum_burn_seconds'] >= .45, 'chain minimum burn delay changed')
    require(natural['main_duration'] >= .5 and natural['bombs_remaining_restored'], 'natural fuse or native bomb refund missing')
    require(report['child_visuals_observed'], 'accepted child display inheritance missing')
    if report['mode'] != 'Baseline':
        prefix = 'python_' if report['mode'] == 'Python' else 'fallback_'
        other = 'fallback_' if report['mode'] == 'Python' else 'python_'
        require(all(report['counts'][prefix+k] > 0 and report['counts'][other+k] == 0 for k in ('add', 'expand', 'snapshot', 'bonus', 'rep', 'begin', 'destroyed', 'overlap', 'trigger', 'increment', 'propagated', 'hover', 'fuse')), 'selected full base bomb Profile missing')
    return dict(status='passed', mode=report['mode'], native_collision_cases=5, native_chained_bombs=2, full_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
