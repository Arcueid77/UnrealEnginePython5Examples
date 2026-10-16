"""Reload report-gate models; cannot establish native animation/GAS proof."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import reload_magazine_contract as gate


def report():
    result = dict(status="passed", error=None, cases=[], original_player_restored=True, original_autoreload_active_restored=True,
        weapon="pistol", native_reload_class=gate.WEAPONS["pistol"][0],
        fixture_native_inventory_api_used=True, observer_scopes_created=20, observer_scopes_closed=20,
        policy_shutdown=dict(active_count=0, scopes_created=8, scopes_closed=8, errors=[]))
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed",
        "task_callbacks_replayed", "reload_done_event_injected", "ammo_properties_written", "ability_activation_called_by_probe"): result[field] = False
    for name in gate.PLAN:
        refused, early = name in gate.REFUSED, name in gate.EARLY
        initial = [12, 12, 24] if name == "full-magazine-refused" else ([1, 12, 0] if name == "no-spare-refused" else [0, 12, 24])
        row = dict(native_type_preserved=True, native_equipment_item_source_matches=True, fixture_ammo_restored=True,
            native_class=gate.WEAPONS["pistol"][0],
            input_injections=1, tasks_after_end=0, native_ability_inactive=True, no_late_callback=True, no_firing_after_end=False,
            initial_ammo=initial, final_ammo=copy.deepcopy(initial) if refused or early else [12, 12, 12], expected_ammo=[12, 12, 12],
            native_active_observed=not refused, native_failure_tags=[gate.REFUSED[name]] if refused else [], failure_messages=int(refused),
            native_tasks_observed=0 if refused else 2, original_montage_playing_observed=not refused, expected_no_firing_observed=not refused,
            native_reload_done_events=int(not refused and not early), profile_teardown_ended_native_ability=name == "active-profile-switch",
            native_pause_observed=name == "paused-world-time", counters=dict(activations=int(not refused), scopes_created=int(not refused),
                scopes_closed=int(not refused), tasks_created=2*int(not refused), authority_reloads=int(not refused and not early),
                can_activate_checks=1, magazine_full_refusals=int(name == "full-magazine-refused"), no_spare_refusals=int(name == "no-spare-refused"),
                native_ends=int(not refused and name != "active-profile-switch"), blocks_added=int(not refused), blocks_removed=int(not refused),
                fallback_activations=int(not refused), fallback_native_ends=int(not refused and name != "active-profile-switch")))
        result["cases"].append(dict(name=name, blueprint=copy.deepcopy(row), python=copy.deepcopy(row)))
    return result


class ReloadMagazineGate(unittest.TestCase):
    def test_complete_matrix(self): self.assertEqual(gate.validate(report())["pairs"], 10)

    def test_reject_replayed_notify_raw_ammo_write_and_probe_activation(self):
        for field in ("reload_done_event_injected", "ammo_properties_written", "ability_activation_called_by_probe"):
            value = report(); value[field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_wrong_failure_reason_or_activated_refusal(self):
        value = report(); value["cases"][2]["python"]["native_failure_tags"] = []
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][3]["python"]["native_active_observed"] = True
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_missing_native_montage_task_and_notify(self):
        for field, bad in (("native_tasks_observed", 0), ("original_montage_playing_observed", False), ("native_reload_done_events", 0)):
            value = report(); value["cases"][0]["python"][field] = bad
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_ammo_creation_cancellation_transfer_and_late_callback(self):
        value = report(); value["cases"][0]["python"]["final_ammo"][2] += 1
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][4]["python"]["final_ammo"] = [12, 12, 12]
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["python"]["no_late_callback"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_tag_scope_and_fixture_leak(self):
        value = report(); value["cases"][0]["python"]["no_firing_after_end"] = True
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["policy_shutdown"]["scopes_closed"] -= 1
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["original_autoreload_active_restored"] = False
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_reject_native_refusal_bypassing_python_can_activate(self):
        value = report(); value["cases"][2]["python"]["counters"]["can_activate_checks"] = 0
        with self.assertRaises(RuntimeError): gate.validate(value)
