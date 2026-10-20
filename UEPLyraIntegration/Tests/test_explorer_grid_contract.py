import unittest
from uep_lyra_hud.explorer_grid_contract import CASES,FALSE_FIELDS,TRUE_FIELDS,validate
def report():
    r=dict(status='passed',error=None,cases=[],native_proxy_counts=[2,2],native_proxy_paths_per_widget=[['a','b'],['c','d']],switched_callback_profiles=[True,True],owned_proxy_gi_refs_after_gc=0);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for name in CASES:
        count=2 if name in CASES[-2:] else 1;r['cases'].append(dict(name=name,states=[['item'],['item']],expected=['item'],callback_deltas=[count,count],expected_callbacks=count))
    return r
class ExplorerGridContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['native_message_cases'],10)
    def test_missing_original_edge_case_rejected(self):
        r=report();r['cases'].pop(5)
        with self.assertRaises(RuntimeError):validate(r)
    def test_native_pair_disagreement_rejected(self):
        r=report();r['cases'][0]['states'][1]=[]
        with self.assertRaises(RuntimeError):validate(r)
    def test_reconstructed_callback_loss_rejected(self):
        r=report();r['cases'][-1]['callback_deltas']=[1,2]
        with self.assertRaises(RuntimeError):validate(r)
    def test_leaked_native_listener_rejected(self):
        r=report();r['owned_proxy_gi_refs_after_gc']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_full_or_fastarray_acceptance_overclaim_rejected(self):
        for field in ('full_acceptance','fastarray_replication_claimed'):
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_native_context_or_original_listener_failure_rejected(self):
        for field in TRUE_FIELDS:
            r=report();r[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_duplicate_proxy_identity_or_stale_profile_rejected(self):
        for field,value in (('native_proxy_paths_per_widget',[['a','b'],['b','d']]),('switched_callback_profiles',[True,False])):
            r=report();r[field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
