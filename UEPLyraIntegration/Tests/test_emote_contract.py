"""Emote independent gate rejects incomplete, replayed or leaking evidence."""
import copy
import unittest
from uep_lyra_abilities.emote_contract import PLAN, FALSE_CLAIMS, validate


def report():
    value = dict(status="passed", error=None, native_montage_length=5.45,
        native_external_movement_fixture=True, player_movement_input_tested=False, native_movement_producer="Character.LaunchCharacter",
        native_existing_spec_input_activation=True, original_player_restored=True, original_profile_restored=True,
        original_widget_grant_preserved=True, fixture_observers_closed=True, original_cdo_untouched=True,
        fixture_scopes_created=18, fixture_scopes_closed=18, cases=[],
        policy_shutdown=dict(active_count=0, scopes_created=18, scopes_closed=18, errors=[]))
    value.update({name: False for name in FALSE_CLAIMS})
    for name in PLAN:
        events = [] if name in ("external-native-end", "active-profile-switch") else \
            ["OnInterrupted"] if name in ("native-movement", "native-crouch", "native-cancel") else ["OnCompleted"]
        row = dict(native_type_preserved=True, native_source_preserved=True, profile_selected=True,
            native_montage_observed=True, native_montage_stopped=True, widget_grant_preserved=True,
            player_restored=True, ability_ended=True, input_injections=1, native_tasks_during=1, native_tasks_after=0,
            foreign_calls_before_intervention=3, native_end_callbacks=len(events), native_montage_events=events,
            active_game_seconds=5.43, native_velocity_observed=10., native_crouch_observed=True,
            crouched_before_activation=True, native_uncrouch_observed=True, profile_teardown_ended_ability=True,
            native_pause_observed=True, active_during_pause=True, no_late_python_movement=True,
            foreign_calls_after_end=4, counters=dict(activations=1, tasks_created=1, scopes_created=2, scopes_closed=2,
                movement_stops=1, montage_interrupted=1, uncrouches=1))
        original = copy.deepcopy(row)
        if name in ("native-movement", "native-crouch"):
            original["foreign_calls_after_end"] = 0
        value["cases"].append(dict(name=name, blueprint=original, python=row))
    return value


class EmoteGate(unittest.TestCase):
    def test_complete_bounded_report(self):
        self.assertEqual(validate(report())["pairs"], 9)

    def test_rejects_missing_order_replay_pause_and_cleanup_claims(self):
        for mutation in (lambda r: r["cases"].pop(), lambda r: r["cases"].reverse(),
            lambda r: r.update(activation_handler_replayed=True), lambda r: r.update(foreign_listener_parity_claimed=True),
            lambda r: r["cases"][-1]["python"].update(native_pause_observed=False),
            lambda r: r["policy_shutdown"].update(scopes_closed=17)):
            with self.subTest(mutation=mutation):
                value = report(); mutation(value)
                with self.assertRaises(RuntimeError): validate(value)

    def test_rejects_fake_motion_and_foreign_listener_difference(self):
        for side, field, target in (("python", "native_velocity_observed", 0.),
            ("python", "foreign_calls_after_end", 0), ("blueprint", "foreign_calls_after_end", 1),
            ("python", "no_late_python_movement", False)):
            with self.subTest(field=field):
                value = report(); value["cases"][1][side][field] = target
                with self.assertRaises(RuntimeError): validate(value)

    def test_external_end_must_not_invent_a_montage_callback(self):
        value = report(); value["cases"][5]["python"].update(native_montage_events=["OnCancelled"], native_end_callbacks=1)
        with self.assertRaises(RuntimeError): validate(value)


if __name__ == "__main__":
    unittest.main()
