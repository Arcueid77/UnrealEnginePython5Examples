import copy
import unittest
from uep_lyra_abilities.arena_natural_bomb_contract import validate,validate_native_delays
from test_arena_natural_bomb_contract import report


def variable_report():
    value=report();value['native_timing_mode']='variable';value['native_timing_observer_profiles_restored']=True
    value['natural']['original_minimum_burn_seconds']=.5
    value['native_timing_events']=[dict(scope=scope,method=method,object=scope,profile='Python',frame=frame,game_seconds=seconds,world_delta_seconds=1/60) for scope,method,frame,seconds in (
        ('bomb','UEPArenaBombBegin',0,0.),('bomb','UEPArenaBombTrigger',90,1.5),('bomb','UEPArenaBombIncrement',120,2.),('death','Activate',120,2.),('bomb','UEPArenaBombDestroyed',144,2.4),('death','AfterWait',240,4.))]
    return value


class ArenaNativeDelayContractTests(unittest.TestCase):
    def test_fixed_and_variable_evidence_remain_distinct(self):
        validate(report());validate(variable_report())

    def test_each_original_native_delay_has_a_measured_interval(self):
        result=validate_native_delays(variable_report())
        self.assertEqual([result[k]['requested_seconds'] for k in ('fuse_pause','minimum_burn','death_task')],[1.5,.5,2.])

    def test_measured_long_boundary_frame_explains_same_frame_latent_work(self):
        value=variable_report();events=value['native_timing_events'];events[1]['world_delta_seconds']=.4
        for e,seconds in zip(events,[0.,1.5,1.6,1.6,2.,3.6]):e['game_seconds']=seconds
        validate_native_delays(value)

    def test_early_delay_without_measured_frame_budget_rejected(self):
        value=variable_report()
        for e,seconds in zip(value['native_timing_events'],[0.,1.5,1.6,1.6,2.,3.6]):e['game_seconds']=seconds
        with self.assertRaises(AssertionError):validate_native_delays(value)

    def test_late_native_task_cannot_hide_behind_a_fixed_tolerance(self):
        value=variable_report();value['native_timing_events'][-1]['game_seconds']=5.
        with self.assertRaises(AssertionError):validate_native_delays(value)

    def test_nonfinite_native_clock_or_frame_rejected(self):
        for field in ('game_seconds','world_delta_seconds'):
            for bad in (float('nan'),float('inf')):
                value=variable_report();value['native_timing_events'][1][field]=bad
                with self.subTest(field=field,bad=bad),self.assertRaises(AssertionError):validate_native_delays(value)

    def test_profile_mismatch_missing_callback_or_reorder_rejected(self):
        for change in ('profile','missing','order'):
            value=variable_report();events=value['native_timing_events']
            if change=='profile':events[1]['profile']='BlueprintFallback'
            elif change=='missing':del events[1]
            else:events[0],events[1]=events[1],events[0]
            with self.subTest(change=change),self.assertRaises(AssertionError):validate_native_delays(value)

    def test_observer_profile_restoration_required(self):
        value=variable_report();value['native_timing_observer_profiles_restored']=False
        with self.assertRaises(AssertionError):validate_native_delays(value)

    def test_unknown_mode_does_not_bypass_fixed_gate(self):
        value=report();value['native_timing_mode']='unknown'
        with self.assertRaises(AssertionError):validate(value)
