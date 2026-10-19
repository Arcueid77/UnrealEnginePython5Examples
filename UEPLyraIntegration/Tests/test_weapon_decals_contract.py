"""Reject sticky-array cleanup regressions and synthetic native evidence claims."""
import unittest
from uep_lyra_weapons import weapon_decals_contract as policy


def report():
    data=dict(status="passed",error=None,native_mode="Standalone",cases=[],timer_cases=[])
    data.update({field:False for field in ("full_acceptance","network_acceptance","packaged_runtime","pixels_tested","audio_playback_tested","timer_properties_written","latent_callback_replayed","health_properties_written")})
    data.update({field:True for field in ("native_warmup_ready","all_test_actors_destroyed","all_test_components_destroyed","original_pawn_health_unchanged","production_classes_restored","original_view_restored","original_signature_restored")})
    for profile in policy.PROFILES:
        for index,name in enumerate(policy.CASES):
            points=[[100.,0.,25.]]*len(policy.SURFACES[index]);normals=[]
            data["cases"].append(dict(profile=profile,name=name,actual_selected_fire_dispatch=True,component_valid=True,
                same_cached=name not in ("cold","replace-inactive"),trigger=policy.TRIGGERS[index],trigger_parameter=policy.TRIGGERS[index],
                input_surfaces=list(policy.SURFACES[index]),surface_types=list(policy.EXPECTED_SURFACES[index]),native_surfaces=list(policy.EXPECTED_SURFACES[index]),
                position_array_kind="NiagaraDataInterfaceArrayPosition",native_positions=points,positions=points,normals=normals,native_normals=normals,native_hit_count=len(points),
                world_location=[0.,0.,0.],world_rotation=[0.,0.,0.],world_scale=[1.,1.,1.],unattached=True,native_auto_destroy=True))
        data["timer_cases"].append(dict(profile=profile,native_retrigger_observed=True,survived_original_deadline=True,destroyed_after_retrigger=True,destroy_elapsed=4.05,
            native_callback_elapsed=4.05,hold_callback_elapsed=[3.01,6.02],valid_inactive_kept_actor_alive=True,native_repeat_cleanup_observed=True,destroyed_after_component_removal=True))
    return data


class TestWeaponDecalsContract(unittest.TestCase):
    def setUp(self):self.data=report()
    def rejected(self):
        with self.assertRaises(RuntimeError):policy.validate(self.data)
    def test_complete_native_matrix(self):self.assertEqual(policy.validate(self.data)["actual_native_niagara_trials"],10)
    def test_surface_tail_truncated(self):self.data["cases"][1]["surface_types"]=[3];self.rejected()
    def test_native_surface_array_not_updated(self):self.data["cases"][0]["native_surfaces"]=[];self.rejected()
    def test_vector_interface_substituted_for_position(self):self.data["cases"][0]["position_array_kind"]="NiagaraDataInterfaceArrayFloat3";self.rejected()
    def test_native_position_readback_differs(self):self.data["cases"][0]["native_positions"]=[];self.rejected()
    def test_native_normal_readback_differs(self):self.data["cases"][0]["native_normals"]=[[1.,0.,0.]];self.rejected()
    def test_native_count_uses_surface_tail(self):self.data["cases"][1]["native_hit_count"]=4;self.rejected()
    def test_inactive_cache_reused(self):self.data["cases"][3]["same_cached"]=True;self.rejected()
    def test_active_cache_recreated(self):self.data["cases"][1]["same_cached"]=False;self.rejected()
    def test_trigger_not_reset_on_replacement(self):self.data["cases"][3]["trigger"]=False;self.rejected()
    def test_native_trigger_store_not_updated(self):self.data["cases"][0]["trigger_parameter"]=False;self.rejected()
    def test_component_attached_to_decal_actor(self):self.data["cases"][0]["unattached"]=False;self.rejected()
    def test_spawn_uses_actor_location(self):self.data["cases"][0]["world_location"]=[200.,100.,50.];self.rejected()
    def test_native_cleanup_callback_times_missing(self):self.data["timer_cases"][0]["hold_callback_elapsed"]=[];self.rejected()
    def test_native_delay_does_not_repeat_for_valid_inactive(self):self.data["timer_cases"][0]["valid_inactive_kept_actor_alive"]=False;self.rejected()
    def test_profile_duplicate_cannot_replace_other_profile_timer(self):self.data["timer_cases"][1]["profile"]="BlueprintFallback";self.rejected()
    def test_fixture_replayed_native_continuation(self):self.data["latent_callback_replayed"]=True;self.rejected()
    def test_orphaned_world_owned_niagara_component(self):self.data["all_test_components_destroyed"]=False;self.rejected()
