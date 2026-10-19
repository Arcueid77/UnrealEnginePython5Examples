"""Native FX cache/order/data evidence must cover all three inherited classes."""
import copy
import unittest
from uep_lyra_weapons import weapon_actor_fire_contract as policy


def report():
    result=dict(status="passed",error=None,native_mode="Standalone",cases=[],observation_errors=[],test_actors_destroyed=True,
        original_pawn_health_unchanged=True,fx_observers_removed=True,original_fx_signatures_restored=True,production_parent_binding_preserved=True)
    result.update({name:False for name in ("full_acceptance","network_acceptance","packaged_runtime","audio_playback_tested","pixels_tested","real_gas_firing_tested","health_properties_written","begin_play_migrated")})
    for cls in policy.CLASSES:
        for profile in policy.PROFILES:
            for name in policy.CASES:
                count=3 if name=="fake" else 2 if name=="reuse" else 1
                positions=[[100.,0.,0.]]*count;normals=[[-1.,0.,0.]]*count;surfaces=[0]*count;muzzle=[0.,0.,0.]
                events=[dict(**{"class":fx},attached_to_weapon_mesh=True,positions=positions,normals=normals,surfaces=surfaces,
                    mesh_is_weapon_mesh=True,enable_flags=[True]*3,muzzle=muzzle,distance_threshold=500.) for fx in policy.FX]
                result["cases"].append(dict(name=name,profile=profile,**{"class":cls},parent_dispatch_verified=True,events=events,
                    positions=positions,normals=normals,surfaces=surfaces,muzzle=muzzle,input_count=2 if name=="reuse" else 1,
                    same_cached=[False]*3 if name=="cold" else [True,False,True] if name=="replace-impact" else [True]*3,
                    delta=dict(fx_calls=3,spawns=3 if name=="cold" else 1 if name=="replace-impact" else 0,fake_calls=int(name=="fake"))))
    return result


class TestWeaponActorFireContract(unittest.TestCase):
    def setUp(self):self.data=report()
    def rejected(self):
        with self.assertRaises(RuntimeError):policy.validate(self.data)
    def test_native_matrix(self):self.assertEqual(policy.validate(self.data)["native_original_fx_entries"],72)
    def test_wrong_fx_call_order(self):self.data["cases"][0]["events"].reverse();self.rejected()
    def test_fx_not_attached_to_weapon_mesh(self):self.data["cases"][0]["events"][0]["attached_to_weapon_mesh"]=False;self.rejected()
    def test_missing_decal_data_copy(self):self.data["cases"][0]["events"][2]["positions"]=[];self.rejected()
    def test_missing_impact_muzzle(self):self.data["cases"][0]["events"][1]["muzzle"]=[1.,1.,1.];self.rejected()
    def test_spawn_inputs_changed(self):self.data["cases"][0]["events"][0]["enable_flags"]=[True,False,True];self.rejected()
    def test_existing_fx_recreated(self):self.data["cases"][1]["same_cached"]=[False]*3;self.rejected()
    def test_invalid_impact_not_recreated(self):self.data["cases"][2]["same_cached"]=[True]*3;self.rejected()
    def test_fake_arrays_not_appended(self):self.data["cases"][3]["positions"]=[];self.rejected()
    def test_missing_child_class_hidden_by_duplicate(self):self.data["cases"][-1]=self.data["cases"][0];self.rejected()
    def test_fx_observers_not_removed(self):self.data["fx_observers_removed"]=False;self.rejected()
    def test_audio_pixels_overclaim(self):self.data["audio_playback_tested"]=True;self.rejected()
