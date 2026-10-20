"""Require actual server travel, native phase callbacks and typed zero countdown."""
import unittest
from uep_lyra_weapons.game_phases_contract import FALSE_FIELDS,TRUE_FIELDS,validate


def report():
    r=dict(status='passed',error=None,profile='Python',native_mode='Standalone',sanitize_cases=[{}]*4,countdown_messages=[dict(magnitude=v) for v in (2.,1.,0.)],postgame_wait_elapsed=.25,block_frame=100,restart_frame=101,native_travel_log_evidence=dict(requested=True,started=True,finished=True,ordered=True));r.update(dict.fromkeys(FALSE_FIELDS,False));r.update(dict.fromkeys(TRUE_FIELDS,True));return r


class PhaseContractTests(unittest.TestCase):
    def test_complete_actual_phase_flow(self):self.assertTrue(validate(report())['actual_server_travel'])
    def test_travel_and_second_round_cannot_be_replaced_with_direct_calls(self):
        r=report();r['actual_server_travel_and_second_natural_round']=False
        with self.assertRaises(RuntimeError):validate(r)
        with self.assertRaises(RuntimeError):validate(report(),'no actual travel log')
    def test_zero_countdown_and_next_tick_are_required(self):
        for key,value in (('countdown_messages',[dict(magnitude=2.),dict(magnitude=1.)]),('restart_frame',100)):
            r=report();r[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
    def test_cleanup_and_no_callback_replay_are_required(self):
        for key,value in (('runtime_cdo_fields_and_profile_wrappers_restored',False),('ability_callbacks_replayed',True)):
            r=report();r[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(r)
