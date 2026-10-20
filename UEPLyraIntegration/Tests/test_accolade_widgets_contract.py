"""Require real native queue order/timing, widget return and remount cleanup."""
import unittest
from uep_lyra_hud.accolade_widgets_contract import PROFILES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',pairs=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_energy_measured','native_registry_or_queue_replaced','timer_or_animation_callbacks_replayed','health_properties_written','localized_text_roundtripped'):r[k]=False
    for k in ('animation_repeat_pairs_match','widget_profile_families_restored','owned_widgets_removed_unrooted','sender_root_removed','original_health_unchanged','owned_foreign_player_destroyed'):r[k]=True
    for p in PROFILES:
        r['pairs'].append(dict(profile=p,natural_constructs=2,initial_collapsed=True,remount_collapsed=True,direct_cases=[dict(returned_owned_toast=True,native_text_matches=True,icon_matches=True,visible=True,animation_playing=True) for _ in range(2)],destroy_ignores_foreign_argument=True,repeat_animation_still_playing=True,fifo_create_order=['chain','streak'],expected_fifo=['chain','streak'],fifo_native_allocated_widget_matches=True,fifo_duration_checks=True,cancel_order=['create','destroy','create','destroy'],cancel_create_order=['chain2','chain3'],expected_cancel=['chain2','chain3'],foreign_target_ignored=True,unmounted_message_ignored=True,single_create_after_remount=True,all_queued_native_text_icon_and_allocation_match=True,diagnostic_fallbacks=0))
    return r


class AccoladeWidgetContractTests(unittest.TestCase):
    def test_complete_native_evidence(self):self.assertEqual(validate(report())['native_direct_create_cases'],4)
    def test_native_existing_widget_return_and_opaque_text_cannot_be_missing(self):
        for key in ('returned_owned_toast','native_text_matches','icon_matches','animation_playing'):
            r=report();r['pairs'][0]['direct_cases'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_queue_order_duration_and_tag_cancel_are_required(self):
        for key,value in (('fifo_create_order',['streak','chain']),('fifo_duration_checks',False),('cancel_order',['create','create','destroy','destroy'])):
            r=report();r['pairs'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_filter_and_native_listener_remount_are_required(self):
        for key in ('foreign_target_ignored','unmounted_message_ignored','single_create_after_remount'):
            r=report();r['pairs'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_no_native_registry_timer_replacement_or_callback_replay_claim(self):
        for key in ('native_registry_or_queue_replaced','timer_or_animation_callbacks_replayed','localized_text_roundtripped'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_owned_roots_and_original_profile_families_must_be_restored(self):
        r=report();r['owned_widgets_removed_unrooted']=False
        with self.assertRaises(RuntimeError):validate(r)
