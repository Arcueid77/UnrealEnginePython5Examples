"""Reject incomplete AutoReload reports; models do not prove native execution."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import autoreload_contract as gate


def report():
    result = dict(status="passed", error=None, cases=[], native_default_python_loop_owned=True,
        original_player_restored=True, original_ability_active_restored=True, fixture_native_inventory_api_used=True,
        observer_scopes_created=12, observer_scopes_closed=12,
        policy_shutdown=dict(active_count=0, scopes_created=30, scopes_closed=30, errors=[]))
    result.update({field: False for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "ammo_properties_written",
        "activation_handler_replayed", "task_callbacks_replayed", "reload_handler_called_by_probe", "poll_interval_or_idle_threshold_written")})
    for name in gate.PLAN:
        reload = name in ("empty-spare", "real-fire-auto-reload")
        row = dict(native_type_preserved=True, native_equipment_item_source_matches=True, tasks_at_start=1, tasks_after_end=0,
            no_callbacks_after_end=True, fixture_ammo_restored=True, ammo_check=name == "empty-spare", reload_event_deliveries=int(reload),
            native_reload_active_observed=reload, native_reload_tag_observed=reload, final_magazine=0 if name == "empty-no-spare" else 12,
            magazine_capacity=12, final_spare=12 if reload else (0 if name == "empty-no-spare" else 24), ammo_conserved=True,
            real_fire_rounds=12 if name == "real-fire-auto-reload" else 0, native_input_injections=20 if name == "real-fire-auto-reload" else 0,
            ammo_api_calls_after_firing_began=0, profile_teardown_ended_native_ability=name == "active-profile-switch",
            counters=dict(activations=1, polls=3, scopes_created=4, scopes_closed=4, reload_requests=int(reload)))
        result["cases"].append(dict(name=name, blueprint=copy.deepcopy(row), python=copy.deepcopy(row)))
    return result


class AutoReloadGate(unittest.TestCase):
    def test_complete_matrix(self): self.assertEqual(gate.validate(report())["pairs"], 6)

    def test_reject_faked_empty_magazine_and_missing_input(self):
        for field, value in (("ammo_api_calls_after_firing_began", 1), ("native_input_injections", 0), ("real_fire_rounds", 0)):
            result = report(); result["cases"][3]["python"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(result)

    def test_reject_event_without_real_reload_or_duplicate_requests(self):
        for field, value in (("native_reload_active_observed", False), ("native_reload_tag_observed", False), ("reload_event_deliveries", 2), ("ammo_conserved", False)):
            result = report(); result["cases"][2]["python"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate(result)

    def test_reject_wrong_predicate_and_unowned_equipment(self):
        result = report(); result["cases"][1]["python"]["ammo_check"] = True
        with self.assertRaises(RuntimeError): gate.validate(result)
        result = report(); result["cases"][0]["python"]["native_equipment_item_source_matches"] = False
        with self.assertRaises(RuntimeError): gate.validate(result)

    def test_reject_callbacks_after_end_or_scope_leak(self):
        result = report(); result["cases"][4]["python"]["no_callbacks_after_end"] = False
        with self.assertRaises(RuntimeError): gate.validate(result)
        result = report(); result["observer_scopes_closed"] = 11
        with self.assertRaises(RuntimeError): gate.validate(result)
