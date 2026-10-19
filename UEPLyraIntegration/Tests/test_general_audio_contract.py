"""Require actual receiver forwarding and do not overclaim unrun error branches."""
import copy
import unittest
from uep_lyra_audio.general_audio_contract import PLAN,validate


def report():
    value=dict(status="passed",error=None,pairs=[])
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","static_functions_registered_as_mixins","native_error_branches_exercised","cpp_compile_executed"):value[key]=False
    for key in ("static_signature_flags_preserved","router_profile_restored","music_profile_family_restored","manager_fields_restored","owned_actor_destroyed","player_health_unchanged"):value[key]=True
    for index,(positive,mode,alpha) in enumerate(PLAN):
        state=dict(intensity=0.,positive_arguments=[positive],parameters={})
        value["pairs"].append(dict(index=index,observations=[copy.deepcopy(state) for _ in range(4)],fallback_dispatches=2,python_dispatches=2,python_manager_calls=2))
    return value


class TestGeneralAudioContract(unittest.TestCase):
    def test_complete_actual_static_bp_matrix(self):self.assertEqual(validate(report())["actual_music_receiver_entries"],72)
    def test_registered_router_without_actual_manager_forwarding_rejected(self):
        value=report();value["pairs"][0]["python_manager_calls"]=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_identical_wrong_positive_argument_rejected(self):
        value=report()
        for item in value["pairs"][0]["observations"]:item["positive_arguments"]=[True]
        with self.assertRaises(RuntimeError):validate(value)
    def test_receiver_state_or_parameters_must_match_every_caller(self):
        value=report();value["pairs"][0]["observations"][3]["parameters"]["other"]=1
        with self.assertRaises(RuntimeError):validate(value)
    def test_complete_current_music_family_restore_required(self):
        value=report();value["music_profile_family_restored"]=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_static_mixin_or_native_error_path_overclaim_rejected(self):
        for key in ("static_functions_registered_as_mixins","native_error_branches_exercised","full_acceptance"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
