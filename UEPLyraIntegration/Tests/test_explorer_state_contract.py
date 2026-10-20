"""Reject direct-event results masquerading as real compiled-tree execution."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_world.explorer_state_contract import FALSE_FIELDS,TRUE_FIELDS,validate

def report():
    r=dict(status='passed',error=None,profile='Python',compiled_tree_nodes=['location','goto','follow'],direct_event_nodes=['eval','delay','goto','follow'],direct_move_counts={k:dict(enter=1,success=1,failed=0) for k in ('goto','follow')},compiled_tree_counts=dict(location_tick=3,goto_enter=1,goto_success=1,goto_failed=0,follow_enter=1,follow_success=0,follow_failed=1),delay_counts=dict(enter=1,enter_done=1,tick=3,tick_done=1),delay_duration=.18,delay_elapsed=.4)
    r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r
class ExplorerStateContractTests(unittest.TestCase):
    def test_complete_native_tree_and_direct_event_matrix(self):self.assertEqual(validate(report())['profile'],'Python')
    def test_actual_native_observations_required(self):
        for field in TRUE_FIELDS:
            r=report();r[field]=False
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_overclaims_rejected(self):
        for field in FALSE_FIELDS:
            r=report();r[field]=True
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_gates_without_native_completion_are_insufficient(self):
        for field in ('goto_success','follow_failed'):
            r=report();r['compiled_tree_counts'][field]=0
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
    def test_unused_nodes_cannot_be_claimed_as_original_tree_execution(self):
        r=report();r['compiled_tree_nodes'].append('delay')
        with self.assertRaises(RuntimeError):validate(r)
    def test_actual_native_already_at_goal_success_required(self):
        r=report();r['direct_move_counts']['follow']['success']=0
        with self.assertRaises(RuntimeError):validate(r)
    def test_two_real_latent_waits_required(self):
        r=report();r['delay_elapsed']=.18
        with self.assertRaises(RuntimeError):validate(r)
    def test_original_delay_callback_counts_required(self):
        for field in ('enter','enter_done','tick_done'):
            r=report();r['delay_counts'][field]=2
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(r)
