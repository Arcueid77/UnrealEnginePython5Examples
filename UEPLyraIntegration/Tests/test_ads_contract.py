"""Reject fabricated ADS input/camera/mapping/UI proof; report models only."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import ads_contract as gate


def report():
    result = dict(status="passed", error=None, cases=[], original_player_restored=True, original_widget_grant_preserved=True,
        source_observer_closed=True, source_scopes_created=12, source_scopes_closed=12,
        policy_shutdown=dict(active_count=0, scopes_created=6, scopes_closed=6, helpers_rooted=12, helpers_unrooted=12, errors=[]))
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed",
        "task_callbacks_replayed", "camera_or_speed_written_by_probe", "mapping_context_written_by_probe", "ui_messages_injected_by_probe"): result[field] = False
    for name in gate.PLAN:
        row = dict(native_type_preserved=True, native_camera_while_held=True, native_speed_while_held=True, native_mapping_priority_11=True,
            actual_reticle_ads_on=True, actual_reticle_ads_off=True, camera_speed_mapping_restored=True, widget_grant_preserved=True,
            no_late_callbacks=True, input_injections=4, wait_tasks_while_held=1, tasks_after_end=0, source_ui_events=[True, False],
            native_pause_observed=True, profile_teardown_ended_ability=True,
            counters=dict(activations=1, tasks_created=1, scopes_created=1, scopes_closed=1, ui_on=1, ui_off=1,
                mappings_added=1, mappings_removed=1, input_releases=1))
        result["cases"].append(dict(name=name, blueprint=copy.deepcopy(row), python=copy.deepcopy(row)))
    return result


class ADSGate(unittest.TestCase):
    def test_complete_matrix(self): self.assertEqual(gate.validate(report())["pairs"], 6)

    def test_reject_missing_native_input_camera_speed_mapping_and_reticle(self):
        for field in ("native_camera_while_held", "native_speed_while_held", "native_mapping_priority_11", "actual_reticle_ads_on", "actual_reticle_ads_off"):
            value = report(); value["cases"][0]["python"][field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_duplicate_ui_messages_and_insufficient_input(self):
        value = report(); value["cases"][0]["python"]["source_ui_events"] = [True, True, False]
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["blueprint"]["input_injections"] = 1
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_probe_writes_and_task_replay(self):
        for field in ("camera_or_speed_written_by_probe", "mapping_context_written_by_probe", "ui_messages_injected_by_probe", "task_callbacks_replayed"):
            value = report(); value[field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_profile_widget_scope_or_helper_leak(self):
        value = report(); value["cases"][3]["python"]["profile_teardown_ended_ability"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["original_widget_grant_preserved"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["policy_shutdown"]["helpers_unrooted"] = 11
        with self.assertRaises(RuntimeError): gate.validate(value)
