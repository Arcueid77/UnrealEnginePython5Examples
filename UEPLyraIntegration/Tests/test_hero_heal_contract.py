"""Reject missing Hero Heal native paths; synthetic report models only."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import hero_heal_contract as gate


def report():
    result = dict(status="passed", error=None, original_player_restored=True, original_ability_specs_restored=True,
        fixture_native_asc_grant_activate_and_input_api=True, cases=[],
        policy_shutdown=dict(active_count=0, scopes_created=8, scopes_closed=8, errors=[]), foreign_lock_regressions=[])
    for name in ("montage-end", "state-end", "profile-teardown"):
        result["foreign_lock_regressions"].append(dict(name=name, external_lock_added_with_native_api=True,
            external_lock_preserved_after_native_end=True, external_lock_released_once_restores_baseline=True,
            state_cleanup_preserved_external_lock=True, tasks_after_end=0, effects_after_end=0, health_after=80., no_late_callbacks=True,
            counters=dict(movement_locks=1, movement_unlocks=1, scopes_created=1, scopes_closed=1)))
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_or_enhanced_input_tested",
        "activation_handler_replayed", "task_callbacks_replayed", "health_properties_written", "animation_assets_modified", "original_montage_or_effect_written"): result[field] = False
    for name in gate.PLAN:
        row = dict(native_type_preserved=True, native_tasks_at_start=3, movement_locked_at_start=True,
            original_montage_playing_observed=True, tasks_after_end=0, native_ability_ended=True, movement_unlocked_after_end=True,
            native_montage_stopped=True, native_heal_effects_restored=True, no_late_callbacks=True, fixture_health_restored=True,
            health_before=75., health_after=95., max_health=100., native_input_press_sent=True, profile_teardown_ended_ability=True,
            native_state_end_released_effects_while_active=True, native_state_end_released_movement_while_active=True, native_pause_observed=True,
            counters=dict(activations=1, effects_applied=1, movement_locks=1, movement_unlocks=1, tasks_created=3,
                scopes_created=1, scopes_closed=1, montage_blends=1, input_presses=1, state_ends=1))
        result["cases"].append(dict(name=name, blueprint=copy.deepcopy(row), python=copy.deepcopy(row)))
    return result


class HeroHealGate(unittest.TestCase):
    def test_complete_matrix(self): self.assertEqual(gate.validate(report())["pairs"], 8)

    def test_reject_effect_or_movement_leak(self):
        for field in ("native_heal_effects_restored", "movement_unlocked_after_end", "native_montage_stopped", "no_late_callbacks"):
            value = report(); value["cases"][0]["python"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_task_callback_replay_and_health_write(self):
        for field in ("task_callbacks_replayed", "health_properties_written", "original_montage_or_effect_written"):
            value = report(); value[field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_native_press_state_pause_and_profile_path(self):
        for index, field in ((1, "native_input_press_sent"), (5, "profile_teardown_ended_ability"),
            (6, "native_state_end_released_effects_while_active"), (7, "native_pause_observed")):
            value = report(); value["cases"][index]["blueprint"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_diff_and_shutdown_scope_leak(self):
        value = report(); value["cases"][0]["python"]["health_after"] = 99.
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_python_consuming_foreign_native_input_lock(self):
        for index, field in ((0, "external_lock_preserved_after_native_end"), (1, "state_cleanup_preserved_external_lock"),
            (2, "external_lock_released_once_restores_baseline")):
            value = report(); value["foreign_lock_regressions"][index][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["policy_shutdown"]["scopes_closed"] = 7
        with self.assertRaises(RuntimeError): gate.validate(value)
