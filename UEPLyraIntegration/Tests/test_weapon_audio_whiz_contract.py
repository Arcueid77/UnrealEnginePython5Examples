"""Reject wrong native audio branches, geometry, fields and restoration evidence."""
import copy
import unittest
from uep_lyra_weapons.weapon_audio_whiz_contract import PLAN,TRAJECTORIES,SOUND,expected_geometry,validate


def report(no_sound=False):
    value=dict(status="passed",error=None,no_sound=no_sound,math_regression=[True]*8,whiz_pairs=[])
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","preset_asset_saved","cpp_compile_executed","static_functions_registered_as_mixins"):value[key]=False
    for key in ("router_profile_restored","owned_components_destroyed","owned_actors_destroyed","player_health_unchanged","original_static_signatures_preserved","dispatch_regression_passed"):value[key]=True
    for index,(label,surface,trajectory) in enumerate(PLAN):
        origin,impact=TRAJECTORIES[trajectory];eligible=label=="foreign" and surface!=1;geometry=expected_geometry((0.,0.,0.),origin,impact)
        state=dict(sound=SOUND,location=geometry["location"],playing=True,auto_destroy=True,volume=1.,pitch=1.,attenuation_success=True,
            attenuation=dict(StereoSpread=geometry["spread"],OtherNativeField=17),parameters=dict(OnsetDelay=geometry["onset"],SwapLR=geometry["swap"]))
        states=[state] if eligible and not no_sound else []
        value["whiz_pairs"].append(dict(index=index,observations=[copy.deepcopy(states) for _ in range(4)],fallback_dispatches=2,python_dispatches=2,
            math_dispatches=4 if eligible else 0,listener=[0.,0.,0.],origin=list(origin),impact=list(impact)))
    return value


class TestWeaponAudioWhizContract(unittest.TestCase):
    def test_both_native_backends_require_full_matrix(self):
        self.assertEqual(validate(report())["actual_audio_components"],60);self.assertEqual(validate(report(True))["actual_audio_components"],0)
    def test_missing_or_disagreeing_native_callers_rejected(self):
        for operation in (lambda row:row["observations"].pop(),lambda row:row["observations"][0].clear()):
            value=report();operation(value["whiz_pairs"][0])
            with self.assertRaises(RuntimeError):validate(value)
    def test_identically_wrong_native_parameter_values_rejected(self):
        for key,wrong in (("OnsetDelay",-1.),("SwapLR",17.)):
            value=report()
            for observation in value["whiz_pairs"][0]["observations"]:observation[0]["parameters"][key]=wrong
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_full_attenuation_state_disagreement_rejected(self):
        value=report();value["whiz_pairs"][0]["observations"][3][0]["attenuation"]["OtherNativeField"]=99
        with self.assertRaises(RuntimeError):validate(value)
    def test_disabled_backend_does_not_excuse_skipped_original_math(self):
        value=report(True);value["whiz_pairs"][0]["math_dispatches"]=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_profile_restore_and_prior_static_helper_regressions_required(self):
        for key in ("router_profile_restored","dispatch_regression_passed","owned_components_destroyed"):
            value=report();value[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_full_audio_or_version_acceptance_overclaim_rejected(self):
        for key in ("full_acceptance","audible_playback_tested","static_functions_registered_as_mixins"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
