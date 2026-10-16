"""Native Reset Character ingress evidence models; no lifecycle replay proof."""
import ast
import copy
from pathlib import Path
import types
import unittest
from test_auto_respawn_reset_contract import report as reset_report
from test_character_inventory_clear_contract import add_peer, add_row
from uep_lyra_characters import inventory_clear_contract as gate


def report():
    value = reset_report(); add_peer(value)
    for row in value["cases"]: add_row(row, row["profile"])
    value["inventory_fixture_shutdown"] = dict(created=8, closed=8, active=0)
    return value


class CharacterInventoryResetModels(unittest.TestCase):
    def test_eight_real_reset_requests_require_original_character_ingress(self):
        self.assertTrue(gate.validate_reset(report())["character_clear_native_reset_bp_ingress"])

    def test_native_producer_does_not_substitute_for_selected_character_helper(self):
        value = report(); value["cases"][1]["character_inventory"]["counters"]["python_calls"] = 0
        with self.assertRaises(RuntimeError): gate.validate_reset(value)

    def test_independent_empty_window_and_native_item_definition_restore_required(self):
        for mutate in (lambda r: r.update(native_empty_before_new_pawn=None), lambda r: r["after"].update(items=[])):
            value = report(); mutate(value["cases"][1]["character_inventory"])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate_reset(value)

    def test_manual_helper_invocation_cleanup_or_whole_character_claim_cannot_pass(self):
        for mutate in (lambda r: r.update(character_clear_called_by_fixture=True), lambda r: r.update(other_character_business_migrated=True),
            lambda r: r["cases"][0]["character_inventory"]["native_orphan_cleanup"].update(required=True)):
            value = report(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate_reset(value)

    def test_parent_reset_footer_does_not_start_a_second_fixture(self):
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_reset_validation.py"
        footer = ast.parse(path.read_text(encoding="utf-8")).body[-1]
        def unexpected(*args): raise AssertionError("duplicate parent Reset fixture")
        scope = dict(result="x", sys=types.SimpleNamespace(argv=["-UEPAutoRespawnResetResult=x", "-UEPCharacterInventory"]), ResetTrials=unexpected)
        exec(compile(ast.Module(body=[footer], type_ignores=[]), str(path), "exec"), scope)
