"""Report models reject a mere direction/RPC pass without real activation ownership."""
import copy
import unittest
from test_dash_local_direction_standalone_contract import report as local_report
from test_dash_local_direction_contract import reports as local_reports
from uep_lyra_abilities.dash_activation_contract import standalone, network, STANDALONE_TRIALS


def entry(profile, controlled, authority=None, zero=False, crouched=False):
    python = profile == "Python"; last = None
    if python:
        last = dict(local_controlled=controlled, zero_direction=None, committed=None, crouched_before=None,
            uncrouch_called=False, authority=None, rpc_sent=False, native_tasks_started=False, order=["local-control"])
        if controlled:
            last["zero_direction"] = zero; last["order"] += ["prepare-local", "zero-check"]
            if zero: last["order"] += ["cancel"]
            else:
                last.update(committed=True, crouched_before=crouched, uncrouch_called=crouched, authority=authority,
                    rpc_sent=not authority, native_tasks_started=True)
                last["order"] += ["commit"]+(["uncrouch"] if crouched else [])+["authority"]+([] if authority else ["send-info"])+["native-tasks"]
    return dict(counters=dict(python_calls=int(python), fallback_calls=int(not python)), last=last)


def report():
    value = local_report(); old = {(row["name"], row["profile"]): row for row in value["cases"]}; value["cases"] = []
    value.update(actual_activation_event_business_migrated=True, native_commit_failure_tested=False, native_crouch_restored=True, crouch_fixture_entry="Character.Crouch")
    for restoration in value["restoration"]:
        restoration.update(control_expected=[0., 0., 0.], control_before=[0., 0., .0002], control_after=[0., 0., 0.], native_control_reset_forced=True)
    for index, (name, profile) in enumerate(STANDALONE_TRIALS):
        crouched = name == "crouched-forward"; row = copy.deepcopy(old["forward" if crouched else name, profile])
        row.update(index=index, name=name, native_crouched_after=False)
        row["input"]["native_crouched_before"] = crouched
        row["activation_entry"] = entry(profile, True, True, zero=row["zero_direction"], crouched=crouched)
        value["cases"].append(row)
    return value


def reports():
    value = local_reports()
    for authority in value["server"]["cases"]:
        row = value[authority["target"]]["cases"][authority["index"]]
        row["activation_entry"] = entry(row["profile"], True, False)
        authority["activation_entry"] = entry(row["profile"], False)
        authority["client"]["row"] = copy.deepcopy(row)
    return value


class ActivationReportModels(unittest.TestCase):
    def setUp(self): self.value, self.values = report(), reports()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError)): standalone(self.value)
    def reject_network(self):
        with self.assertRaises((RuntimeError, KeyError)): network(self.values)
    def test_complete_shape_is_not_native_execution(self): self.assertEqual(standalone(self.value)["native_standalone_activation_trials"], 12)
    def test_old_direction_report_is_not_activation_acceptance(self): self.value = local_report(); self.reject()
    def test_missing_crouch_cases_rejected(self): self.value["cases"] = self.value["cases"][:-1]; self.reject()
    def test_native_crouch_must_be_observed(self): self.value["cases"][-1]["input"]["native_crouched_before"] = False; self.reject()
    def test_native_uncrouch_must_complete(self): self.value["cases"][-1]["native_crouched_after"] = True; self.reject()
    def test_original_native_crouch_restored(self): self.value["native_crouch_restored"] = False; self.reject()
    def test_control_restoration_is_not_merely_a_pass_flag(self): self.value["restoration"][0]["control_after"][2] = .0002; self.reject()
    def test_entry_dispatch_must_be_actual_python(self): self.value["cases"][-1]["activation_entry"]["counters"]["python_calls"] = 0; self.reject()
    def test_no_implicit_original_fallthrough(self): self.value["cases"][-1]["activation_entry"]["counters"]["fallback_calls"] = 1; self.reject()
    def test_zero_cannot_commit(self):
        row = next(row for row in self.value["cases"] if row["profile"] == "Python" and row["zero_direction"])
        row["activation_entry"]["last"]["committed"] = True; self.reject()
    def test_native_task_entry_is_after_commit(self): self.value["cases"][-1]["activation_entry"]["last"]["order"][-1] = "commit"; self.reject()
    def test_authority_must_not_send_rpc(self): self.value["cases"][-1]["activation_entry"]["last"]["rpc_sent"] = True; self.reject()
    def test_native_commit_failure_not_claimed_from_models(self): self.value["native_commit_failure_tested"] = True; self.reject()
    def test_complete_network_shape_is_not_native_execution(self): self.assertEqual(network(self.values)["native_remote_authority_activation_events"], 8)
    def test_remote_server_does_not_start_local_work(self): self.values["server"]["cases"][2]["activation_entry"]["last"]["native_tasks_started"] = True; self.reject_network()
    def test_remote_actual_event_must_have_dispatched(self): self.values["server"]["cases"][0]["activation_entry"]["counters"]["fallback_calls"] = 0; self.reject_network()
    def test_client_must_send_original_rpc_before_tasks(self):
        self.values["A"]["cases"][2]["activation_entry"]["last"]["rpc_sent"] = False; self.reject_network()
    def test_explicit_runtime_selection_and_commandlet_disarming(self):
        from uep_lyra_hud.startup import validation_module
        for flag, module in (("-UEPDashActivationResult=x", "dash_activation_validation"), ("-UEPDashActivationNetworkResult=x", "dash_activation_network_validation")):
            self.assertEqual(validation_module([flag]), "uep_lyra_abilities."+module)
            self.assertIsNone(validation_module(["-run=Py", flag]))
