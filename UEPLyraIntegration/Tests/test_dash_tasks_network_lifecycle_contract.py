"""Two-world lifecycle counterexamples, synthetic report shapes only."""
import copy
from pathlib import Path
import unittest
from test_dash_tasks_contract import reports as basic_reports
from uep_lyra_abilities.dash_tasks_network_lifecycle_contract import validate


def reports():
    values = basic_reports()
    for value in values.values(): value["network_lifecycle_interventions"] = True
    for authority in values["server"]["cases"]:
        peer = authority["target"]; row = values[peer]["cases"][authority["index"]]; switched = row["index"]%2 == 1; python = row["profile"] == "Python"
        action = dict(authority_ready_observed=True, root_before=True, montage_before=True, active_before=True, active_after=False,
            quiet_unchanged=True, elapsed=.1, native_entry="ue.set_mixin_profile" if switched else "GameplayAbility.K2_CancelAbility")
        if switched: action["new_profile"] = "BlueprintFallback" if python else "Python"
        row["network_lifecycle"] = action; authority["authority_ready_sent"] = True
        for value, owner in ((row, True), (authority, False)):
            value["task_business"]["stats"].update(root_finished=0, native_delays_started=0, delay_completed=0, fallback_delay_completed=0,
                native_ends=int(python and not (owner and switched)), fallback_native_ends=int(not python and not (owner and switched)),
                montage_interrupted=int(python and not switched), montage_cancelled=0)
        authority["client"]["row"] = copy.deepcopy(row)
    return values


class NetworkTaskLifecycleModels(unittest.TestCase):
    def setUp(self): self.values = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError)): validate(self.values)
    def test_complete_synthetic_shape_is_not_native_execution(self): self.assertEqual(validate(self.values)["actual_native_two_owner_interventions"], 8)
    def test_authority_must_have_observed_rpc_and_tasks(self): self.values["server"]["cases"][0]["authority_ready_sent"] = False; self.reject()
    def test_client_must_receive_authority_barrier(self): self.values["A"]["cases"][0]["network_lifecycle"]["authority_ready_observed"] = False; self.reject()
    def test_intervention_must_be_before_native_root_end(self): self.values["A"]["cases"][0]["network_lifecycle"]["elapsed"] = .3; self.reject()
    def test_profile_must_really_change(self): self.values["A"]["cases"][3]["network_lifecycle"]["new_profile"] = "Python"; self.reject()
    def test_real_native_ability_must_end(self): self.values["A"]["cases"][0]["network_lifecycle"]["active_after"] = True; self.reject()
    def test_no_late_native_delay_callback(self): self.values["server"]["cases"][2]["task_business"]["stats"]["delay_completed"] = 1; self.reject()
    def test_no_scope_left_after_profile_switch(self): self.values["A"]["cases"][3]["task_business"]["actual_task_scope_closed"] = False; self.reject()
    def test_owner_cancel_must_have_one_real_montage_event(self): self.values["A"]["cases"][2]["task_business"]["stats"]["montage_interrupted"] = 0; self.reject()
    def test_original_server_native_end_required(self): self.values["server"]["cases"][0]["task_business"]["stats"]["fallback_native_ends"] = 0; self.reject()
    def test_replicated_server_cancellation_has_its_own_montage_event(self): self.values["server"]["cases"][2]["task_business"]["stats"]["montage_interrupted"] = 0; self.reject()
    def test_source_observer_restores_original_cue(self): self.values["B0"]["producer_shutdown"]["cue_function_restored"] = False; self.reject()
    def test_commandlet_is_disarmed(self):
        from uep_lyra_hud.startup import validation_module
        flag = "-UEPDashTasksNetworkLifecycleResult=x"
        self.assertEqual(validation_module([flag]), "uep_lyra_abilities.dash_tasks_network_lifecycle_validation")
        self.assertIsNone(validation_module(["-run=Py", flag]))
    def test_native_rpc_and_callback_not_replayed_by_fixture(self):
        source = (Path(__file__).parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/dash_tasks_network_lifecycle_validation.py").read_text(encoding="utf-8")
        for name in ("SendInfo", "K2_ActivateAbility", "UEPDashAfterNativeDelay"):
            self.assertNotIn('call_function("'+name+'"', source)
