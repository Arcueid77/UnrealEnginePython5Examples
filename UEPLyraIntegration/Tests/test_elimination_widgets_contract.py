"""Native list timing, material/text/icon parity and rooted remount boundaries."""
import unittest
from uep_lyra_hud.elimination_widgets_contract import PROFILES,validate


def report():
    r=dict(status='passed',error=None,native_mode='Standalone',profiles=[])
    for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_or_list_subscription_replaced','timer_callbacks_replayed','list_item_callbacks_replayed','localized_text_roundtripped','health_properties_written','split_screen_filter_added'):r[k]=False
    for k in ('widget_roots_removed','original_cdo_profiles_restored','production_profile_families_restored','original_health_unchanged'):r[k]=True
    for p in PROFILES:
        row=dict(profile=p,style_cases=[dict(native_material_values_match=True) for _ in range(3)],icon_cases=[dict(native_text_matches=True,native_icon_matches=True) for _ in range(9)],expiry_entries=2,removed_entries=2,diagnostic_fallbacks=0)
        for k in ('initial_collapsed','two_items_visible','items_outer_matches_feed','all_native_entry_fields_match','animation_started','collapsed_after_expiry','native_expiry_durations_match','removed_widget_still_received_native_message','remount_has_one_entry','remount_single_listener_entry','remount_expired'):row[k]=True
        r['profiles'].append(row)
    return r


class EliminationWidgetContractTests(unittest.TestCase):
    def test_complete_native_evidence(self):self.assertEqual(validate(report())['native_style_cases'],6)
    def test_native_material_and_icon_text_must_match(self):
        r=report();r['profiles'][0]['style_cases'][0]['native_material_values_match']=False
        with self.assertRaises(RuntimeError):validate(r)
        r=report();r['profiles'][0]['icon_cases'][0]['native_text_matches']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_expiry_must_be_real_timer_and_remove_exact_items(self):
        for key,value in (('expiry_entries',0),('removed_entries',1),('native_expiry_durations_match',False)):
            r=report();r['profiles'][0][key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_rooted_removed_widget_listener_behavior_cannot_be_silently_changed(self):
        r=report();r['profiles'][0]['removed_widget_still_received_native_message']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_no_native_timer_list_or_split_screen_replacement_claim(self):
        for key in ('native_timer_or_list_subscription_replaced','timer_callbacks_replayed','list_item_callbacks_replayed','split_screen_filter_added'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
