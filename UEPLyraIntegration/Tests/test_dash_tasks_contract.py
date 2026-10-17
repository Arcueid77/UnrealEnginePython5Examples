"""Independent report mutations; synthetic shapes are not native acceptance."""
import copy
import unittest
from test_dash_activation_contract import report as activation_report, reports as activation_reports
from uep_lyra_abilities.dash_tasks_contract import standalone, network


def evidence(value, target, zero=False, authority=True, remote=False, dedicated=False):
    python = value["profile"] == "Python"; on = int(not zero)
    stats = dict(task_starts=int(python)*on, fallback_task_starts=int(not python)*on, montage_tasks=int(python)*on, root_tasks=int(python)*on,
        root_finished=int(python)*on, native_delays_started=int(python)*on, delay_completed=int(python)*on, fallback_delay_completed=int(not python)*on,
        cues=int(python and authority)*on, ui_messages=int(python)*on, montage_interrupted=0, montage_cancelled=0,
        native_ends=int(python), fallback_native_ends=int(not python), remote_commits=int(python and remote), scopes_created=int(python)*on, scopes_closed=int(python)*on)
    payload = value.get("chosen", value.get("stored"))
    return dict(target=target, stats=stats, observer_errors=[], actual_task_scope_closed=True, native_dedicated_server=dedicated,
        ui=[] if zero else [dict(instigator=target, duration=1.5, native_cooldown=1.5, game_time=1.)],
        cues=[] if zero or dedicated else [dict(target=target, normalized=.25, raw=1850., normal=copy.deepcopy(payload["direction"]),
            effect_level=1, ability_level=1, replicate_location=False, game_time=1.)])


def flags(value):
    value.update(dash_task_business_migrated=True, task_callbacks_replayed=False, cue_or_ui_producer_replayed=False,
        original_kismet_delay_retained=True, task_shutdown=dict(active_count=0, scopes_created=4, scopes_closed=4, errors=[]),
        producer_shutdown=dict(scope_closed=True, cue_function_restored=True, errors=[]))


def report():
    value = activation_report(); flags(value)
    for row in value["cases"]: row["task_business"] = evidence(row, row["actor"], zero=row["zero_direction"])
    return value


def reports():
    values = activation_reports()
    for value in values.values(): flags(value)
    for authority in values["server"]["cases"]:
        peer = authority["target"]; row = values[peer]["cases"][authority["index"]]
        row["task_business"] = evidence(row, peer+"-native-pawn", authority=False)
        authority["task_business"] = evidence(authority, peer+"-authority-pawn", remote=True, dedicated=True)
        authority["client"]["row"] = copy.deepcopy(row)
    return values


class TaskProducerContractModels(unittest.TestCase):
    def setUp(self): self.value, self.values = report(), reports()
    def reject(self):
        with self.assertRaises((RuntimeError, KeyError)): standalone(self.value)
    def reject_network(self):
        with self.assertRaises((RuntimeError, KeyError)): network(self.values)
    def test_complete_synthetic_standalone_shape_not_native_execution(self): self.assertEqual(standalone(self.value)["actual_native_task_trials"], 12)
    def test_complete_synthetic_network_shape_not_native_execution(self): self.assertTrue(network(self.values)["native_task_cue_ui_business_tested"])
    def test_stats_alone_are_not_a_cue(self): self.value["cases"][1]["task_business"]["cues"] = []; self.reject()
    def test_stats_alone_are_not_typed_ui(self): self.value["cases"][1]["task_business"]["ui"] = []; self.reject()
    def test_wrong_native_ui_owner_rejected(self): self.value["cases"][1]["task_business"]["ui"][0]["instigator"] = "foreign"; self.reject()
    def test_ui_duration_matches_actual_same_frame_native_cooldown(self): self.value["cases"][1]["task_business"]["ui"][0]["native_cooldown"] = 0.; self.reject()
    def test_native_cue_strength_not_just_delivery(self): self.value["cases"][1]["task_business"]["cues"][0]["raw"] = 0.; self.reject()
    def test_native_cue_direction_not_just_delivery(self): self.value["cases"][1]["task_business"]["cues"][0]["normal"] = [0., 0., 0.]; self.reject()
    def test_zero_direction_must_not_emit_ui(self):
        row = next(row for row in self.value["cases"] if row["zero_direction"]); row["task_business"]["ui"] = [dict(instigator=row["actor"], duration=1.5, native_cooldown=1.5)]; self.reject()
    def test_no_scope_leak(self): self.value["task_shutdown"]["active_count"] = 1; self.reject()
    def test_no_observer_function_leak(self): self.value["producer_shutdown"]["cue_function_restored"] = False; self.reject()
    def test_native_callback_must_not_be_replayed(self): self.value["task_callbacks_replayed"] = True; self.reject()
    def test_no_fixture_cue_or_duration_producer(self): self.value["cue_or_ui_producer_replayed"] = True; self.reject()
    def test_native_root_finish_and_delay_must_actually_dispatch(self): self.value["cases"][-1]["task_business"]["stats"]["native_delays_started"] = 0; self.reject()
    def test_no_double_remote_commit_body(self): self.values["server"]["cases"][2]["task_business"]["stats"]["remote_commits"] = 2; self.reject_network()
    def test_native_replication_can_cancel_server_latent_action_after_owner_completion(self):
        self.values["server"]["cases"][2]["task_business"]["stats"]["delay_completed"] = 0
        self.assertTrue(network(self.values)["task_scopes_closed"])
    def test_native_replication_can_cancel_owner_latent_action_after_server_completion(self):
        owner = self.values["A"]["cases"][2]; owner["task_business"]["stats"]["delay_completed"] = 0
        self.values["server"]["cases"][2]["client"]["row"] = copy.deepcopy(owner)
        self.assertTrue(network(self.values)["task_scopes_closed"])
    def test_both_worlds_without_natural_completion_are_rejected(self):
        owner = self.values["A"]["cases"][2]; owner["task_business"]["stats"]["delay_completed"] = 0
        self.values["server"]["cases"][2]["client"]["row"] = copy.deepcopy(owner)
        self.values["server"]["cases"][2]["task_business"]["stats"]["delay_completed"] = 0; self.reject_network()
    def test_duplicated_delay_callback_is_not_replication(self): self.values["server"]["cases"][2]["task_business"]["stats"]["delay_completed"] = 2; self.reject_network()
    def test_complete_cue_parameter_control_includes_extra_native_fields(self):
        self.value["cases"][-1]["task_business"]["cues"][0]["context"] = dict(instigator="unexpected")
        self.reject()
    def test_client_must_receive_real_replicated_cue(self): self.values["A"]["cases"][2]["task_business"]["cues"] = []; self.reject_network()
    def test_dedicated_server_does_not_substitute_for_client_cue(self): self.values["A"]["cases"][2]["task_business"]["native_dedicated_server"] = True; self.reject_network()
    def test_original_delay_primitive_is_required(self): self.value["original_kismet_delay_retained"] = False; self.reject()
    def test_explicit_entry_disarms_in_commandlet(self):
        from uep_lyra_hud.startup import validation_module
        for flag, name in (("-UEPDashTasksResult=x", "dash_tasks_validation"), ("-UEPDashTasksNetworkResult=x", "dash_tasks_network_validation")):
            self.assertEqual(validation_module([flag]), "uep_lyra_abilities."+name)
            self.assertIsNone(validation_module(["-run=Py", flag]))
