"""Fail-closed model reports, never a substitute for native inventory proof."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_abilities import quickslot_contract as contract


def report():
    result = dict(status="passed", error=None, native_gameplay_event_producer=True, original_player_restored=True,
        native_default_owned_python_scope=True,
        original_ability_active_restored=True, cases=[], policy_shutdown=dict(active_count=0, scopes_created=13, scopes_closed=13, errors=[]))
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "hardware_input_tested", "enhanced_input_tested",
                  "python_handler_replayed", "task_callbacks_replayed", "inventory_properties_written", "native_rpc_bypassed"): result[field] = False
    for name, _, selected in contract.PLAN:
        value = dict(inventory=dict(active=selected, equipment_instigator_matches=True), native_type_preserved=True,
            native_tasks_before=3, native_tasks_after_end=0, ended_inactive=True, ended_event_ignored=True,
            profile_switch_reactivated=name == "active-profile-switch", counters=dict(activations=1, scopes_created=1,
                scopes_closed=1, tasks_created=3, selects=int(name.startswith("select")), backward=int(name == "cycle-backward"),
                forward=int(name in ("cycle-forward", "forward-wrap", "native-cancel"))))
        result["cases"].append(dict(name=name, blueprint=copy.deepcopy(value), python=copy.deepcopy(value)))
    return result


class QuickslotContract(unittest.TestCase):
    def test_complete_matrix(self): self.assertEqual(contract.validate(report())["pairs"], 10)

    def test_reject_missing_or_wrong_native_selection(self):
        for side in ("blueprint", "python"):
            value = report(); value["cases"][0][side]["inventory"]["active"] = 2
            with self.assertRaises(RuntimeError): contract.validate(value)
        value = report(); value["cases"].pop()
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_unmatched_equipment_and_unclosed_tasks(self):
        for field, replacement in (("native_tasks_before", 2), ("native_tasks_after_end", 1), ("ended_event_ignored", False),
                                   ("native_type_preserved", False), ("profile_switch_reactivated", True)):
            value = report(); value["cases"][0]["python"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_callback_not_reached_or_repeated(self):
        for field, replacement in (("selects", 0), ("backward", 1), ("forward", 1), ("tasks_created", 6)):
            value = report(); value["cases"][0]["python"]["counters"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_overclaim_replay_and_unrestored_ability(self):
        for field in ("task_callbacks_replayed", "python_handler_replayed", "native_rpc_bypassed", "enhanced_input_tested", "full_acceptance"):
            value = report(); value[field] = True
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)
        value = report(); value["original_ability_active_restored"] = False
        with self.assertRaises(RuntimeError): contract.validate(value)

    def test_reject_shutdown_leaks(self):
        for field, replacement in (("active_count", 1), ("scopes_closed", 12), ("errors", ["callback"] )):
            value = report(); value["policy_shutdown"][field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError): contract.validate(value)
