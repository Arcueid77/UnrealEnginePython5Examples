"""Do not accept decision counters without native component/BT/late payload proof."""
import unittest
from uep_lyra_characters.explorer_behavior_contract import validate,FALSE_FIELDS,TRUE_FIELDS

def report():
    r=dict(status='passed',error=None,profile='Python',hero_empty_motion_override_and_parent_constructor_retained=True,pawn=dict(natural_false_constructor_label_and_parent=True,natural_true_constructor_label_and_parent=True,false_behavior_keeps_state_tree_and_stopped_brain=True,true_behavior_destroys_state_tree_and_uses_input_ai_controller=True,native_nil_controller_path_preserved=True,natural_possession_grant_behavior_controller_order=True,late_behavior=[dict(name=name,grants_while_missing=0,native_grants=2,owned_cleanup=True,latest_controller_argument_matches=True,state_tree_destroyed_after_grant=True,native_behavior_tree_seen_running=True) for name in ('controller','switch-pending')]));r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r
class ExplorerBehaviorContractTests(unittest.TestCase):
    def test_complete_native_case_matrix(self):self.assertEqual(validate(report())['native_late_cases'],2)
    def test_scope_overclaims_and_resource_leaks_rejected(self):
        for name,value in [(n,True) for n in FALSE_FIELDS]+[(n,False) for n in TRUE_FIELDS]:
            r=report();r[name]=value
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_every_constructor_and_native_behavior_observation_required(self):
        for name in ('natural_false_constructor_label_and_parent','natural_true_constructor_label_and_parent','false_behavior_keeps_state_tree_and_stopped_brain','true_behavior_destroys_state_tree_and_uses_input_ai_controller','native_nil_controller_path_preserved','natural_possession_grant_behavior_controller_order'):
            r=report();r['pawn'][name]=False
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_latest_event_controller_and_delayed_grant_order_required(self):
        for name,value in (('latest_controller_argument_matches',False),('grants_while_missing',1),('native_grants',3),('state_tree_destroyed_after_grant',False),('native_behavior_tree_seen_running',False)):
            r=report();r['pawn']['late_behavior'][0][name]=value
            with self.subTest(name=name),self.assertRaises(RuntimeError):validate(r)
    def test_both_late_lifetimes_required(self):
        r=report();r['pawn']['late_behavior'].pop()
        with self.assertRaises(RuntimeError):validate(r)
    def test_empty_override_and_forwarder_review_required(self):
        r=report();r['hero_empty_motion_override_and_parent_constructor_retained']=False
        with self.assertRaises(RuntimeError):validate(r)
