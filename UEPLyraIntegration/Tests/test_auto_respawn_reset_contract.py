"""Synthetic Reset evidence gate rejection; never a native acceptance claim."""
import copy
from pathlib import Path
import unittest
from uep_lyra_abilities import auto_respawn_reset_contract as gate


def report():
    rows = []
    for name in gate.PLAN:
        for profile in ("BlueprintFallback", "Python"):
            pending, switched = "pending-long" in name, "switch" in name
            final = ("BlueprintFallback" if profile == "Python" else "Python") if switched else profile
            python = int(final == "Python")
            messages = [dict(channel="Ability.Respawn.Completed.Message", player_id=1, owner_matches=True,
                verb="Ability.Respawn.Completed.Message", magnitude=1., target_is_null=True, instigator_tags=[], target_tags=[], context_tags=[])]
            if pending: messages.insert(0, dict(channel="Ability.Respawn.Duration.Message", player_id=1, owner_matches=True, duration=5.))
            model = dict(classes=["native-root", "native-death"], persistent=[[1, "native-root"], [2, "native-death"]])
            rows.append(dict(name=name, profile=profile, player_id=1, native_reset_class=gate.RESET_CLASS, native_reset_existing_specs=1,
                trigger_entry="SendGameplayEventToActor(GameplayEvent.RequestReset)", native_reset_requests=1,
                old_pawn="old", new_pawn="new", health_before=100., health_after=100., death_after=0, native_type_preserved=True,
                delay_unchanged=True, specs_before=model, specs_after=copy.deepcopy(model), specs_at_restart=copy.deepcopy(model),
                auto_active_before=True, auto_active_after=True, final_profile=final, runtime_ended=False, reset_proxy_active=True, ui_valid_before=True, ui_valid_after=True,
                reset_messages=[dict(channel=gate.CHANNEL, player_id=1, owner_matches=True)], event_messages=messages,
                elapsed_game_seconds=6., observer_closed=True, original_delay_written=False, callbacks_replayed=False,
                activation_counters=dict(native_reset_starts=0, native_reset_cancelled=0, removed=0, fallback_removed=0, end_cleanups=0,
                    fallback_end_cleanups=0, reset_messages=python, resets_handled=python, foreign_resets=0, fallback_reset_messages=1-python),
                event_counters=dict(long_continuations=int(pending and final == "Python"), fallback_long_continuations=int(pending and final != "Python"),
                    short_continuations=python, fallback_short_continuations=1-python, native_restarts=python, native_completion_rpcs=python,
                    cosmetic_completion_messages=python)))
    return dict(status="passed", error=None, native_reset_producer_tested=True, reset_broadcast_by_fixture=False, full_auto_respawn_acceptance=False,
        original_profile_restored=True, original_specs_restored=True, observer_shutdown=dict(created=8, closed=8, active=0), cases=rows)


class NativeResetEvidenceModels(unittest.TestCase):
    def test_bounded_shape(self): self.assertEqual(gate.validate(report())["pairs"], 4)

    def test_all_real_reset_pairs_required(self):
        value = report(); value["cases"].pop()
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_broadcast_or_callback_replay_cannot_certify_native_producer(self):
        for mutate in (lambda v: v.update(reset_broadcast_by_fixture=True), lambda v: v.update(native_reset_producer_tested=False),
            lambda v: v["cases"][0].update(callbacks_replayed=True), lambda v: v["cases"][0].update(trigger_entry="ResetMessage")):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_typed_owner_is_not_a_channel_only_signal(self):
        for fields in (dict(owner_matches=False), dict(player_id=2), dict(channel="GameplayEvent.RequestReset")):
            value = report(); value["cases"][0]["reset_messages"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_duplicate_reset_or_native_completion_rejected(self):
        for key in ("reset_messages", "event_messages"):
            value = report(); value["cases"][0][key] *= 2
            with self.subTest(key=key), self.assertRaises(RuntimeError): gate.validate(value)

    def test_pending_original_deadline_and_no_duplicate_restart_required(self):
        for mutate in (lambda r: r.update(elapsed_game_seconds=.5), lambda r: r["event_counters"].update(native_restarts=2),
            lambda r: r["event_counters"].update(long_continuations=0), lambda r: r.update(original_delay_written=True)):
            value = report(); mutate(value["cases"][5])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_profile_flip_resolves_actual_delivery_and_continuation(self):
        value = report(); value["cases"][-1]["final_profile"] = "Python"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reset_lifetime_ui_specs_and_observer_restoration_required(self):
        for mutate in (lambda r: r.update(ui_valid_after=False), lambda r: r.update(reset_proxy_active=False),
            lambda r: r.update(runtime_ended=True), lambda r: r["activation_counters"].update(native_reset_starts=1),
            lambda r: r.update(specs_after={}), lambda r: r.update(observer_closed=False)):
            value = report(); mutate(value["cases"][0])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_raw_bp_python_observation_cannot_hide_model_difference(self):
        value = report(); value["cases"][1]["specs_at_restart"] = {}
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_no_fake_full_asset_acceptance_or_leaked_observer(self):
        for fields in (dict(full_auto_respawn_acceptance=True), dict(observer_shutdown=dict(created=8, closed=7, active=1))):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def test_fixture_and_probe_do_not_grant_replay_or_broadcast_reset(self):
        root = Path(__file__).resolve().parents[1]
        source = (root/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_reset_validation.py").read_text(encoding="utf-8")
        for forbidden in ('call_function("K2_GiveAbility"', 'call_function("ClearAbility"', 'call_function("OnDeathStarted"',
            'call_function("ResetMessage"', 'call_function("K2_ActivateAbility"', '"BroadcastReset"', '.add_to_root('):
            self.assertNotIn(forbidden, source)
        probe = (root/"Tools/generate_auto_respawn_reset_probe.py").read_text(encoding="utf-8")
        self.assertNotIn("broadcast_graph(", probe)
        self.assertIn('read_graph(bp, "Reset"', probe)
