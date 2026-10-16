"""Native death-event dispatch, true roles/replicas and foreign event isolation."""
import ast
import copy
from pathlib import Path
import types
import unittest
from test_character_inventory_clear_network_contract import reports as inventory_reports
from test_character_lifecycle_contract import header, add_row
from uep_lyra_characters import lifecycle_contract as gate
from uep_lyra_hud.startup import validation_module


def reports():
    values = inventory_reports()
    for peer, report in values.items():
        header(report)
        for row in report["cases"]:
            add_row(row, row["profile"])
            if peer == "server": row["server_foreign_character_lifecycle"] = dict(before={}, after={})
        for row in report.get("foreign_cases", []): row["foreign_character_lifecycle"] = dict(before={}, after={})
    for row in values["server"]["cases"]:
        row["owner_ack"]["row"] = copy.deepcopy(values[row["target"]]["cases"][row["index"]])
        other = "B0" if row["target"] == "A" else "A"
        row["foreign_ack"]["row"] = copy.deepcopy(next(value for value in values[other]["foreign_cases"] if value["position"] == row["position"]))
    return values


class CharacterLifecycleNetworkModels(unittest.TestCase):
    def test_native_twelve_authority_and_twelve_owner_event_trials(self):
        self.assertEqual(gate.validate_network(reports())["authority_trials"], 12)

    def test_client_native_role_one_or_two_but_never_authority(self):
        for role in (1, 2):
            value = reports(); row = value["A"]["cases"][0]; row["character_inventory"]["last_call"]["native_role"] = role
            value["server"]["cases"][0]["owner_ack"]["row"] = copy.deepcopy(row); gate.validate_network(value)
        value = reports(); value["A"]["cases"][0]["character_inventory"]["last_call"]["authority"] = True
        with self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_each_owner_enters_only_selected_event_and_forwards_once(self):
        for fields in (dict(death_python=0), dict(death_fallback=1), dict(clear_forwards=2)):
            value = reports(); row = next(row for row in value["A"]["cases"] if row["profile"] == "Python")
            row["character_lifecycle"]["counters"].update(fields)
            with self.subTest(fields=fields), self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_foreign_server_and_client_event_counters_must_stay_unchanged(self):
        value = reports(); value["server"]["cases"][0]["server_foreign_character_lifecycle"]["after"] = dict(death_python=1)
        with self.assertRaises(RuntimeError): gate.validate_network(value)
        value = reports(); value["B0"]["foreign_cases"][0]["foreign_character_lifecycle"]["after"] = dict(death_python=1)
        with self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_native_inventory_replication_and_foreign_inventory_gates_are_retained(self):
        value = reports(); value["server"]["cases"][0]["server_foreign_inventory"]["after"]["items"] = []
        with self.assertRaises(RuntimeError): gate.validate_network(value)
        value = reports(); value["A"]["cases"][0]["character_inventory"]["counters"]["items_removed"] = 1
        with self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_native_cleanup_and_real_client_process_exits_required(self):
        for mutate in (lambda r: r["A"]["inventory_fixture_shutdown"].update(active=1),
                lambda r: r["server"].update(server_waited_for_client_process_exit=False)):
            value = reports(); mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError): gate.validate_network(value)

    def test_explicit_lifecycle_network_flag_does_not_start_legacy_network_fixture(self):
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_abilities/auto_respawn_activation_network_validation.py"
        node = ast.parse(file.read_text(encoding="utf-8")).body[-1]
        def unexpected(*args): raise AssertionError("duplicate legacy native network fixture")
        namespace = dict(sys=types.SimpleNamespace(argv=["-UEPCharacterLifecycleNetworkResult=x", "-UEPAutoRespawnActivation"]), Server=unexpected, Client=unexpected, arg=unexpected)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(file), "exec"), namespace)

    def test_explicit_network_selector_is_disabled_for_authoring_commandlet(self):
        self.assertEqual(validation_module(["-UEPCharacterLifecycleNetworkResult=x"]), "uep_lyra_characters.lifecycle_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterLifecycleNetworkResult=x"]))
