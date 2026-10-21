import unittest
from uep_lyra_world.arena_bomb_base_contract import validate


def report(mode='Python'):
    keys = ('add', 'expand', 'snapshot', 'bonus', 'rep', 'begin', 'destroyed', 'overlap', 'trigger', 'increment', 'propagated', 'hover', 'fuse')
    prefix = 'python_' if mode == 'Python' else 'fallback_'
    counts = {p+k: int(p == prefix) for p in ('python_', 'fallback_') for k in keys}
    cases = [dict(name=name, space_blocked=blocked, spawned=spawned, instance_delta=int(spawned), target_destroyed=name in ('destructible', 'pickup'))
        for name, blocked, spawned in (('empty', False, True), ('static', True, False), ('destructible', True, True), ('pickup', True, True), ('asc', False, True))]
    cases[-1].update(native_query_contains_pawn=True, health_before=100., health_after=0.)
    return dict(status='passed', error=None, mode=mode, full_acceptance=False, network_acceptance=False, packaged_runtime=False, pixels_tested=False, audio_playback_tested=False, callbacks_replayed=False, native_delays_replaced=False, global_rng_replaced=False,
        cleanup_complete=True, collision_cases=cases, snapshot=dict(found=True, radius=2, attribute=2., missing_keeps_radius=7),
        bonus=dict(zero_count=0, guaranteed_count=1, original_effect_class=True, original_location=True), authority_rep_does_not_update_visuals=True,
        overlap=dict(ignored_initially=True, restored_after_native_end=True), short_arrays=dict(blocked_length=0, radius_length=0),
        natural=dict(main_destroyed=True, chain_destroyed=True, main_radius_seen=2, chain_radius_seen=1, chain_fuse_extinguished=True, chain_minimum_burn_seconds=.5, main_duration=1., bombs_remaining_restored=True),
        child_visuals_observed=True, counts=counts)


class ArenaBombBaseContractTests(unittest.TestCase):
    def test_original_and_both_profiles(self):
        for mode in ('Baseline', 'Python', 'BlueprintFallback'):
            self.assertEqual(validate(report(mode))['native_collision_cases'], 5)

    def test_destructible_must_not_suppress_its_fireball(self):
        value = report()
        value['collision_cases'][2]['spawned'] = False
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_real_collision_and_end_overlap_required(self):
        for path in (('collision_cases', None), ('overlap', 'restored_after_native_end')):
            value = report()
            if path[0] == 'collision_cases':
                value['collision_cases'][-1]['native_query_contains_pawn'] = False
            else:
                value[path[0]][path[1]] = False
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_natural_chain_and_minimum_burn_are_required(self):
        for key, replacement in (('chain_destroyed', False), ('chain_fuse_extinguished', False), ('chain_minimum_burn_seconds', .1), ('bombs_remaining_restored', False)):
            value = report()
            value['natural'][key] = replacement
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_full_family_including_destroy_and_macro_query_required(self):
        for key in ('python_destroyed', 'python_fuse', 'python_overlap', 'python_rep'):
            value = report()
            value['counts'][key] = 0
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_native_array_no_resize_and_missing_attribute_semantics_required(self):
        value = report()
        value['short_arrays']['blocked_length'] = 4
        with self.assertRaises(RuntimeError):
            validate(value)
        value = report()
        value['snapshot']['missing_keeps_radius'] = 0
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_broader_claim_or_callback_replay_rejected(self):
        for key in ('network_acceptance', 'pixels_tested', 'packaged_runtime', 'callbacks_replayed', 'native_delays_replaced'):
            value = report()
            value[key] = True
            with self.assertRaises(RuntimeError):
                validate(value)
