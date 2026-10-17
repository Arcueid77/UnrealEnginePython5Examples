"""Synthetic report mutations test the gate, not native gameplay acceptance."""
import copy
import math
from pathlib import Path
import unittest
from uep_lyra_abilities.dash_local_direction_contract import standalone, STANDALONE_TRIALS


def report():
    value = dict(status="passed", error=None, native_net_mode="Standalone", player="player", ai="bot", ai_controller="AIController",
        actual_ability_class="/ShooterCore/Game/Dash/GA_Hero_Dash.GA_Hero_Dash_C", actual_granted_primary_instances=True,
        request_entry="ASC.TryActivateAbilityByClass", movement_intent_entry="Pawn.AddMovementInput",
        fixture_control_rotation_entry="Controller.SetControlRotation", fixture_pose_entry="Actor.K2_TeleportTo",
        restoration=[dict(profile=True, specs=True, configuration=True, pose_reset=True, control_rotation=True) for _ in range(2)], cases=[])
    for key in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "enhanced_input_tested",
            "whole_dash_activation_migrated", "dash_task_business_migrated", "movement_parity_certified", "activation_event_replayed",
            "rpc_receiver_replayed", "ability_granted_by_fixture", "ability_direction_montage_written_by_fixture", "health_written_by_fixture",
            "raw_velocity_written_by_fixture", "gameplay_state_delivered_by_files"):
        value[key] = False
    for index, (name, profile) in enumerate(STANDALONE_TRIALS):
        python, ai = profile == "Python", name == "ai-navigation"
        raw = [0., -1., 0.] if name == "left" else [1., 0., 0.] if name in ("forward", "camera-pitch") else [0., 0., 0.]
        last = [0., 0., 0.] if ai else raw[:]
        movement = [0., 0., 0.] if ai else [math.cos(math.radians(20.)), 0., 1.2*math.sin(math.radians(20.))] if name == "camera-pitch" else [1., 0., 0.]
        direction = last[:] if name == "left" else movement[:]; montage = "left-montage" if name == "left" else "forward-montage"
        chosen = dict(direction=direction, montage=montage); zero = ai
        inputs = dict(ai=ai, facing=[1., 0., 0.], last_input=last, movement=movement, raw_last_input=raw, point=[0., 0., 0.],
            projected=[0., 0., 0.] if ai else None, projection_succeeded=True if ai else None,
            control_rotation=[0., 20. if name == "camera-pitch" else 0., 0.])
        counts = dict(python_calls=int(python), fallback_calls=int(not python))
        data = dict(ai=ai, facing=inputs["facing"][:], last_input=last[:], movement=movement[:], projected=copy.deepcopy(inputs["projected"]),
            projection_succeeded=inputs["projection_succeeded"], bias=name != "left", **copy.deepcopy(chosen)) if python else None
        row = dict(index=index, name=name, profile=profile, actor="bot" if ai else "player", controller="AIController" if ai else "PlayerController",
            native_role=3, native_pose_reset=True, control_pitch_fixture=20. if name == "camera-pitch" else 0., input=inputs, chosen=chosen,
            zero_direction=zero, immediate_active=not zero, native_active_observed=not zero, native_root_motion_task_observed=not zero,
            native_montage_task_observed=not zero, cooldown_repeat_rejected=None if zero else True,
            max_motion_distance=0. if zero else 100., max_native_speed=0. if zero else 1850., native_request_accepted=True,
            local_direction=dict(counters=counts.copy(), before=dict(direction=[1., 1., 0.], montage="old"), stored=copy.deepcopy(chosen), last=data),
            selector_counters=counts.copy(), rpc_counters=dict(python_calls=0, fallback_calls=0),
            native_ability_ended=True, native_tasks_after=0, quiet_ticks=20, specs_unchanged=True, native_configuration_unchanged=True, health_unchanged=True)
        value["cases"].append(row)
    return value


class StandaloneDirectionGateModels(unittest.TestCase):
    def setUp(self): self.value = report()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError, TypeError)): standalone(self.value)
    def test_complete_synthetic_shape_is_not_native_proof(self): self.assertEqual(standalone(self.value)["native_standalone_trials"], 10)
    def test_missing_actual_ai_is_rejected(self): self.value["cases"].pop(); self.reject()
    def test_ai_cannot_be_player(self): self.value["ai"] = self.value["player"]; self.reject()
    def test_projection_must_be_actual_native_result(self): self.value["cases"][-1]["input"]["projection_succeeded"] = None; self.reject()
    def test_native_failed_projection_output_is_not_replaced(self):
        for row in (self.value["cases"][4], self.value["cases"][9]): row["input"]["projection_succeeded"] = False
        self.value["cases"][9]["local_direction"]["last"]["projection_succeeded"] = False
        self.assertTrue(standalone(self.value)["ai_navigation_tested"])
    def test_noinput_cannot_use_held_movement(self): self.value["cases"][0]["input"]["raw_last_input"] = [1., 0., 0.]; self.reject()
    def test_camera_pitch_requires_actual_camera_z(self): self.value["cases"][3]["input"]["movement"][2] = 0.; self.reject()
    def test_camera_pitch_must_select_camera_branch(self): self.value["cases"][8]["local_direction"]["last"]["bias"] = False; self.reject()
    def test_zero_direction_must_cancel_before_tasks(self): self.value["cases"][4]["native_root_motion_task_observed"] = True; self.reject()
    def test_real_nonzero_native_tasks_required(self): self.value["cases"][1]["native_montage_task_observed"] = False; self.reject()
    def test_no_late_task_leak(self): self.value["cases"][1]["native_tasks_after"] = 1; self.reject()
    def test_cleanup_includes_both_native_actors(self): self.value["restoration"][1]["control_rotation"] = False; self.reject()
    def test_quiet_window_not_just_process_exit(self): self.value["cases"][0]["quiet_ticks"] = 0; self.reject()
    def test_no_fake_field_restoration(self): self.value["ability_direction_montage_written_by_fixture"] = True; self.reject()
    def test_activation_event_replay_not_native_entry(self): self.value["activation_event_replayed"] = True; self.reject()
    def test_no_whole_dash_promotion(self): self.value["whole_dash_activation_migrated"] = True; self.reject()
    def test_noinput_counter_not_an_old_pass(self): self.value["cases"][5]["local_direction"]["counters"]["python_calls"] = 0; self.reject()
    def test_remote_rpc_must_not_run_in_standalone(self): self.value["cases"][0]["rpc_counters"]["fallback_calls"] = 1; self.reject()
    def test_native_class_preserved(self): self.value["actual_ability_class"] = "PythonSubclass"; self.reject()
    def test_native_snapshot_nan_rejected(self): self.value["cases"][0]["input"]["point"][0] = float("nan"); self.reject()
    def test_explicit_standalone_dispatch_and_commandlet_disarming(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPDashLocalDirectionResult=x"]), "uep_lyra_abilities.dash_local_direction_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPDashLocalDirectionResult=x"]))
    def test_fixture_uses_native_request_and_no_field_writes(self):
        source = (Path(__file__).parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/dash_local_direction_validation.py").read_text(encoding="utf-8")
        for fragment in ('call_function("TryActivateAbilityByClass"', 'call_function("AddMovementInput"', 'call_function("K2_TeleportTo"', 'call_function("SetControlRotation"'):
            self.assertIn(fragment, source)
        self.assertNotIn(".set_property(", source)
        for name in ("K2_ActivateAbility", "SendInfo", "UEPDashPrepareLocalDirection", "UEPDashStoreRemoteInput"):
            self.assertNotIn('call_function("'+name+'"', source)
