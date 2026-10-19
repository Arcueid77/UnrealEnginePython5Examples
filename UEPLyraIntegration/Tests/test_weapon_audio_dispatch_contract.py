"""Reject copied wrong states, missing native callers and cleanup/acceptance drift."""
import copy
import unittest
from uep_lyra_weapons.weapon_audio_dispatch_contract import TAP_PLAN,PARAM_PLAN,FIRE_PLAN,DEBUG_PLAN,expected_tap,validate


def report():
    value=dict(status="passed",error=None,local_pawn="native-pawn",actual_magazine_ammo=12,remote_pawn_seed=57,owned_tap_id=16,
        camera_location=[0.,0.,0.],camera_right=[0.,1.,0.],math_regression=[True]*8)
    for key in ("full_acceptance","network_acceptance","audible_playback_tested","debug_pixels_tested","cpp_compile_executed","static_functions_registered_as_mixins","preset_asset_saved"):value[key]=False
    for key in ("router_profile_restored","music_observer_removed","owned_actors_destroyed","original_instigator_restored","original_player_health_unchanged","preset_state_restored","original_static_signatures_preserved"):value[key]=True
    for label,plan in (("tap_pairs",TAP_PLAN),("parameter_pairs",PARAM_PLAN),("fire_pairs",FIRE_PLAN),("debug_pairs",DEBUG_PLAN)):
        rows=[]
        for index,item in enumerate(plan):
            if label=="tap_pairs":state=dict(TapId=16,TapLineMode=1,OutputChannel=0,**expected_tap(item,[0.,0.,0.],[0.,1.,0.]))
            elif label=="parameter_pairs":
                fields=dict(PawnSeed=-1 if item=="local" else 57 if item=="remote" else 321,MagazineAmmo=12 if item=="local" else 777,Unrelated=19);state=[fields.copy(),fields.copy()]
            elif label=="fire_pairs":state=[dict(player="native-pawn",strength=item[1])] if item[0]=="local" else []
            else:state=True
            rows.append(dict(index=index,observations=[copy.deepcopy(state) for _ in range(4)],fallback_dispatches=2,python_dispatches=2,expected_behavior=True))
        value[label]=rows
    return value


class TestWeaponAudioDispatchContract(unittest.TestCase):
    def test_full_observed_matrix(self):self.assertEqual(validate(report())["dispatch_invocations"],568)
    def test_missing_native_caller_or_profile_rejected(self):
        for key in ("tap_pairs","parameter_pairs","fire_pairs","debug_pairs"):
            value=report();value[key][0]["observations"].pop()
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_identically_wrong_native_tap_states_rejected(self):
        for key,wrong in (("Gain",0.),("DelayLength",1.),("PanInDegrees",11.),("OutputChannel",7),("TapLineMode",2),("TapId",3)):
            value=report()
            for observation in value["tap_pairs"][0]["observations"]:observation[key]=wrong
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_nonlocal_ammo_write_even_when_all_four_states_equal_rejected(self):
        value=report()
        for observation in value["parameter_pairs"][1]["observations"]:
            for audio in observation:audio["MagazineAmmo"]=12
        with self.assertRaises(RuntimeError):validate(value)
    def test_foreign_music_message_or_clamped_strength_rejected(self):
        for index in (0,4):
            value=report();value["fire_pairs"][index]["observations"]=[[dict(player="native-pawn",strength=0.)] for _ in range(4)]
            with self.subTest(index=index),self.assertRaises(RuntimeError):validate(value)
    def test_identical_debug_void_failure_rejected(self):
        value=report();value["debug_pairs"][0]["observations"]=[False]*4
        with self.assertRaises(RuntimeError):validate(value)
    def test_profile_call_counts_and_prior_math_regression_required(self):
        for key in ("python_dispatches","fallback_dispatches"):
            value=report();value["tap_pairs"][0][key]=0
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
        value=report();value["math_regression"][0]=False
        with self.assertRaises(RuntimeError):validate(value)
    def test_cleanup_and_scope_overclaim_rejected(self):
        for key in ("preset_state_restored","music_observer_removed","original_instigator_restored","router_profile_restored"):
            value=report();value[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
        for key in ("audible_playback_tested","full_acceptance","static_functions_registered_as_mixins","preset_asset_saved"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
