"""Reject counter-only Niagara claims and replacement timer behavior."""
import copy
import unittest
from uep_lyra_weapons import weapon_fire_fx_contract as policy


def report():
    data=dict(status="passed",error=None,native_mode="Standalone",cases=[],timer_cases=[],native_warmup_ready=True,
        all_test_actors_destroyed=True,original_pawn_health_unchanged=True,production_classes_restored=True)
    data.update({field:False for field in ("full_acceptance","network_acceptance","packaged_runtime","pixels_tested","audio_playback_tested","timer_properties_written","latent_callback_replayed","health_properties_written")})
    for profile in policy.PROFILES:
        for name in policy.CASES:
            triggers=[name in ("cold","replace-inactive")]*3
            data["cases"].append(dict(profile=profile,name=name,actual_selected_fire_dispatch=True,
                components=[dict(valid=True,trigger_parameter=value,relative_rotation=[0.,0.,90.],attached_to_root=True) for value in triggers],triggers=triggers,
                same_cached=[False]*3 if name=="cold" else [True,False,True] if name=="replace-inactive" else [True]*3,
                direction_parameter=[1.,0.,0.],expected_direction=[1.,0.,0.],tracer_array=[[100.,0.,0.]],impacts=[[100.,0.,0.]]))
        data["timer_cases"].append(dict(profile=profile,native_retrigger_observed=True,survived_original_deadline=True,destroyed_after_retrigger=True,destroy_elapsed=4.05,
            valid_inactive_kept_actor_alive=True,native_repeat_cleanup_observed=True,destroyed_after_component_removal=True))
    return data


class TestWeaponFireFXContract(unittest.TestCase):
    def setUp(self):self.data=report()
    def rejected(self):
        with self.assertRaises(RuntimeError):policy.validate(self.data)
    def test_complete_native_matrix(self):self.assertEqual(policy.validate(self.data)["actual_native_niagara_trials"],8)
    def test_actual_trigger_store_differs(self):self.data["cases"][0]["components"][0]["trigger_parameter"]=False;self.rejected()
    def test_wrong_direction_store(self):self.data["cases"][0]["direction_parameter"]=[0.,0.,0.];self.rejected()
    def test_array_writes_not_applied(self):self.data["cases"][0]["tracer_array"]=[];self.rejected()
    def test_active_cache_recreated(self):self.data["cases"][1]["same_cached"]=[False]*3;self.rejected()
    def test_inactive_cache_reused(self):self.data["cases"][3]["same_cached"]=[True]*3;self.rejected()
    def test_disabled_branch_changes_trigger(self):self.data["cases"][2]["triggers"][0]=True;self.rejected()
    def test_old_deadline_not_retriggered(self):self.data["timer_cases"][0]["survived_original_deadline"]=False;self.rejected()
    def test_destroyed_too_early(self):self.data["timer_cases"][0]["destroy_elapsed"]=3.;self.rejected()
    def test_inactive_valid_component_ignored(self):self.data["timer_cases"][0]["valid_inactive_kept_actor_alive"]=False;self.rejected()
    def test_fixture_replayed_native_resume(self):self.data["latent_callback_replayed"]=True;self.rejected()
    def test_pixels_overclaim(self):self.data["pixels_tested"]=True;self.rejected()
