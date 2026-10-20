"""Reject altered init state/parent, synchronous visibility and destroyed resumes."""
import unittest
from uep_lyra_characters.explorer_beginplay_contract import validate,FALSE_FIELDS,TRUE_FIELDS

def report():
    r=dict(status='passed',error=None,profile='Python',characters=[]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True))
    for kind in ('hero','pawn'):r['characters'].append(dict(kind=kind,natural_begin_once=True,natural_next_frame_show=True,original_spawned_registration=True,required_state='InitState.Spawned',static_parent='/Game/Characters/Character_Default.Character_Default_C',visibility_cases=[dict(name=name,native_registration_called=True,not_shown_synchronously=True,received_callbacks=2,native_next_frame_show=True,no_late_script_work_after_destroy=True) for name in ('repeat','switch-pending','destroy-pending')]))
    return r
class ExplorerBeginPlayContractTests(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())['visibility_cases'],6)
    def test_scope_and_cleanup_are_enforced(self):
        for name,value in [(n,True) for n in FALSE_FIELDS]+[(n,False) for n in TRUE_FIELDS]:
            r=report();r[name]=value
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_source_parent_and_required_state_are_exact(self):
        for name,value in (('required_state','InitState.GameplayReady'),('static_parent','OtherParent')):
            r=report();r['characters'][0][name]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_natural_begin_and_next_frame_are_required(self):
        for name in ('natural_begin_once','natural_next_frame_show','original_spawned_registration'):
            r=report();r['characters'][0][name]=False
            with self.assertRaises(RuntimeError):validate(r)
    def test_synchronous_show_is_rejected(self):
        r=report();r['characters'][0]['visibility_cases'][0]['not_shown_synchronously']=False
        with self.assertRaises(RuntimeError):validate(r)
    def test_destroyed_pending_actor_must_do_no_late_work(self):
        r=report();r['characters'][1]['visibility_cases'][-1]['no_late_script_work_after_destroy']=False
        with self.assertRaises(RuntimeError):validate(r)
