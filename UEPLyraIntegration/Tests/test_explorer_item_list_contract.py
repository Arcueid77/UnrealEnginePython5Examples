import unittest
from uep_lyra_hud.explorer_item_list_contract import CASES,FALSE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,groups=[],original_native_listener_released_after_owned_gc=True,owned_proxies_inactive_after_gc_and_message=True,primary_player_inventory_and_health_unchanged=True,owned_widgets_actors_roots_and_selectors_restored=True);r.update(dict.fromkeys(FALSE_FIELDS,False))
    for profile in ('BlueprintFallback','Python'):
        g=dict(row_profile=profile,cases=[],native_proxy_counts=[2,2],proxy_paths=[['a','b'],['c','d']],expired_items=[2,2],expiry_elapsed=[2.,2.,2.,2.]);g.update(dict.fromkeys(('native_entry_assignment_and_binding_observed','pending_row_and_list_profiles_used','native_two_second_expiry_removes_all_items','final_empty_list_collapsed','original_listener_refs_preserved'),True))
        for name in CASES:
            count=0 if name in CASES[:3] else 2 if name in CASES[-2:] else 1;callbacks=0 if name==CASES[0] else 2 if name in CASES[-2:] else 1;state=[dict(duration=2.,text='1x Pistol',icon='texture',native_format_identity_preserved=True) for _ in range(count)];g['cases'].append(dict(name=name,states=[state,list(state)],callback_deltas=[callbacks,callbacks],expected_callbacks=callbacks,expected_items=count,expected_text='1x Pistol',expected_icon='texture',all_item_outers_match_own_list=True))
        r['groups'].append(g)
    return r
class ExplorerItemListContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['list_row_profile_combinations'],4)
    def test_missing_row_profile_or_message_rejected(self):
        r=report();r['groups'][0]['cases'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_expiry_or_current_profile_failure_rejected(self):
        for key in ('pending_row_and_list_profiles_used','native_two_second_expiry_removes_all_items'):
            r=report();r['groups'][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_duplicate_native_proxy_identity_rejected(self):
        r=report();r['groups'][0]['proxy_paths']=[['a','b'],['b','d']]
        with self.assertRaises(RuntimeError):validate(r)
    def test_leaked_owned_native_listener_rejected(self):
        r=report();r['original_native_listener_released_after_owned_gc']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_full_or_fastarray_claim_rejected(self):
        for key in ('full_acceptance','fastarray_replication_claimed'):
            r=report();r[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_falsely_empty_positive_case_rejected(self):
        r=report();row=r['groups'][0]['cases'][3];row.update(states=[[],[]],expected_items=0)
        with self.assertRaises(RuntimeError):validate(r)
