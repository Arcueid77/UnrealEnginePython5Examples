"""Synthetic body/velocity report guards, not native acceptance."""
import unittest
import test_character_equipment_hide_contract as hide_models
from uep_lyra_characters.ragdoll_contract import validate, impulse, SCENARIOS, CLASS


def counts(profile, calls=1, velocity=None, strength=500.):
    py = profile == "Python"; velocity = velocity or [0., 0., 0.]
    return dict(python_calls=calls if py else 0, fallback_calls=0 if py else calls,
        collision_calls=calls if py else 0, simulation_calls=calls if py else 0, impulse_calls=calls if py else 0, missing_mesh_noops=0,
        trace=["collision", "simulation", "impulse"]*calls if py else [],
        last_call=dict(bone="Pelvis", strength=strength, velocity=list(velocity), impulse=impulse(velocity, strength),
            collision_profile="Ragdoll", include_self=True, velocity_change=True, normalize_tolerance=.0001) if py else None)


def body(velocity=None, simulating=True):
    return dict(mesh="native-mesh", bone="Pelvis", collision_profile="Ragdoll", simulating=simulating, velocity=list(velocity or [0., 0., 0.]))


def upgrade(value):
    value.update(ragdoll_orchestration_migrated=True, native_physics_or_animation_implementation_changed=False,
        physics_properties_written_directly=False, ragdoll_caller_roots=dict(created=1, released=1))
    return value


def report():
    value = upgrade(hide_models.report()); value["ragdoll_cases"] = []
    for name, calls, profile in SCENARIOS:
        prepared = name != "stationary"; velocity = [150., 50., 80.] if prepared else [0., 0., 0.]; strength = 0. if name == "zero-strength" else 500.
        before = [3., 4., 5.] if prepared else [0., 0., 0.]
        after = [a+calls*b for a, b in zip(before, impulse(velocity, strength))]
        value["ragdoll_cases"].append(dict(name=name, calls=calls, profile=profile, actual_character_class=CLASS, physics_properties_written_directly=False,
            bp_reference_call=True, native_pawn_hidden_unchanged=True, inventory_unchanged=True, actor_was_not_rooted=True,
            owned_strength_restored_before_destroy=True, owned_new_pawn_destroyed=True, no_late_script_work_after_owned_destruction=True,
            owned_team_observers_collected=True, original_active_proxies_preserved=True, ragdoll_quiet_after_destroy=True,
            cleanup=dict(owned_pawn_controller_playerstate_producer_destroyed=True, original_bot_producer_list_preserved=True), native_pooled_cue_observers=[],
            counters=counts(profile, calls, velocity, strength), native_before=body(before, prepared), native_after=body(before), native_after_physics_step=body(after), native_physics_frames_elapsed=2,
            native_launch_producer=prepared, known_physics_velocity_prepared_via_native_api=prepared, input_velocity=velocity, strength=strength,
            single_body_constraint_free_native_control=prepared, fixture_gravity_and_damping_disabled_via_native_api=prepared))
    for row in value["equipment_hide_cases"]:
        row.update(natural_ragdoll_counters=counts(row["profile"]), natural_ragdoll_physical=body())
    return value


class CharacterRagdollReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.report)
    def row(self): return self.report["ragdoll_cases"][3]
    def test_complete_shape_is_only_model(self): self.assertEqual(validate(self.report)["native_ragdoll_pairs"], 4)
    def test_actual_native_body_must_simulate(self): self.row()["native_after"]["simulating"] = False; self.reject()
    def test_actual_collision_profile_required(self): self.row()["native_after"]["collision_profile"] = "Pawn"; self.reject()
    def test_actual_body_velocity_not_only_policy_counter(self): self.row()["native_after_physics_step"]["velocity"] = [0., 0., 0.]; self.reject()
    def test_immediate_read_does_not_stand_in_for_physics_step(self): self.row()["native_physics_frames_elapsed"] = 0; self.reject()
    def test_controlled_fixture_not_claimed_as_full_rig_impulse(self): self.row()["single_body_constraint_free_native_control"] = False; self.reject()
    def test_launch_must_produce_actual_last_velocity(self): self.row()["input_velocity"] = [0., 0., 0.]; self.reject()
    def test_native_known_velocity_preparation_required(self): self.row()["native_before"]["velocity"] = [0., 0., 0.]; self.reject()
    def test_native_original_parameters_required(self): self.row()["counters"]["last_call"]["include_self"] = False; self.reject()
    def test_order_required(self): self.row()["counters"]["trace"] = ["simulation", "collision", "impulse"]; self.reject()
    def test_no_direct_physics_property_writes(self): self.report["physics_properties_written_directly"] = True; self.reject()
    def test_no_engine_animation_migration_claim(self): self.report["native_physics_or_animation_implementation_changed"] = True; self.reject()
    def test_natural_death_must_route_ragdoll(self): self.report["equipment_hide_cases"][-1]["natural_ragdoll_counters"]["python_calls"] = 0; self.reject()
    def test_prior_equipment_hide_still_required(self): self.report["equipment_hide_cases"][-1]["native_all_spawned_actors_hidden"] = False; self.reject()
    def test_caller_class_root_must_release(self): self.report["ragdoll_caller_roots"]["released"] = 0; self.reject()
    def test_body_nans_rejected(self): self.row()["native_after"]["velocity"][0] = float("nan"); self.reject()
    def test_missing_policy_impulse_vector_rejected(self): self.row()["counters"]["last_call"]["impulse"] = []; self.reject()
    def test_nonfinite_native_input_rejected(self): self.row()["input_velocity"][0] = float("nan"); self.reject()
    def test_original_bot_identity_control_required(self): self.report["original_bots_after"][0]["pawn"] = "new"; self.reject()
    def test_normal_tolerance_uses_squared_length(self): self.assertEqual(impulse([.00001, 0., 0.], 500.), [.00001, 0., 0.])
    def test_private_startup_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterRagdollResult=x"]), "uep_lyra_characters.ragdoll_validation")
