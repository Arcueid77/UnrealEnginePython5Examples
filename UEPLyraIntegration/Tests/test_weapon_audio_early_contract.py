"""Reject missing real queries, altered source listeners, callbacks and cleanup."""
import copy
import math
import unittest
from uep_lyra_weapons.weapon_audio_early_contract import PLAN,ORDER,INDICES,eligible,validate


def report():
    value=dict(status="passed",error=None,open_geometry=False,tap_ids=list(range(20,28)),owned_wall_preflight=dict(hit=True,owned_actor=True),math_regression=[True]*8,early_pairs=[])
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","preset_asset_saved","cpp_compile_executed","trace_results_injected","tap_callbacks_replayed","static_functions_registered_as_mixins"):value[key]=False
    for key in ("preset_state_restored","current_dispatch_profiles_restored","owned_actors_destroyed","player_health_unchanged","router_profile_restored","original_static_signatures_preserved","dispatch_regression_passed","whiz_regression_passed"):value[key]=True
    for index,(name,target,surface,offset,normal) in enumerate(PLAN):
        distance=math.sqrt(sum(v*v for v in offset));active=eligible(target,surface,distance);listener=[10.,20.,30.]
        events=[dict(suffix=suffix,tap_id=20+tap,trace_distance=4000.,did_hit=(surface is not None if i==0 else i%2==0),listener=listener if i<6 else [0.,0.,0.]) for i,(suffix,tap) in enumerate(zip(ORDER,INDICES))] if active else []
        observed=dict(events=events,taps={"20":dict(Gain=-60.)})
        value["early_pairs"].append(dict(index=index,name=name,distance=distance,listener=listener,observations=[copy.deepcopy(observed) for _ in range(4)],fallback_dispatches=2,python_dispatches=2,python_eligible=2 if active else 0,python_queries=14 if active else 0,python_taps=16 if active else 0))
    return value


class TestWeaponAudioEarlyContract(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())["static_and_bp_invocations"],120)
    def test_python_calls_without_actual_business_queries_rejected(self):
        value=report();value["early_pairs"][0]["python_queries"]=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_identically_repaired_source_listener_rejected(self):
        value=report()
        for observation in value["early_pairs"][0]["observations"]:observation["events"][-1]["listener"]=[10.,20.,30.]
        with self.assertRaises(RuntimeError):validate(value)
    def test_native_complete_preset_disagreement_rejected(self):
        value=report();value["early_pairs"][0]["observations"][3]["taps"]["20"]["Gain"]=0.
        with self.assertRaises(RuntimeError):validate(value)
    def test_current_profile_family_restore_and_prior_helpers_required(self):
        for key in ("current_dispatch_profiles_restored","preset_state_restored","whiz_regression_passed"):
            value=report();value[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_fake_trace_replay_and_full_acceptance_rejected(self):
        for key in ("trace_results_injected","tap_callbacks_replayed","full_acceptance","audible_playback_tested"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
