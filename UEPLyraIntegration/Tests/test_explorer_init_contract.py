"""Require distinct native listeners, actual deferred readiness and owned cleanup."""
import unittest
from uep_lyra_characters.explorer_init_contract import validate,FALSE_FIELDS,TRUE_FIELDS,NAMES

def report():
    r=dict(status='passed',error=None,profile='Python',characters=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for kind in ('hero','pawn'):
        row=dict(kind=kind,natural_possession_factory_and_grant=True,two_listeners_create_two_native_proxies=True,initial_callbacks_match_native_team=True,native_team_change_and_cancel_isolation=True,native_no_team_callback_is_noop=True,named_actor_specific_callbacks_resolved=True,readiness=[])
        for name in NAMES:
            stage=1 if name=='inventory' else 2 if name=='quickbar' else 0;row['readiness'].append(dict(name=name,stage=stage,grants_while_missing=0,native_wait_resumed_after_availability=True,owned_cleanup=True,native_readiness_released=name!='destroy-pending',native_grants=0 if name=='destroy-pending' else 2 if stage==0 else 1,no_late_work_after_destroy=True))
        r['characters'].append(row)
    return r
class ExplorerInitContractTests(unittest.TestCase):
    def test_complete_two_actor_native_matrix(self):self.assertEqual(validate(report())['deferred_cases'],10)
    def test_all_overclaims_and_cleanup_are_checked(self):
        for name,value in [(n,True) for n in FALSE_FIELDS]+[(n,False) for n in TRUE_FIELDS]:
            r=report();r[name]=value
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_native_listener_and_callback_observations_required(self):
        for name in ('natural_possession_factory_and_grant','two_listeners_create_two_native_proxies','initial_callbacks_match_native_team','native_team_change_and_cancel_isolation','native_no_team_callback_is_noop','named_actor_specific_callbacks_resolved'):
            r=report();r['characters'][0][name]=False
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_grant_while_missing_is_rejected(self):
        r=report();r['characters'][0]['readiness'][0]['grants_while_missing']=1
        with self.assertRaises(RuntimeError):validate(r)
    def test_repeated_request_coalescing_is_checked(self):
        r=report();r['characters'][0]['readiness'][1]['native_grants']=2
        with self.assertRaises(RuntimeError):validate(r)
    def test_destroyed_actor_cannot_resume_work(self):
        r=report();r['characters'][0]['readiness'][-1]['no_late_work_after_destroy']=False
        with self.assertRaises(RuntimeError):validate(r)
