"""New-Pawn evidence must come from natural death/Avatar replacement, not replay."""
import ast
import copy
from pathlib import Path
import types
import unittest
from test_character_inventory_clear_contract import report as clear_report
from test_character_initial_inventory_contract import grant
from uep_lyra_characters import initial_inventory_natural_contract as gate


def report():
    value = clear_report(); value.update(additional_character_helper_under_test="AddInitialInventory",
        add_initial_called_by_fixture=False, whole_character_migrated=False, natural_startup_python_grant=grant())
    for case in value["cases"]:
        for key in ("blueprint", "python"): case[key]["new_pawn_initial_inventory"] = grant(case[key]["new_pawn"])
    for row in value["avatar_endplay_cases"]: row["new_pawn_initial_inventory"] = grant(row["new_pawn"], avatar=True)
    return value


class CharacterLoadoutNaturalModels(unittest.TestCase):
    def test_natural_first_and_ten_replacement_grants(self): self.assertTrue(gate.validate(report())["natural_first_pawn_and_ten_replacement_python_grants"])

    def test_replacement_pawn_must_run_python_once_not_replay_old_actor_evidence(self):
        for fields in (dict(python_calls=0), dict(fallback_calls=1), dict(grant_calls=2)):
            value = report(); value["cases"][0]["python"]["new_pawn_initial_inventory"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)
        value = report(); value["cases"][0]["python"]["new_pawn_initial_inventory"]["last_call"]["actor"] = "old"
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_bare_avatar_retains_original_plus_exact_new_unslotted_native_pistol(self):
        value = report(); value["avatar_endplay_cases"][0]["new_pawn_initial_inventory"]["last_call"]["before"]["items"] = []
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_original_clear_native_empty_window_and_scopes_still_required(self):
        for mutate in (lambda v: v["cases"][0]["python"]["character_inventory"].update(native_empty_before_new_pawn=None),
                lambda v: v["inventory_fixture_shutdown"].update(active=1)):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_probe_grant_or_whole_character_claim_rejected(self):
        for fields in (dict(add_initial_called_by_fixture=True), dict(inventory_properties_written=True), dict(whole_character_migrated=True)):
            value = report(); value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate(value)

    def finish_wrapper(self, finishing):
        messages = []
        class Parent:
            def finish(self, error=None):
                if finishing: self.finished = True; self.report["status"] = "failed" if error else "awaiting_shutdown"
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/initial_inventory_natural_validation.py"
        tree = ast.parse(file.read_text(encoding="utf-8")); cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        namespace = dict(Native=Parent, ue=types.SimpleNamespace(log=messages.append, log_error=messages.append))
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(file), "exec"), namespace)
        value = namespace["Validation"].__new__(namespace["Validation"]); value.finished = False; value.report = dict(status="running")
        value.finish(); return messages

    def test_avatar_transition_is_not_a_failed_final_finish(self): self.assertEqual(self.finish_wrapper(False), [])

    def test_only_real_finish_logs_the_differential_marker(self): self.assertEqual(self.finish_wrapper(True), ["UEP_CHARACTER_LOADOUT_DIFFERENTIAL_PASSED"])
