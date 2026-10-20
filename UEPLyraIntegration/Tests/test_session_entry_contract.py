"""Real nonempty rows and successful native peer joins must be proved."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_hud.session_entry_contract import FALSE_FIELDS,CLIENT_TRUE,HOST_TRUE,validate_peer
def report(role='client'):
    r=dict(status='passed',error=None,role=role);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(HOST_TRUE if role=='host' else CLIENT_TRUE,True))
    if role=='host':r.update(request_mode=1,request_bots='0',native_destination_mode='ListenServer')
    else:r.update(profile='Python',prepared_handler_calls=1,completion_handler_calls=1,native_destination_mode='Client',native_result_count=1,native_world_controller_replacement_expected=True)
    return r
class SessionEntryContractTests(unittest.TestCase):
    def test_native_host_and_client_pass(self):self.assertTrue(validate_peer(report()));self.assertTrue(validate_peer(report('host')))
    def test_missing_client_native_observation_rejected(self):
        for field in CLIENT_TRUE:
            r=report();r[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate_peer(r)
    def test_missing_host_native_observation_rejected(self):
        for field in HOST_TRUE:
            r=report('host');r[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate_peer(r)
    def test_scope_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate_peer(r)
    def test_empty_result_or_missing_actual_travel_rejected(self):
        for field,value in (('native_result_count',0),('native_world_controller_replacement_expected',False),('native_destination_mode','Standalone')):
            r=report();r[field]=value
            with self.assertRaises(RuntimeError):validate_peer(r)
    def test_wrong_join_callback_counts_rejected(self):
        for field in ('prepared_handler_calls','completion_handler_calls'):
            r=report();r[field]=2
            with self.assertRaises(RuntimeError):validate_peer(r)
    def test_wrong_host_mode_or_bots_rejected(self):
        for field,value in (('request_mode',2),('request_bots','3')):
            r=report('host');r[field]=value
            with self.assertRaises(RuntimeError):validate_peer(r)
