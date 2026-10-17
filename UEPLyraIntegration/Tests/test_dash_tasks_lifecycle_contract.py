"""Game-clock/native-intervention report mutations, not native test evidence."""
import copy
from pathlib import Path
import unittest
from test_dash_tasks_contract import report as basic_report
from uep_lyra_abilities.dash_tasks_lifecycle_contract import TRIALS, validate


def report():
    value = basic_report(); old = {row["profile"]: row for row in value["cases"] if row["name"] == "forward"}
    value.update(lifecycle_interventions_declared=True, frame_times_observed=True, cases=[])
    for index, (name, profile) in enumerate(TRIALS):
        row = copy.deepcopy(old[profile]); row.update(index=index, name=name)
        python = profile == "Python"; paused = name.startswith("pause-"); switched = name == "profile-switch-active"
        action_time = .25 if name == "pause-delay" else .1
        samples = []
        for frame in range(31):
            now = round(frame*.05, 8); active = now < (.55 if paused else .1); root = now < .25 and active
            samples.append(dict(time=now, active=active, root=root, montage=active, tasks=2 if root else int(active)))
        entry = "GameplayStatics.SetGamePaused" if paused else {"montage-interrupt": "Character.StopAnimMontage", "native-cancel": "GameplayAbility.K2_CancelAbility", "profile-switch-active": "ue.set_mixin_profile"}[name]
        action = dict(time=action_time, active_before=True, root_before=name != "pause-delay", native_entry=entry, active_after=False)
        if switched: action["new_profile"] = "Python" if profile == "BlueprintFallback" else "BlueprintFallback"
        row["lifecycle"] = dict(samples=samples, activation_at_start=copy.deepcopy(row["activation_entry"]), intervention=action,
            quiet_unchanged=True, pause=dict(time=action_time, tasks=dict(count=2 if name == "pause-root" else 1, root=name == "pause-root", montage=True),
                ticks=5, unpaused=True, wall_seconds=.35) if paused else None)
        row["task_business"]["stats"].update(root_finished=int(python and paused), native_delays_started=int(python and paused),
            delay_completed=int(python and paused), fallback_delay_completed=int(not python and paused),
            native_ends=int(python and not switched), fallback_native_ends=int(not python and not switched),
            montage_interrupted=int(python and name == "montage-interrupt"), montage_cancelled=int(python and name == "native-cancel"))
        value["cases"].append(row)
    return value


class TaskLifecycleContractModels(unittest.TestCase):
    def setUp(self): self.value = report()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError)): validate(self.value)
    def test_complete_synthetic_matrix_not_native_execution(self): self.assertEqual(validate(self.value)["actual_native_lifecycle_trials"], 10)
    def test_missing_native_intervention_rejected(self): self.value["cases"][0]["lifecycle"]["intervention"] = None; self.reject()
    def test_pause_requires_actual_ticks_and_unpause(self): self.value["cases"][0]["lifecycle"]["pause"]["ticks"] = 0; self.reject()
    def test_pause_root_and_delay_are_distinct(self): self.value["cases"][1]["lifecycle"]["pause"]["tasks"]["root"] = True; self.reject()
    def test_native_frame_bound_not_a_widened_constant(self): self.value["cases"][0]["lifecycle"]["samples"][-1]["time"] = 3.; self.reject()
    def test_nonfinite_native_time_rejected(self): self.value["cases"][0]["lifecycle"]["samples"][1]["time"] = float("nan"); self.reject()
    def test_real_native_end_transition_required(self):
        for sample in self.value["cases"][0]["lifecycle"]["samples"]: sample["active"] = True
        self.reject()
    def test_real_root_finish_time_checked(self):
        for sample in self.value["cases"][0]["lifecycle"]["samples"]: sample["root"] = sample["time"] < .45
        self.reject()
    def test_actual_profile_must_change(self): self.value["cases"][4]["lifecycle"]["intervention"]["new_profile"] = "BlueprintFallback"; self.reject()
    def test_interrupt_does_not_run_late_root_callback(self): self.value["cases"][7]["task_business"]["stats"]["root_finished"] = 1; self.reject()
    def test_no_native_task_left_after_cancel(self): self.value["cases"][3]["native_tasks_after"] = 1; self.reject()
    def test_no_native_cue_replay(self): self.value["cue_or_ui_producer_replayed"] = True; self.reject()
    def test_pause_case_requires_native_source_entry(self): self.value["cases"][0]["lifecycle"]["intervention"]["native_entry"] = "fake-tick"; self.reject()
    def test_no_late_producer_after_end(self): self.value["cases"][0]["lifecycle"]["quiet_unchanged"] = False; self.reject()
    def test_explicit_commandlet_disarming(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPDashTasksLifecycleResult=x"]), "uep_lyra_abilities.dash_tasks_lifecycle_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPDashTasksLifecycleResult=x"]))
    def test_native_callbacks_not_called_by_fixture(self):
        source = (Path(__file__).parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/dash_tasks_lifecycle_validation.py").read_text(encoding="utf-8")
        for name in ("RootFinished", "AfterNativeDelay", "UEPDashAfterNativeDelay", "K2_ActivateAbility"):
            self.assertNotIn('call_function("'+name+'"', source)
