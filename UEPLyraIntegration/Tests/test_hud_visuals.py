"""Presenter command/state tests; real UMG rendering needs its own run."""

import unittest

from test_hud_presenter import _FakeController, _FakeHealth, _FakePawn, _PythonHealthbarHarness, fake_ue
from uep_lyra_hud.healthbar_mixin import normalized_health


class HUDVisualTests(unittest.TestCase):
    def setUp(self):
        self.error_count = len(fake_ue.errors)
        self.health = _FakeHealth('/Test/Health')
        self.controller = _FakeController('/Test/Controller', _FakePawn('/Test/Pawn', self.health))
        self.widget = _PythonHealthbarHarness(self.controller)
        self.widget.Construct()
        self.addCleanup(self.widget.__uep_mixin_teardown__)

    def tearDown(self):
        self.assertEqual(fake_ue.errors[self.error_count:], [])

    def test_damage_interpolates_without_reinitializing(self):
        self.health.set_health(90.0)
        self.assertEqual(self.widget.initialize_visual_calls, 1)
        self.assertEqual(self.widget.HealthNumber.current_value, 100.0)
        self.assertEqual(self.widget.HealthNumber.calls[-1], ('InterpolateToValue', 90.0, 1.0, 4.0, 0.0))
        self.assertEqual(self.widget.played_animations[-1], self.widget.OnDamaged)
        for name in ('BarBorderMID', 'BarFillMID', 'BarGlowMID'):
            expected = {'Health_Current': 1.0, 'Health_Updated': 0.9,
                        'Animate_Damage': 0.0, 'Animate_DamageFade': 0.0}
            if name != 'BarFillMID':
                expected.update(Animate_Glow_AlphaChange=0.0, Animate_Glow_ColorChange=0.0)
            self.assertEqual(getattr(self.widget, name).scalars, expected)

    def test_queued_spawn_stop_is_flushed_before_new_health_material(self):
        # UE 5.8 Stop queues a frame-zero evaluation. That key writes 1.0 in
        # the retained OnSpawned asset, even after the stop was requested.
        self.widget.defer_native_stops = True
        self.health.set_health(75.0)
        self.assertEqual(self.widget.pending_native_stops, [])
        self.widget.call_function("FlushAnimations")
        self.assertEqual(self.widget.BarFillMID.scalars["Health_Updated"], .75)
        self.assertEqual(self.widget.HealthNumber.target_value, 75.0)

    def test_router_teardown_does_not_flush_an_unavailable_router(self):
        count = self.widget.flush_calls
        self.widget.__uep_mixin_teardown__()
        self.assertEqual(self.widget.flush_calls, count)

    def test_second_hit_keeps_displayed_interpolation_value(self):
        self.health.set_health(90.0)
        self.widget.HealthNumber.current_value = 95.0
        self.health.set_health(80.0)
        self.assertEqual(self.widget.HealthNumber.current_value, 95.0)
        self.assertEqual(self.widget.HealthNumber.target_value, 80.0)
        self.assertEqual(self.widget.initialize_visual_calls, 1)

    def test_healing_selects_its_authored_animation(self):
        self.health.set_health(90.0)
        self.health.set_health(100.0)
        self.assertEqual(self.widget.played_animations[-1], self.widget.OnHealed)
        self.assertEqual(self.widget.BarFillMID.scalars['Health_Current'], 0.9)
        self.assertEqual(self.widget.BarFillMID.scalars['Health_Updated'], 1.0)

    def test_death_waits_for_damage_animation(self):
        self.health.set_health(0.0)
        self.assertNotIn(self.widget.OnEliminated, self.widget.played_animations)
        self.widget.finish_animation(self.widget.OnHealed)
        self.assertTrue(self.widget._uep_hud_pending_elimination)
        self.widget.finish_animation(self.widget.OnDamaged)
        self.assertFalse(self.widget._uep_hud_pending_elimination)
        self.assertEqual(self.widget.played_animations[-1], self.widget.OnEliminated)

    def test_old_finish_cannot_end_a_new_damage_animation(self):
        self.health.set_health(0.0)
        self.widget.OnAnimationFinished(self.widget.OnDamaged)
        self.assertNotIn(self.widget.OnEliminated, self.widget.played_animations)

    def test_new_pawn_cancels_pending_death(self):
        self.health.set_health(0.0)
        replacement = _FakeHealth('/Test/NewHealth', 75.0)
        self.controller.possess(_FakePawn('/Test/NewPawn', replacement))
        self.widget.finish_animation(self.widget.OnDamaged)
        self.assertNotIn(self.widget.OnEliminated, self.widget.played_animations)
        self.assertEqual(self.widget.played_animations[-1], self.widget.OnSpawned)
        self.assertEqual(self.widget.HealthNumber.current_value, 75.0)
        self.assertEqual(self.widget.BarFillMID.scalars['Health_Updated'], 0.75)

    def test_destruction_disarms_animation_completion(self):
        self.health.set_health(0.0)
        self.widget.Destruct()
        self.widget.finish_animation(self.widget.OnDamaged)
        self.assertNotIn(self.widget.OnEliminated, self.widget.played_animations)
        self.assertFalse(self.widget.playing_animations)

    def test_router_teardown_does_not_dispatch_animation_completion(self):
        self.health.set_health(0.0)
        def unavailable_during_teardown(animation):
            raise AssertionError("completion reentered an unavailable router")
        self.widget.OnAnimationFinished = unavailable_during_teardown
        self.widget.__uep_mixin_teardown__()
        self.assertFalse(self.widget.playing_animations)
        self.assertFalse(self.widget._uep_hud_pending_elimination)

    def test_max_health_only_change_does_not_replay_or_snap(self):
        self.health.set_health(90.0)
        plays = len(self.widget.played_animations)
        calls = len(self.widget.HealthNumber.calls)
        self.health.set_max_health(200.0)
        self.assertEqual(len(self.widget.played_animations), plays)
        self.assertEqual(len(self.widget.HealthNumber.calls), calls)
        self.assertEqual(self.widget.BarFillMID.scalars['Health_Updated'], 0.45)

    def test_duplicate_health_notification_does_not_restart_animation(self):
        self.health.set_health(90.0)
        plays = len(self.widget.played_animations)
        self.health.set_health(90.0)
        self.assertEqual(len(self.widget.played_animations), plays)
        self.assertEqual(self.widget.initialize_visual_calls, 1)

    def test_zero_and_nonstandard_max_health(self):
        self.assertEqual(normalized_health(10.0, 0.0), 0.0)
        self.assertEqual(normalized_health(100.0, 200.0), 0.5)
        self.assertEqual(normalized_health(300.0, 200.0), 1.0)
        self.assertEqual(normalized_health(-1.0, 100.0), 0.0)

    def test_nonfinite_health_is_not_rendered(self):
        for health, maximum in ((float('nan'), 100.0), (1.0, float('inf'))):
            with self.assertRaises(ValueError):
                normalized_health(health, maximum)

    def test_delayed_asc_zero_then_identical_positive_attribute_values_recovers(self):
        delayed = _FakeHealth('/Test/DelayedASC', health=0.0, max_health=0.0)
        self.controller.possess(_FakePawn('/Test/DelayedPawn', delayed))
        self.assertEqual(self.widget.played_animations[-1], self.widget.OnEliminated)
        delayed.health = delayed.max_health = 100.0
        delayed.broadcast('OnHealthChanged', delayed, 100.0, 100.0, None)
        self.assertEqual(self.widget.played_animations[-1], self.widget.OnSpawned)
        self.assertEqual(self.widget.HealthNumber.current_value, 100.0)
        self.assertEqual(self.widget.BarFillMID.scalars['Health_Updated'], 1.0)
        plays = len(self.widget.played_animations)
        delayed.broadcast('OnMaxHealthChanged', delayed, 100.0, 100.0, None)
        self.assertEqual(len(self.widget.played_animations), plays)

    def test_delayed_asc_max_health_event_can_be_first_ready_notification(self):
        delayed = _FakeHealth('/Test/DelayedASC', health=0.0, max_health=0.0)
        self.controller.possess(_FakePawn('/Test/DelayedPawn', delayed))
        delayed.health = delayed.max_health = 100.0
        delayed.broadcast('OnMaxHealthChanged', delayed, 100.0, 100.0, None)
        self.assertEqual(self.widget.played_animations[-1], self.widget.OnSpawned)
        self.assertEqual(self.widget.HealthNumber.current_value, 100.0)


if __name__ == '__main__':
    unittest.main()
