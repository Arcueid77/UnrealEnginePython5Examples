"""Report rejection/model checks only; separate native run is required."""
import ast
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
source = ROOT/"Overlay/Content/Scripts/uep_lyra_world/inventory_pad_player_contract.py"
spec = importlib.util.spec_from_file_location("_inventory_player_contract", source)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class PlayerInventoryGate(unittest.TestCase):
    def setUp(self):
        self.report = {"schema_version": 1, "status": "passed", "error": None, "net_mode": "Standalone",
            "original_player_restored": True, "actors_created": 8, "actors_destroyed": 8, "cases": [],
            "player_restore": {"inventory_identity_equal": True, "movement": [1, 0], "expected_movement": [1, 0],
                "position_max_error": 0.0, "aim_max_error": 0.0},
            "policy_shutdown": {"errors": [], "authority_grants": 2, "full_slots": 2}}
        for flag in ("network_acceptance", "full_acceptance", "packaged_runtime", "overlap_handler_called_by_probe",
                     "ammo_properties_written", "inventory_properties_written", "manual_lifecycle_event"):
            self.report[flag] = False
        for name in contract.CASES:
            value = {"item_delta": 1, "native_equipment_instigator_matches": True, "equipment_class": "/NativePistol",
                "magazine_before": 12, "magazine_after": 11} if "pickup-fire" in name else {
                "item_delta": 0, "inventory_unchanged": True}
            self.report["cases"].append({"name": name, "passed": True, "same_class": True,
                "python": value, "blueprint": dict(value), "native_input_frames": [3, 4], "native_rollbacks": [True, True]})

    def test_exact_bounded_lane_passes(self):
        self.assertTrue(contract.validate(self.report)["native_player_inventory_equipment_fire"])
        self.assertFalse(contract.validate(self.report)["network_acceptance"])

    def test_no_inventory_equipment_or_fire_shortcut(self):
        for key, value in (("item_delta", 2), ("native_equipment_instigator_matches", False), ("magazine_after", 12)):
            report = copy.deepcopy(self.report)
            for side in ("python", "blueprint"):
                report["cases"][0][side][key] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_missing_input_or_rollback_rejected(self):
        for key, value in (("native_input_frames", []), ("native_input_frames", [0, 0]), ("native_rollbacks", [True, False])):
            report = copy.deepcopy(self.report)
            report["cases"][0][key] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_player_transform_or_actor_leak_rejected(self):
        self.report["player_restore"]["position_max_error"] = float("nan")
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)
        self.report["player_restore"]["position_max_error"] = 0.0
        self.report["actors_destroyed"] = 7
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_no_network_or_property_write_claim(self):
        for flag in ("network_acceptance", "ammo_properties_written", "inventory_properties_written"):
            report = copy.deepcopy(self.report)
            report[flag] = True
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_native_player_fixture_uses_collision_services_and_real_input(self):
        source = (ROOT/"Overlay/Content/Scripts/uep_lyra_world/inventory_pad_player_validation.py").read_text(encoding="utf-8")
        for token in ('.set_actor_location(', 'inject_enhanced_input_for_action(', '"GetInstigator"',
                      '"RemoveItemFromSlot"', '"RemoveItemInstance"', '"GetActiveSlotItem"'):
            self.assertIn(token, source)
        for token in ('"ReceiveTick"', '"ReceiveBeginPlay"', '"ReceiveEndPlay"', '"RemoveStatTagStack"', '"SetStatTagStack"'):
            self.assertNotIn(token, source)
        tree = ast.parse(source)
        finalize = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "finalize")
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in
            ("call_function", "actor_destroy", "set_actor_location", "inject_enhanced_input_for_action") for node in ast.walk(finalize)))
