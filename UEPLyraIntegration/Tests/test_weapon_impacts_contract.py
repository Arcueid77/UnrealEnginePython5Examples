"""Reject native impact array/channel/caching and lifetime evidence gaps."""
import copy
import unittest
from uep_lyra_weapons import weapon_impacts_contract as policy


def report():
    data=dict(status="passed",error=None,native_mode="Standalone",cases=[],bucket_cases=[],fire_cases=[],channel_cases=[],timer_cases=[])
    data.update({key:False for key in ("full_acceptance","network_acceptance","packaged_runtime","pixels_tested","audio_playback_tested","timer_properties_written","latent_callback_replayed","health_properties_written","data_channel_buffers_written_by_fixture")})
    data.update({key:True for key in ("native_warmup_ready","all_test_actors_destroyed","all_test_components_destroyed","original_pawn_health_unchanged","production_classes_restored","original_view_restored","original_signature_restored","function_locals_not_actor_properties")})
    for profile in policy.PROFILES:
        for index,name in enumerate(policy.BUCKET_CASES):
            points=[[100.+i*10.,index,25.] for i in range(len(policy.BUCKET_SURFACES[index]))];normals=[[-1.,0.,0.] for _ in points]
            groups=[dict(positions=[points[i] for i,s in enumerate(policy.BUCKET_SURFACES[index]) if s==surface],normals=[normals[i] for i,s in enumerate(policy.BUCKET_SURFACES[index]) if s==surface]) for surface in range(policy.BUCKET_LENGTHS[index])]
            data["bucket_cases"].append(dict(profile=profile,name=name,buckets=groups,points=points,normals=normals,input_arrays_unchanged=True,native_struct_type="/Game/Effects/Blueprints/SurfaceImpacts.SurfaceImpacts"))
        for name in policy.ARRAY_CASES:
            points=[[100.,0.,50.]];normals=[[-1.,0.,0.]];muzzle=[25.,-10.,5.]
            native=dict(position_array_kind="NiagaraDataInterfaceArrayPosition",positions=points,normals=normals,number_of_hits=1,muzzle_valid=True,muzzle=muzzle,muzzle_storage_kind="Vector" if name=="character" else "Position")
            data["cases"].append(dict(profile=profile,name=name,component_valid=True,same_cached=name in policy.REUSED,before_parameters=copy.deepcopy(native),native_parameters=native,
                before_location=points[0],world_location=points[0],points=points,normals=normals,muzzle=muzzle,active=True,asset_is_current_template=name!="changed-template-far",unattached=True,world_rotation=[0.,0.,0.],world_scale=[1.,1.,1.]))
        for channels in (False,True):
            data["fire_cases"].append(dict(profile=profile,channels=channels,routes=[dict(method="SpawnFromDataChannels" if channels and surface in (2,3) else "SpawnFromArrays",surface=surface) for surface in range(4)],
                selected_fire_dispatch=True,input_arrays_cleared=True,buckets=[dict(positions=[[100.,0.,50.]],normals=[[-1.,0.,0.]])]*4,cached_surfaces=[0,1] if channels else [0,1,2,3]))
        rows=[dict(position=[float(index),0.,50.],normal=[-1.,0.,0.],muzzle=[25.,-10.,5.],surface=2+index%2,valid=True) for index in range(4)]
        data["channel_cases"].append(dict(profile=profile,native_reader=True,reader_count=4,published=rows,expected=copy.deepcopy(rows)))
        data["timer_cases"].append(dict(profile=profile,native_retrigger_observed=True,survived_original_deadline=True,destroyed_after_retrigger=True,destroy_elapsed=4.05,native_callback_elapsed=4.05,
            valid_inactive_kept_actor_alive=True,native_repeat_cleanup_observed=True,destroyed_after_component_removal=True,native_has_valid_systems=True,hold_callback_elapsed=[3.01,6.02]))
    return data


class TestWeaponImpactsContract(unittest.TestCase):
    def setUp(self):self.data=report()
    def rejected(self):
        with self.assertRaises(RuntimeError):policy.validate(self.data)
    def test_complete_native_matrix(self):self.assertEqual(policy.validate(self.data)["native_published_channel_rows"],8)
    def test_stale_bucket_data_not_cleared(self):self.data["bucket_cases"][2]["buckets"][0]["positions"]=[[999.,0.,0.]];self.rejected()
    def test_sparse_bucket_array_shrunk(self):self.data["bucket_cases"][1]["buckets"].pop();self.rejected()
    def test_function_locals_treated_as_actor_properties(self):self.data["function_locals_not_actor_properties"]=False;self.rejected()
    def test_bucket_helper_cleared_input_early(self):self.data["bucket_cases"][0]["input_arrays_unchanged"]=False;self.rejected()
    def test_far_cache_recreated(self):self.data["cases"][3]["same_cached"]=False;self.rejected()
    def test_equal_distance_cache_reused(self):self.data["cases"][2]["same_cached"]=True;self.rejected()
    def test_template_comparison_added_to_reuse(self):self.data["cases"][6]["asset_is_current_template"]=True;self.rejected()
    def test_invalid_template_overwrote_parameters(self):self.data["cases"][7]["native_parameters"]["number_of_hits"]=3;self.rejected()
    def test_vector_array_replaced_native_position(self):self.data["cases"][0]["native_parameters"]["position_array_kind"]="NiagaraDataInterfaceArrayFloat3";self.rejected()
    def test_native_muzzle_readback_invalid(self):self.data["cases"][0]["native_parameters"]["muzzle_valid"]=False;self.rejected()
    def test_original_character_vector_fallback_not_observed(self):self.data["cases"][8]["native_parameters"]["muzzle_storage_kind"]="Position";self.rejected()
    def test_channel_route_misapplied_to_character(self):self.data["fire_cases"][1]["routes"][1]["method"]="SpawnFromDataChannels";self.rejected()
    def test_fire_inputs_not_cleared(self):self.data["fire_cases"][0]["input_arrays_cleared"]=False;self.rejected()
    def test_channel_path_populated_component_cache(self):self.data["fire_cases"][1]["cached_surfaces"]=[0,1,2,3];self.rejected()
    def test_no_native_channel_reader(self):self.data["channel_cases"][0]["native_reader"]=False;self.rejected()
    def test_published_channel_position_differs(self):self.data["channel_cases"][0]["published"][0]["position"]=[999.,0.,0.];self.rejected()
    def test_published_channel_enum_differs(self):self.data["channel_cases"][0]["published"][0]["surface"]=1;self.rejected()
    def test_fixture_substituted_channel_buffers(self):self.data["data_channel_buffers_written_by_fixture"]=True;self.rejected()
    def test_validity_flag_not_updated_by_native_cleanup(self):self.data["timer_cases"][0]["native_has_valid_systems"]=False;self.rejected()
    def test_native_repeat_callback_too_early(self):self.data["timer_cases"][0]["hold_callback_elapsed"]=[3.,3.1];self.rejected()
    def test_current_production_binding_not_restored(self):self.data["production_classes_restored"]=False;self.rejected()
