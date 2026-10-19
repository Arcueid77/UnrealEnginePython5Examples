"""Reject missing native input, inherited body fallthrough and cleanup claims."""
import unittest
from uep_lyra_weapons.netshooter_ability_contract import PLAN,validate


def report():
    value=dict(status="passed",error=None,native_mode="Standalone",cases=[])
    for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested",
                "activation_handler_replayed","target_data_callback_replayed","montage_callback_replayed","health_properties_written",
                "ammo_properties_written","projectile_spawn_requested_by_fixture","projectile_physics_accepted"):value[key]=False
    for key in ("native_independent_camera_view_target_fixture","original_view_target_restored","inherited_added_listener_once","original_inventory_restored","original_player_health_unchanged","original_player_pose_control_movement_restored",
                "all_test_actors_destroyed","production_profiles_restored","cue_observer_restored"):value[key]=True
    for profile,kind in PLAN:
        row=dict(profile=profile,kind=kind,native_input_used=True,activations=1,native_ammo_cost=1,target_data_entries=1,parent_target_data_calls=0,parent_fire_timers_or_complete=0,
            native_firing_cue_entries=1,native_projectile_spawns=1,native_callbacks=["OnCancelled" if kind=="null-montage" else "OnInterrupted" if kind in ("cancel","interrupt") else "OnCompleted"],native_montage_observed=kind!="null-montage")
        for key in ("native_cue_geometry_matches","native_cue_default_fields_match","controller_forward_differs_from_camera_forward","native_location_direction_match",
                    "native_projectile_transform_matches","native_owner_none_instigator_source","native_default_exposed_hit","projectile_destroyed_by_fixture_before_movement_tick","native_ability_ended"):row[key]=True
        value["cases"].append(row)
    return value


class TestNetShooterAbilityContract(unittest.TestCase):
    def test_complete_bounded_native_matrix_passes(self):self.assertEqual(validate(report())["native_input_cases"],10)
    def test_missing_or_reordered_native_matrix_rejected(self):
        for mutate in (lambda r:r["cases"].pop(),lambda r:r["cases"].reverse()):
            value=report();mutate(value)
            with self.assertRaises(RuntimeError):validate(value)
    def test_native_cost_input_callback_or_spawn_counts_cannot_be_substituted(self):
        for key in ("activations","native_ammo_cost","target_data_entries","native_firing_cue_entries","native_projectile_spawns"):
            value=report();value["cases"][0][key]=0
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_shared_parent_target_body_or_unused_timer_fallthrough_rejected(self):
        for key in ("parent_target_data_calls","parent_fire_timers_or_complete"):
            value=report();value["cases"][0][key]=1
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_callback_identity_and_real_montage_evidence_required(self):
        for key,val in (("native_callbacks",["OnCancelled"]),("native_montage_observed",False)):
            value=report();value["cases"][0][key]=val
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_native_geometry_spawn_defaults_and_cleanup_required(self):
        for key in ("native_cue_geometry_matches","native_cue_default_fields_match","controller_forward_differs_from_camera_forward","native_location_direction_match",
                    "native_projectile_transform_matches","native_owner_none_instigator_source","native_default_exposed_hit","projectile_destroyed_by_fixture_before_movement_tick","native_ability_ended"):
            value=report();value["cases"][0][key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_no_full_network_physics_or_callback_replay_overclaim(self):
        for key in ("full_acceptance","network_acceptance","projectile_physics_accepted","projectile_spawn_requested_by_fixture","activation_handler_replayed","target_data_callback_replayed","montage_callback_replayed"):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
    def test_actual_inheritance_and_original_state_restoration_required(self):
        for key in ("native_independent_camera_view_target_fixture","original_view_target_restored","inherited_added_listener_once","original_inventory_restored","original_player_health_unchanged","original_player_pose_control_movement_restored","all_test_actors_destroyed","production_profiles_restored","cue_observer_restored"):
            value=report();value[key]=False
            with self.subTest(key=key),self.assertRaises(RuntimeError):validate(value)
