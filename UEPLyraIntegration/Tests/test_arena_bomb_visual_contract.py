import copy
import unittest
from uep_lyra_world.arena_bomb_visual_contract import EXPECTED, validate


def report(mode='Python'):
    prefix = 'python_' if mode == 'Python' else 'fallback_'
    counts = {p+k: int(p == prefix) for p in ('python_', 'fallback_') for k in ('construct', 'visuals')}
    return dict(status='passed', error=None, mode=mode, full_acceptance=False,
        network_acceptance=False, packaged_runtime=False, pixels_tested=False,
        audio_playback_tested=False, callbacks_replayed=False, native_fuse_replaced=False,
        cleanup_complete=True, materials=dict(same_mid_on_both_meshes=True, lifespan=2., real_time_bounded=True),
        cases=[dict(positions=copy.deepcopy(v), niagara_active=False) for v in EXPECTED],
        natural=dict(fuse_was_lit=True, fuse_extinguished=True, radius_seen=2, destroyed=True, elapsed_game_seconds=1.),
        counts=counts, natural_counts=counts)


class ArenaBombVisualContractTests(unittest.TestCase):
    def test_original_and_both_profiles(self):
        for mode in ('Baseline', 'Python', 'BlueprintFallback'):
            self.assertEqual(validate(report(mode))['native_array_cases'], 6)

    def test_accumulated_local_array_rejected(self):
        value = report()
        value['cases'][3]['positions'] = [[100., 0., 50.]]
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_global_time_substitution_or_split_mid_rejected(self):
        for key in ('real_time_bounded', 'same_mid_on_both_meshes'):
            value = report()
            value['materials'][key] = False
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_manual_calls_cannot_substitute_for_natural_fuse(self):
        value = report()
        value['natural_counts']['python_visuals'] = 0
        with self.assertRaises(RuntimeError):
            validate(value)
        value = report()
        value['natural']['destroyed'] = False
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_unverified_audio_pixels_or_network_claim_rejected(self):
        for key in ('audio_playback_tested', 'pixels_tested', 'network_acceptance', 'callbacks_replayed'):
            value = report()
            value[key] = True
            with self.assertRaises(RuntimeError):
                validate(value)
