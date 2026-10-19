"""Native control entries do not substitute for natural physics/overlap/life."""
import copy
import unittest
from uep_lyra_weapons import netshooter_actor_contract as policy


def report():
    data=dict(status="passed",error=None,native_mode="Standalone",ray_pairs=[],natural_cases=[],overlap_cases=[],controlled_hit_method_entries=True,
        production_profiles_restored=True,all_test_actors_destroyed=True,original_player_health_unchanged=True)
    data.update({key:False for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested","health_properties_written",
        "natural_hit_callback_replayed","overlap_callback_replayed","life_callback_replayed","rpc_function_overridden")})
    for number in policy.COUNTS:
        event=dict(native_geometry_matches=True,native_template_matches=True,sphere_hidden=True)
        value=dict(native_hit_body_count=1,duplicate_hit_do_once_blocked=True,native_rpc_flags_preserved=True,ray_components=max(0,number+1),spawn_events=[copy.deepcopy(event) for _ in range(max(0,number+1))])
        data["ray_pairs"].append(dict(number=number,same_components=True,same_start=True,same_next_native_random=True,blueprint=value,python=copy.deepcopy(value)))
    for profile in policy.PROFILES:
        data["natural_cases"].append(dict(profile=profile,native_hit_body_count=1,native_moving_samples=3,initial_speed=2500.,gravity_scale=.5,ray_components_before_end=13,destroyed_by_native_life_delay=True,life_elapsed=12.02,hit_frame_delta=.016))
        data["overlap_cases"].append(dict(profile=profile,native_overlap_callbacks=1,native_source_matches_instigator=True,native_rpc_body_count=1,native_template_matches=True,health_before=100.,health_after=88.,native_health_damage_observed=True))
    return data


class TestNetShooterActorContract(unittest.TestCase):
    def setUp(self):self.data=report()
    def rejected(self):
        with self.assertRaises(RuntimeError):policy.validate(self.data)
    def test_complete_native_matrix(self):self.assertEqual(policy.validate(self.data)["natural_projectile_cases"],2)
    def test_random_draw_order_changed(self):self.data["ray_pairs"][0]["same_next_native_random"]=False;self.rejected()
    def test_native_geometry_differs(self):self.data["ray_pairs"][3]["python"]["spawn_events"][0]["native_geometry_matches"]=False;self.rejected()
    def test_original_template_not_used(self):self.data["ray_pairs"][3]["python"]["spawn_events"][0]["native_template_matches"]=False;self.rejected()
    def test_do_once_bypassed(self):self.data["ray_pairs"][1]["python"]["duplicate_hit_do_once_blocked"]=False;self.rejected()
    def test_rpc_flags_changed(self):self.data["ray_pairs"][1]["python"]["native_rpc_flags_preserved"]=False;self.rejected()
    def test_physics_never_moved(self):self.data["natural_cases"][0]["native_moving_samples"]=0;self.rejected()
    def test_projectile_speed_changed(self):self.data["natural_cases"][0]["initial_speed"]=0.;self.rejected()
    def test_original_lifetime_not_respected(self):self.data["natural_cases"][0]["life_elapsed"]=1.;self.rejected()
    def test_overlap_callback_replayed(self):self.data["overlap_callback_replayed"]=True;self.rejected()
    def test_natural_hit_callback_replayed(self):self.data["natural_hit_callback_replayed"]=True;self.rejected()
    def test_no_actual_native_overlap(self):self.data["overlap_cases"][0]["native_overlap_callbacks"]=0;self.rejected()
    def test_no_actual_native_effect_damage(self):self.data["overlap_cases"][0]["health_after"]=100.;self.rejected()
    def test_native_effect_source_substituted(self):self.data["overlap_cases"][0]["native_source_matches_instigator"]=False;self.rejected()
    def test_health_repaired_by_fixture(self):self.data["health_properties_written"]=True;self.rejected()
