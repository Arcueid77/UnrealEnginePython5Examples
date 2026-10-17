"""Native activation report counterexamples, not host gameplay proof."""
import unittest
from uep_lyra_abilities.melee_activation_contract import TRIALS, validate


def report():
    value = dict(status="passed", error=None, actual_granted_primary_instance=True, native_role=3,
        request_entry="ASC.TryActivateAbilityByClass", actual_ability_class="/ShooterCore/Game/Melee/GA_Melee.GA_Melee_C",
        full_acceptance=False, network_acceptance=False, packaged_runtime=False, physical_input_tested=False,
        activation_event_replayed=False, task_callbacks_replayed=False, ability_granted_by_fixture=False,
        health_or_raw_velocity_written=False, trace_damage_business_migrated=False, profile_restored=True,
        specs_unchanged=True, config_unchanged=True, native_pose_restored=True, native_control_restoration=dict(control_rotation=True),
        shutdown=dict(active_count=0, scopes_created=4, scopes_closed=4, errors=[]), cases=[])
    for index, (name, profile) in enumerate(TRIALS):
        python = profile == "Python"; switched = name == "profile-switch"
        counts = dict(activations=int(python), fallback_activations=int(not python), commits=int(python), cast_failed=0,
            montage_tasks=int(python), authority_trace_entries=int(python), scopes_created=int(python), scopes_closed=int(python),
            native_ends=int(python and not switched), fallback_native_ends=int(not python and not switched),
            completed=0, blend_out=int(python and name == "natural"), interrupted=int(python and name in ("interrupt", "cancel")), cancelled=0)
        action = None if name == "natural" else dict(active_before=True, active_after=False, time=.1)
        if switched: action["new_profile"] = "Python" if profile == "BlueprintFallback" else "BlueprintFallback"
        value["cases"].append(dict(index=index, name=name, profile=profile, native_pose_reset=True,
            equipment=dict(weapon="native-weapon", montage="native-melee-montage"), native_initial_montage="native-melee-montage",
            native_request_accepted=True, native_repeat_rejected=True, native_active_observed=True, native_montage_task_observed=True,
            native_ended=True, actual_scope_closed=True, all_pawn_health_unchanged=True, specs_unchanged=True, config_unchanged=True,
            native_tasks_after=0, quiet_ticks=20, native_root_task_observed=False, stats=counts, intervention=action))
    return value


class MeleeActivationReportModels(unittest.TestCase):
    def setUp(self): self.value = report()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError)): validate(self.value)
    def test_complete_synthetic_shape_not_native_execution(self): self.assertEqual(validate(self.value)["actual_native_melee_activation_trials"], 8)
    def test_native_asc_request_required(self): self.value["cases"][0]["native_request_accepted"] = False; self.reject()
    def test_cannot_claim_trace_damage_migration(self): self.value["trace_damage_business_migrated"] = True; self.reject()
    def test_no_health_reset_to_hide_hit(self): self.value["cases"][0]["all_pawn_health_unchanged"] = False; self.reject()
    def test_actual_first_equipment_montage_required(self): self.value["cases"][0]["native_initial_montage"] = "other"; self.reject()
    def test_no_montage_event_replay(self): self.value["task_callbacks_replayed"] = True; self.reject()
    def test_native_task_must_have_existed(self): self.value["cases"][0]["native_montage_task_observed"] = False; self.reject()
    def test_no_leaked_montage_scope(self): self.value["shutdown"]["active_count"] = 1; self.reject()
    def test_active_profile_must_change(self): self.value["cases"][3]["intervention"]["new_profile"] = "BlueprintFallback"; self.reject()
    def test_no_double_native_completion(self): self.value["cases"][4]["stats"]["completed"] = 1; self.reject()
    def test_no_added_native_root_task_in_control(self): self.value["cases"][0]["native_root_task_observed"] = True; self.reject()
    def test_explicit_standalone_commandlet_disarming(self):
        from uep_lyra_hud.startup import validation_module
        flag = "-UEPMeleeActivationResult=x"
        self.assertEqual(validation_module([flag]), "uep_lyra_abilities.melee_activation_validation")
        self.assertIsNone(validation_module(["-run=Py", flag]))
