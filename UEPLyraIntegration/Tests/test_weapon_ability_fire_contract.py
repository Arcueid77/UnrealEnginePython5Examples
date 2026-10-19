"""Reject synthetic callbacks, missing authority damage and native RNG drift."""
import copy
import unittest
from uep_lyra_weapons import weapon_ability_fire_contract as policy


def report():
    data=dict(status="passed",error=None,native_mode="Standalone",montage_pairs=[],shots=[],failure_cases=[],lifecycle_cases=[],native_clear_ability_timers_cvar=1)
    data.update({field:False for field in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested",
        "activation_handler_replayed","target_data_callback_replayed","montage_callback_replayed","timer_callback_replayed","health_properties_written","ammo_properties_written","timer_properties_written")})
    data.update({field:True for field in ("original_player_health_unchanged","original_inventory_ammo_restored","original_control_rotation_restored","observer_profiles_restored","all_test_actors_destroyed","native_global_seed_api_used")})
    data["montage_pairs"]=[dict(same_asset=True,same_next_native_random=True) for _ in range(len(policy.WEAPONS)*len(policy.NORMALS)*2*8)]
    for weapon,profile,field in policy.PLAN:
        data["shots"].append(dict(weapon=weapon,profile=profile,field_enabled=field,native_class=policy.WEAPONS[weapon],native_source_object_matches=True,input_press_count=1,input_released=True,
            native_activation_observed=True,native_target_callbacks=1,target_count=1,blocking_hits=1,ammo_before=10,ammo_after=9,target_health_before=100.,target_health_after=75.,native_enemy_hit=True,
            weapon_actor_fire_calls=1,native_tasks_observed=1,native_montage_playing=True,native_ability_ended=True,field_actor_count=int(field),field_actor_poses_match=True,native_completion_callbacks=1,no_handler_errors=True))
    for weapon in policy.WEAPONS:
        for profile in policy.PROFILES:
            data["failure_cases"].append(dict(weapon=weapon,profile=profile,actual_native_message_dispatch=True,foreign_avatar_noop=True,allowed_message_disabled_flag=True,native_failure_montage_observed=True,
                repeat_throttled=True,native_timer_reenabled_flag=True,reenable_elapsed=1.01,profile_switch_did_not_create_listener=True,source_listener_added_once=True))
    for profile in policy.PROFILES:
        for kind,name in (("complete","MontageCompleted"),("cancel","MontageInterrupted"),("interrupt","MontageInterrupted"),("null-montage","MontageCancelled")):
            data["lifecycle_cases"].append(dict(profile=profile,kind=kind,native_input_used=True,native_activation_montage=kind!="null-montage",native_ability_ended=True,expected_native_callback=name,
                observed_native_callbacks=[dict(name=name,time=.2)],intervention_used=kind in ("cancel","interrupt")))
    return data


class TestWeaponAbilityFireContract(unittest.TestCase):
    def setUp(self):self.data=report()
    def rejected(self):
        with self.assertRaises(RuntimeError):policy.validate(self.data)
    def test_complete_native_matrix(self):self.assertEqual(policy.validate(self.data)["native_equipped_input_shots"],8)
    def test_montage_native_asset_choice_differs(self):self.data["montage_pairs"][0]["same_asset"]=False;self.rejected()
    def test_extra_native_rng_draw(self):self.data["montage_pairs"][0]["same_next_native_random"]=False;self.rejected()
    def test_named_output_pair_missing(self):self.data["montage_pairs"].pop();self.rejected()
    def test_wrong_native_child_class(self):self.data["shots"][0]["native_class"]="/Script/GameplayAbilities.GameplayAbility";self.rejected()
    def test_no_actual_native_input(self):self.data["shots"][0]["input_press_count"]=0;self.rejected()
    def test_input_not_released(self):self.data["shots"][0]["input_released"]=False;self.rejected()
    def test_multiple_native_target_callbacks(self):self.data["shots"][0]["native_target_callbacks"]=2;self.rejected()
    def test_no_native_commit_cost(self):self.data["shots"][0]["ammo_after"]=10;self.rejected()
    def test_no_native_enemy_damage(self):self.data["shots"][0]["target_health_after"]=100.;self.rejected()
    def test_hit_someone_other_than_arranged_enemy(self):self.data["shots"][0]["native_enemy_hit"]=False;self.rejected()
    def test_source_object_substituted(self):self.data["shots"][0]["native_source_object_matches"]=False;self.rejected()
    def test_firing_cue_not_delivered_to_weapon_actor(self):self.data["shots"][0]["weapon_actor_fire_calls"]=0;self.rejected()
    def test_native_montage_task_not_observed(self):self.data["shots"][0]["native_tasks_observed"]=0;self.rejected()
    def test_optional_field_actor_not_spawned(self):self.data["shots"][1]["field_actor_count"]=0;self.rejected()
    def test_field_actor_uses_wrong_hit_position(self):self.data["shots"][1]["field_actor_poses_match"]=False;self.rejected()
    def test_native_completion_did_not_execute(self):self.data["shots"][0]["native_completion_callbacks"]=0;self.rejected()
    def test_failure_message_was_not_actual_native_dispatch(self):self.data["failure_cases"][0]["actual_native_message_dispatch"]=False;self.rejected()
    def test_foreign_avatar_allowed(self):self.data["failure_cases"][0]["foreign_avatar_noop"]=False;self.rejected()
    def test_failure_message_did_not_throttle(self):self.data["failure_cases"][0]["allowed_message_disabled_flag"]=False;self.rejected()
    def test_retriggered_failure_timer_on_suppressed_repeat(self):self.data["failure_cases"][0]["reenable_elapsed"]=1.8;self.rejected()
    def test_listener_created_again_on_profile_switch(self):self.data["failure_cases"][0]["profile_switch_did_not_create_listener"]=False;self.rejected()
    def test_health_repair_cannot_substitute_native_damage(self):self.data["health_properties_written"]=True;self.rejected()
    def test_direct_target_callback_replay_rejected(self):self.data["target_data_callback_replayed"]=True;self.rejected()
    def test_actual_timer_callback_replay_rejected(self):self.data["timer_callback_replayed"]=True;self.rejected()
    def test_original_inventory_not_restored(self):self.data["original_inventory_ammo_restored"]=False;self.rejected()
    def test_original_native_completion_callback_missing(self):self.data["lifecycle_cases"][0]["observed_native_callbacks"]=[dict(name="FireComplete",time=2.)];self.rejected()
    def test_native_gas_timer_cleanup_was_bypassed(self):self.data["lifecycle_cases"][0]["observed_native_callbacks"].append(dict(name="FireComplete",time=2.01));self.rejected()
