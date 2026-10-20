import unittest
from uep_lyra_hud.explorer_toast_contract import SCENARIOS,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,cases=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(('native_list_view_delivered_valid_entries','native_list_expiry_removed_original_items','localized_text_namespace_keys_preserved','icon_texture_visibility_and_unmatched_size_pairs_preserved','owned_timers_widgets_roots_and_selectors_restored','primary_player_inventory_and_health_unchanged'),True))
    for name in SCENARIOS:
        for profile in ('BlueprintFallback','Python'):
            c=dict(name=name,profile=profile,expiry_count=int(name not in ('zero','negative','gc')),expected_item_payload=True,native_timer_state_matches=True,current_callback_profile_matches=True,configured_last_duration=.8,elapsed_after_last_valid_set=.81)
            if name=='gc':c.update(row_native_object_collected=True,no_timer_callback_after_gc=True)
            r['cases'].append(c)
    return r
class ExplorerToastContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_toast_timer_cases'],16)
    def test_missing_timer_case_rejected(self):
        r=report();r['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_old_item_payload_or_early_expiry_rejected(self):
        for field,value in (('expected_item_payload',False),('elapsed_after_last_valid_set',.01)):
            r=report();r['cases'][0][field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_nonpositive_duration_firing_rejected(self):
        r=report();r['cases'][2]['expiry_count']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_stale_profile_or_uncollected_native_row_rejected(self):
        for index,field in ((0,'current_callback_profile_matches'),(-1,'row_native_object_collected')):
            r=report();r['cases'][index][field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_timer_replay_or_full_acceptance_claim_rejected(self):
        for field in ('timer_callback_replayed','full_acceptance'):
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
