"""Spawn report gate negatives; model reports are not native evidence."""
import copy
import unittest
from uep_lyra_abilities import spawn_effect_contract as gate
from uep_lyra_hud.startup import validation_module


def report():
    result = dict(status="passed", error=None, original_player_restored=True, original_ability_specs_restored=True,
        original_fraction_restored=True, native_default_on_spawn_observed=True, cases=[],
        policy_shutdown=dict(errors=[], active_count=0, scopes_created=11, scopes_closed=11))
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "activation_handler_replayed", "task_callbacks_replayed",
        "health_properties_written", "animation_assets_modified", "original_montage_or_effect_written"): result[field] = False
    for name in gate.PLAN:
        early = name in ("native-cancel", "external-native-end", "active-profile-switch")
        fraction = 0. if name == "zero-input-fraction" else (1. if name == "end-input-fraction" else .75)
        value = dict(native_type_preserved=True, effect_at_start=1, immune_at_start=True, movement_locked_at_start=True,
            native_montage_playing_observed=True, native_ability_ended=True, effects_after_end=0, tasks_after_end=0,
            immune_after_end=False, movement_after_end=name == "foreign-input-lock", foreign_lock_released_restores_baseline=True,
            original_player_restored=True, no_late_business_mutation=True, montage_length=2.75, native_elapsed=.35 if early else 2.75,
            input_fraction=fraction, unlock_elapsed=2.75*fraction, profile_teardown_ended_ability=name == "active-profile-switch",
            native_pause_observed=name == "paused-world-time", interrupt_left_ability_active=name == "montage-interrupt",
            counters=dict(activations=1, scopes_created=1, scopes_closed=1, effects_applied=1, effects_removed=1,
                movement_locks=1, movement_unlocks=1, tasks_created=3, native_ends=int(name != "active-profile-switch")))
        result["cases"].append(dict(name=name, blueprint=copy.deepcopy(value), python=copy.deepcopy(value)))
    return result


class SpawnEffectGate(unittest.TestCase):
    def test_complete_matrix(self): self.assertEqual(gate.validate(report())["pairs"], 10)

    def test_nullable_receiver_must_not_consume_foreign_lock_or_create_effects(self):
        row = dict(fixture_cached_controller_per_instance_written=True, actual_existing_instance=True,
            native_actor_info_controller_preserved=True, foreign_native_input_lock_preserved=True,
            no_effect_or_task_created=True, original_cache_restored=True, native_input_baseline_restored=True,
            nullable_entries=1, owned_locks=0, owned_unlocks=0, original_bp_null_warning_parity_claimed=False)
        gate.validate_nullable_controller([row])
        existing = dict(row, effects_before=0, effects_after=0, tasks_before=2, tasks_after=2, effects_created=0, tasks_created=0)
        gate.validate_nullable_controller([existing])
        for field, invalid in (("tasks_after", 3), ("tasks_created", 1), ("effects_created", 1)):
            value = dict(existing); value[field] = invalid
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate_nullable_controller([value])
        for field, invalid in (("foreign_native_input_lock_preserved", False), ("original_cache_restored", False),
                               ("owned_unlocks", 1), ("nullable_entries", 0)):
            value = dict(row); value[field] = invalid
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate_nullable_controller([value])

    def test_immediate_handoff_requires_old_delays_blocked_during_new_activation(self):
        value = report(); value["native_immediate_handoff_tested"] = True
        value["blueprint_to_python_immediate_handoff"] = dict(old_activation_ended=True, new_python_activated=True,
            alive_after_old_bp_deadline=True, new_python_enable_requests=2, effects_after_end=0, tasks_after_end=0,
            original_player_restored=True, new_native_elapsed=2.75, montage_length=2.75, input_fraction=.75, unlock_elapsed=2.0625)
        self.assertTrue(gate.validate(value)["native_immediate_handoff_tested"])
        for field, replacement in (("alive_after_old_bp_deadline", False), ("new_python_enable_requests", 3), ("unlock_elapsed", 1.76)):
            bad = copy.deepcopy(value); bad["blueprint_to_python_immediate_handoff"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(bad)

    def test_only_explicit_lane_starts(self):
        self.assertEqual(validation_module(["-UEPSpawnEffectResult=report.json"]), "uep_lyra_abilities.spawn_effect_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPSpawnEffectResult=report.json"]))

    def test_reject_missing_effect_immune_and_early_unlock(self):
        for field, replacement in (("effect_at_start", 0), ("immune_at_start", False), ("unlock_elapsed", .4)):
            value = report(); value["cases"][0]["python"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_interrupt_ending_early_and_missing_native_pause(self):
        value = report(); value["cases"][1]["python"]["native_elapsed"] = .35
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][-1]["python"]["native_pause_observed"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_removed_foreign_lock_leaked_effect_and_late_business(self):
        for name, field, replacement in (("foreign-input-lock", "movement_after_end", False),
            ("repeat", "effects_after_end", 1), ("active-profile-switch", "no_late_business_mutation", False)):
            value = report(); row = next(row for row in value["cases"] if row["name"] == name); row["python"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_scope_leak_unrestored_fraction_and_unobserved_onspawn(self):
        value = report(); value["policy_shutdown"]["active_count"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)
        for field in ("original_fraction_restored", "native_default_on_spawn_observed"):
            value = report(); value[field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)
