"""Two-owner Character helper/replication gate models, not native acceptance."""
import ast
import copy
from pathlib import Path
import types
import unittest
from test_auto_respawn_activation_contract import reports as natural_reports
from test_character_inventory_clear_contract import add_peer, add_row, state
from uep_lyra_characters import inventory_clear_network_contract as gate


def reports():
    result = natural_reports()
    for peer, report in result.items():
        add_peer(report)
        for row in report["cases"]:
            add_row(row, row["profile"], authority=peer == "server")
            if peer == "server": row["server_foreign_inventory"] = dict(before=state(), after=state())
            else: row["character_inventory"]["last_call"]["native_role"] = 1
        for row in report.get("foreign_cases", []): row["foreign_character_inventory"] = dict(before=state(), after=state())
        report["inventory_fixture_shutdown"] = dict(created=len(report["cases"]), closed=len(report["cases"]), active=0)
    for row in result["server"]["cases"]:
        row["owner_ack"]["row"] = copy.deepcopy(result[row["target"]]["cases"][row["index"]])
        other = "B0" if row["target"] == "A" else "A"
        row["foreign_ack"]["row"] = copy.deepcopy(next(value for value in result[other]["foreign_cases"] if value["position"] == row["position"]))
    return result


class CharacterInventoryNetworkModels(unittest.TestCase):
    def test_bounded_two_owner_shape(self): self.assertEqual(gate.validate(reports())["authority_trials"], 12)

    def test_callback_role_can_be_simulated_or_autonomous_but_never_authority(self):
        for role in (1, 2):
            value = reports(); row = value["A"]["cases"][0]; row["character_inventory"]["last_call"]["native_role"] = role
            value["server"]["cases"][0]["owner_ack"]["row"] = copy.deepcopy(row)
            self.assertTrue(gate.validate(value)["character_native_bp_helper_two_owner_verified"])
        for role in (0, 3):
            value = reports(); value["A"]["cases"][0]["character_inventory"]["last_call"]["native_role"] = role
            with self.subTest(role=role), self.assertRaises(RuntimeError): gate.validate(value)

    def test_native_client_helper_cannot_remove_items_or_claim_authority(self):
        for mutate in (lambda r: r["counters"].update(items_removed=1), lambda r: r["counters"].update(slots_removed=1),
            lambda r: r["last_call"].update(authority=True), lambda r: r["last_call"].update(after=state(None))):
            value = reports(); row = value["A"]["cases"][0]; mutate(row["character_inventory"])
            value["server"]["cases"][0]["owner_ack"]["row"] = copy.deepcopy(row)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_foreign_server_and_client_inventory_must_remain_identical(self):
        value = reports(); value["server"]["cases"][0]["server_foreign_inventory"]["after"] = state(None)
        with self.assertRaises(RuntimeError): gate.validate(value)
        value = reports(); value["B0"]["foreign_cases"][0]["foreign_character_inventory"]["after"] = state(None)
        value["server"]["cases"][0]["foreign_ack"]["row"] = copy.deepcopy(value["B0"]["foreign_cases"][0])
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_one_actor_type_and_selected_profile_are_required_on_real_owner(self):
        value = reports(); row = value["A"]["cases"][0]; row["character_inventory"]["new_character_class"] = "replacement"
        value["server"]["cases"][0]["owner_ack"]["row"] = copy.deepcopy(row)
        with self.assertRaises(RuntimeError): gate.validate(value)

    def test_network_observer_close_and_no_manual_helper_claim_required(self):
        for mutate in (lambda r: r["inventory_fixture_shutdown"].update(active=1), lambda r: r.update(character_clear_called_by_fixture=True)):
            value = reports(); mutate(value["A"])
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate(value)

    def test_parent_network_footer_is_disarmed_for_character_lane(self):
        path = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_activation_network_validation.py"
        footer = ast.parse(path.read_text(encoding="utf-8")).body[-1]
        def unexpected(*args): raise AssertionError("duplicate parent network fixture")
        scope = dict(sys=types.SimpleNamespace(argv=["-UEPAutoRespawnActivation", "-UEPCharacterInventory", "-UEPAutoRespawnHelpersNetworkResult=x"]),
            Server=unexpected, Client=unexpected, arg=unexpected)
        exec(compile(ast.Module(body=[footer], type_ignores=[]), str(path), "exec"), scope)
