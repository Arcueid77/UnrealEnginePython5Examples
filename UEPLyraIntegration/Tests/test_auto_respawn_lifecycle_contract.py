"""Synthetic native lifecycle evidence rejection; no native acceptance claim."""
import copy
import unittest
from uep_lyra_abilities import auto_respawn_lifecycle_contract as gate


def report():
    cases = []
    for index, (name, profile) in enumerate((name, profile) for name in gate.PLAN for profile in ("BlueprintFallback", "Python")):
        old, new = index+2, index+3
        before = dict(classes=[gate.CLASS, "death", "equipment"], persistent=[[old, gate.CLASS], [1, "death"]])
        after = copy.deepcopy(before); after["persistent"] = sorted([[new, gate.CLASS], [1, "death"]])
        prefix = "" if profile == "Python" else "fallback_"
        stats = {prefix+"removed": 0, prefix+"end_cleanups": 1, "native_reset_cancelled": 1,
            "cancelled_long_continuations": 0, "cancelled_short_continuations": 0}
        event_counts = dict(long_continuations=int(name == "clear-pending-short"), fallback_long_continuations=0,
            short_continuations=0, fallback_short_continuations=0, native_restarts=0, native_completion_rpcs=0, cosmetic_completion_messages=0)
        probe = dict(valid=True, container="tuple", arity=2, return_type="bool", reference_type="UIExtensionHandle")
        cases.append(dict(name=name, profile=profile, native_type_preserved=True, ability_active_before=True, ui_before=probe,
            proxy_active_before=True, runtime_ended=True, reflected_proxy_cleared=True, health_listener_cleared=True,
            no_new_pawn_before_fixture_recovery=True, original_source_object_is_null=True, replacement_handle_differs=True,
            new_root_active=True, new_root_ui_valid=True, new_root_proxy_active=True, native_active_after_end=False,
            listening_after_end=False, old_proxy_active_after_end=False, ui_after_end=dict(probe, valid=False),
            old_instance_valid_at_deadline=True, old_instance_inactive_at_deadline=True,
            native_root_spec_count_at_deadline=1, native_root_spec_count_after_end=1, native_root_spec_count_after_clear=0, native_root_spec_count_after_give=1, old_handle=old, new_handle=new,
            specs_before=before, specs_after=after, specs_expected_after_native_regrant=copy.deepcopy(after),
            after_clear_policy=stats, observation_game_seconds=.5 if name != "clear-pending-long" else 5.5,
            elapsed_game_seconds=6., after_clear_events=copy.deepcopy(event_counts), events_at_end=event_counts,
            after_remove_policy={prefix+"removed": 1, prefix+"end_cleanups": 0},
            new_root_policy=dict(added=1, activated=1), fixture_recovery=dict(native_death_end_called=False,
                native_gamemode_restart_called=False, native_quickbar_recovery=False)))
    return dict(status="passed", error=None, mode="native-test-owned-end-clear-give", full_auto_respawn_acceptance=False,
        native_end_ability_called_by_fixture=True, native_end_cancels_latent_actions=True,
        native_clear_ability_called_by_fixture=True, native_give_ability_called_by_fixture=True, test_owned_root_removed_before_exit=True,
        replacement_handle_claimed_identical=False, callback_replay=False, health_properties_written=False,
        ability_spec_properties_written=False, inventory_properties_written=False,
        fixture_roots=dict(added=0, released=0, active=0), cases=cases)


class NativeLifecycleReportModels(unittest.TestCase):
    def test_bounded_synthetic_shape(self): self.assertEqual(gate.validate(report())["pairs"], 3)

    def test_every_real_clear_give_and_both_profiles_required(self):
        value = report(); value["cases"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_actual_native_resources_cannot_survive_clear(self):
        for key in ("native_active_after_end", "listening_after_end", "old_proxy_active_after_end"):
            value = report(); value["cases"][0][key] = True
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_old_late_callback_cannot_restart_or_emit_completion(self):
        for key in ("native_restarts", "native_completion_rpcs", "cosmetic_completion_messages"):
            value = report(); value["cases"][2]["after_clear_events"][key] = 1
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_end_must_cancel_the_actual_delay_through_its_real_deadline(self):
        for mutate in (lambda row: row.update(elapsed_game_seconds=1.), lambda row: row["after_clear_events"].update(long_continuations=1),
            lambda row: row.update(old_instance_valid_at_deadline=False), lambda row: row.update(native_root_spec_count_at_deadline=0),
            lambda row: row["after_clear_policy"].update(cancelled_long_continuations=1)):
            value = report(); mutate(value["cases"][2])
            with self.assertRaises(RuntimeError): gate.validate(value)

    def test_ui_false_return_with_reference_is_not_truthy_tuple(self):
        self.assertIs(gate.decode_ui_valid((False, object())), False)
        self.assertIs(gate.decode_ui_valid((True, object())), True)
        for result in (False, (False,), (0, object()), (False, None), [False, object()]):
            with self.subTest(result=result), self.assertRaises(RuntimeError): gate.decode_ui_valid(result)

    def test_ui_shape_or_true_after_native_end_is_rejected(self):
        for fields in (dict(valid=True), dict(arity=1), dict(container="bool")):
            value = report(); value["cases"][0]["ui_after_end"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_new_handle_is_explicit_and_sequence_cannot_hide_extra_grants(self):
        for mutate in (lambda row: row.update(new_handle=row["old_handle"]), lambda row: row.update(native_root_spec_count_after_give=2),
            lambda row: row.update(old_handle=999)):
            value = report(); mutate(value["cases"][1])
            with self.assertRaises(RuntimeError): gate.validate(value)

    def test_expected_model_cannot_hide_changed_other_classes_or_persistent_handles(self):
        value = report(); value["cases"][0]["specs_after"]["classes"].pop()
        value["cases"][0]["specs_expected_after_native_regrant"] = copy.deepcopy(value["cases"][0]["specs_after"])
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_owned_roots_final_grant_cleanup_and_scope_overclaims_rejected(self):
        for mutate in (lambda r: r["fixture_roots"].update(active=1), lambda r: r.update(test_owned_root_removed_before_exit=False),
            lambda r: r.update(full_auto_respawn_acceptance=True), lambda r: r.update(ability_spec_properties_written=True)):
            value = report(); mutate(value)
            with self.assertRaises(RuntimeError): gate.validate(value)
