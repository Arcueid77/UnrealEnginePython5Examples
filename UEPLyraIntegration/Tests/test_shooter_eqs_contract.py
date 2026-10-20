"""Require real native EQS completion and restoration instead of callback replay."""
import unittest
from uep_lyra_world.shooter_eqs_contract import FALSE_FIELDS,TRUE_FIELDS,validate


def report():
    r=dict(status='passed',error=None,profile='Python',mode='tdm',native_mode='Standalone',diagnostic_fallbacks=0,cases=[dict(context=k) for k,n in (('points',3),('enemy',4),('weapon',5),('enemies',4)) for _ in range(n)]);r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r


class EQSContractTests(unittest.TestCase):
    def test_complete_real_query_matrix(self):self.assertEqual(validate(report())['native_queries'],16)
    def test_native_generator_and_result_match_required(self):
        for key in ('all_query_results_match_source_rules','all_context_and_generator_callbacks_observed'):
            r=report();r[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_no_callback_replay_and_restored_state_required(self):
        for key,value in (('query_callbacks_replayed',True),('blackboard_team_inventory_and_actor_fields_restored',False)):
            r=report();r[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_cp_mode_requires_real_control_points(self):
        r=report();r.update(mode='cp',actual_control_point_count=0)
        with self.assertRaises(RuntimeError):validate(r)
