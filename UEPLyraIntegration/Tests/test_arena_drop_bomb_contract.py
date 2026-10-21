import copy
import unittest
from uep_lyra_abilities.arena_drop_bomb_contract import FAILURE, GRID, validate


def report(mode='Python'):
    prefix = 'python_' if mode == 'Python' else 'fallback_'
    counts = {p+k: (2 if k in ('activate', 'spawn_end') else 3) if p == prefix else 0
              for p in ('python_', 'fallback_') for k in ('location', 'can', 'activate', 'spawn_end')}
    drop = dict(request_accepted=True, new_bomb_count=1, original_standard_class=True, expected_location=True,
        original_instigator=True, remaining_before=1., remaining_after=0., ability_active_after_spawn=False,
        montage_keeps_playing_after_end=True)
    return dict(status='passed', error=None, mode=mode, full_acceptance=False, network_acceptance=False,
        packaged_runtime=False, pixels_tested=False, audio_playback_tested=False, physical_input_tested=False,
        callbacks_replayed=False, native_tasks_replaced=False, spawn_failure_native_tested=False,
        commit_race_failure_native_tested=False, cleanup_complete=True, grid_cases=copy.deepcopy(GRID),
        free_query=dict(allowed=True, tags=[]), occupied_query=dict(allowed=False, tags=[FAILURE]),
        drops=[copy.deepcopy(drop), copy.deepcopy(drop)],
        cost_denial=dict(request_accepted=False, new_bomb_count=0, remaining=0.),
        occupancy_denial=dict(request_accepted=False, new_bomb_count=0, remaining=1.),
        natural=dict(both_bombs_destroyed=True, remaining_after_refund=1., first_destroy_seconds=2.4),
        native_request_entry='ASC.TryActivateAbilityByClass', counts=counts)


class ArenaDropBombContractTests(unittest.TestCase):
    def test_original_and_both_profiles(self):
        for mode in ('Baseline', 'Python', 'BlueprintFallback'):
            self.assertEqual(validate(report(mode))['native_successful_drops'], 2)

    def test_negative_half_tie_grid_behavior_required(self):
        value = report()
        value['grid_cases'][2][1] = -100.
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_authored_failure_tag_required(self):
        value = report()
        value['occupied_query']['tags'] = []
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_cost_and_spawn_end_are_required(self):
        for key, replacement in (('remaining_after', 1.), ('ability_active_after_spawn', True), ('original_instigator', False)):
            value = report()
            value['drops'][0][key] = replacement
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_native_montage_must_survive_ability_end(self):
        value = report()
        value['drops'][0]['montage_keeps_playing_after_end'] = False
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_denied_requests_must_not_consume_cost_or_start_tasks(self):
        value = report()
        value['occupancy_denial']['remaining'] = 0.
        with self.assertRaises(RuntimeError):
            validate(value)
        value = report()
        value['counts']['python_activate'] = 3
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_original_fuse_refund_and_reactivation_required(self):
        value = report()
        value['natural']['both_bombs_destroyed'] = False
        with self.assertRaises(RuntimeError):
            validate(value)

    def test_network_input_and_unrun_failure_claims_are_rejected(self):
        for key in ('physical_input_tested', 'network_acceptance', 'spawn_failure_native_tested', 'commit_race_failure_native_tested', 'callbacks_replayed'):
            value = report()
            value[key] = True
            with self.assertRaises(RuntimeError):
                validate(value)
