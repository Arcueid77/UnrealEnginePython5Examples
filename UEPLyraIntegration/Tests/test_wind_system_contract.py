"""Reject Python scheduler recreation, no-resize fixes and missing real traces."""
import copy
import unittest
from uep_lyra_audio.wind_system_contract import PLAN,TICKS,exterior,validate


def report():
    value=dict(status="passed",error=None,cases=[],natural_python_ticks=5,owned_actors_destroyed=True,player_health_unchanged=True)
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","multigate_state_reimplemented_in_python","trace_results_injected","cpp_compile_executed"):value[key]=False
    for index,(distance,size,pattern) in enumerate(PLAN):
        ticks=[];step=0
        for tick in range(TICKS):
            active=exterior(pattern,tick);stage=step%5 if active else None;step+=int(active);state=dict(player_array_size=size,parameters={})
            ticks.append(dict(index=tick,stages=[stage,stage],states=[copy.deepcopy(state),copy.deepcopy(state)],python_queries=int(active)))
        value["cases"].append(dict(index=index,ticks=ticks))
    return value


class TestWindSystemContract(unittest.TestCase):
    def test_complete_paired_native_cycles(self):self.assertEqual(validate(report())["native_event_calls"],960)
    def test_profile_switch_cannot_restart_native_scheduler(self):
        value=report();value["cases"][0]["ticks"][7]["stages"]=[0,0]
        with self.assertRaises(RuntimeError):validate(value)
    def test_identically_fixed_array_resize_is_not_original_behavior(self):
        value=report()
        for state in value["cases"][0]["ticks"][0]["states"]:state["player_array_size"]=1
        with self.assertRaises(RuntimeError):validate(value)
    def test_parameter_disagreement_or_skipped_trace_rejected(self):
        value=report();value["cases"][0]["ticks"][0]["states"][1]["parameters"]["Wind"]=.5
        with self.assertRaises(RuntimeError):validate(value)
        value=report();value["cases"][0]["ticks"][0]["python_queries"]=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_interior_pause_and_natural_tick_are_required(self):
        value=report();value["cases"][1]["ticks"][4]["stages"]=[4,4]
        with self.assertRaises(RuntimeError):validate(value)
        value=report();value["natural_python_ticks"]=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_reimplemented_state_or_fake_physics_disqualifies_proof(self):
        for key in ("multigate_state_reimplemented_in_python","trace_results_injected","full_acceptance"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
