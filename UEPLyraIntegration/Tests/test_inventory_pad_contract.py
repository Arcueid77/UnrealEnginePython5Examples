"""Synthetic contract rejection checks, not twelve Engine passes."""
import copy
import importlib.util
from pathlib import Path
import unittest

root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_world"
spec = importlib.util.spec_from_file_location("_inventory_contract", root/"inventory_pad_contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class InventoryGate(unittest.TestCase):
    def setUp(self):
        self.report = {"schema_version": 1, "status": "passed", "error": None, "actors_created": 60,
            "native_test_actors_destroyed": 60, "fixture_native_inventory_setup": True,
            "test_owned_controller_pawn_services": True, "numeric_tolerance": .001,
            "cases": [{"name": name, "passed": True, "same_class": True, "python": {"yaw_change": 12.0},
                "blueprint": {"yaw_change": 12.0}} for name in contract.CASES],
            "policy_shutdown": {"errors": [], "constructions": 12, "mesh_constructions": 6, "mesh_ticks": 100,
                "overlaps": 8, "authority_grants": 4, "full_slots": 2, "no_controller": 2, "destroy_requests": 2}}
        for flag in ("full_acceptance", "network_acceptance", "production_placement_tested", "production_equipment_gas_tested",
                     "remote_audio_tested", "packaged_runtime", "manual_lifecycle_event", "overlap_handler_called_by_probe",
                     "inventory_properties_written_by_probe", "native_exception_gate_tested"):
            self.report[flag] = False

    def reject(self):
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_only_bounded_domain_is_accepted(self):
        self.assertEqual(contract.validate(self.report)["case_count"], 12)
        self.assertFalse(contract.validate(self.report)["full_acceptance"])

    def test_wrong_order_class_or_difference_is_rejected(self):
        for mutation in (lambda r: r["cases"].reverse(), lambda r: r["cases"][0].update(same_class=False),
                         lambda r: r["cases"][0]["python"].update(yaw_change=11.0)):
            previous = copy.deepcopy(self.report)
            mutation(self.report)
            self.reject()
            self.report = previous

    def test_nan_and_unrun_tick_are_rejected(self):
        self.report["cases"][2]["python"]["yaw_change"] = float("nan")
        self.reject()
        self.report["cases"][2]["python"]["yaw_change"] = 0.0
        self.report["cases"][2]["blueprint"]["yaw_change"] = 0.0
        self.reject()

    def test_actor_leak_and_missing_physical_branch_are_rejected(self):
        self.report["native_test_actors_destroyed"] = 59
        self.reject()
        self.report["native_test_actors_destroyed"] = 60
        self.report["policy_shutdown"]["no_controller"] = 0
        self.reject()

    def test_production_network_or_exception_claim_is_rejected(self):
        for flag in ("production_placement_tested", "network_acceptance", "native_exception_gate_tested"):
            self.report[flag] = True
            self.reject()
            self.report[flag] = False
