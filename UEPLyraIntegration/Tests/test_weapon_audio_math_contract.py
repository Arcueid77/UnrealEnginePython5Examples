"""Reject missing native static/BP calls and weak original/output/ABI evidence."""
import unittest
from uep_lyra_weapons.weapon_audio_math_contract import SIDE_PLAN,WHIZ_PLAN,validate


def report():
    value=dict(status="passed",error=None,full_acceptance=False,network_acceptance=False,audible_playback_tested=False,cpp_compile_executed=False,
        static_functions_registered_as_mixins=False,physics_or_audio_state_written=False,original_static_signatures_preserved=True,router_profile_restored=True,original_player_health_unchanged=True)
    for field,plan in (("side_pairs",SIDE_PLAN),("whiz_pairs",WHIZ_PLAN)):
        value[field]=[dict(index=i,direct_and_bp_callers_equal=True,original_python_outputs_equal=True,native_next_random_equal=True,fallback_dispatches=2,python_dispatches=2) for i,_ in enumerate(plan)]
    return value


class TestWeaponAudioMathContract(unittest.TestCase):
    def test_complete_native_matrix(self):self.assertEqual(validate(report())["native_static_and_bp_invocations"],1704)
    def test_missing_or_reordered_matrix_rejected(self):
        for field in ("side_pairs","whiz_pairs"):
            value=report();value[field].pop()
            with self.subTest(field=field),self.assertRaises(RuntimeError):validate(value)
    def test_outputs_callers_rng_and_actual_dispatch_required(self):
        for key,val in (("direct_and_bp_callers_equal",False),("original_python_outputs_equal",False),("native_next_random_equal",False),("fallback_dispatches",0),("python_dispatches",0)):
            value=report();value["whiz_pairs"][0][key]=val
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_no_static_mixin_or_full_audio_acceptance_overclaim(self):
        for key in ("full_acceptance","audible_playback_tested","static_functions_registered_as_mixins","physics_or_audio_state_written"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_static_abi_and_original_state_restore_required(self):
        for key in ("original_static_signatures_preserved","router_profile_restored","original_player_health_unchanged"):
            value=report();value[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
