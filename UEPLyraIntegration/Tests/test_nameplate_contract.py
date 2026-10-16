"""Negative checks of the future runtime gate, not fourteen Engine passes."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("_np_contract_test", Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud/nameplate_contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class NameplateGate(unittest.TestCase):
    def setUp(self):
        visual = {"name": "Player One", "health_progress": .37, "health_resource": "/Game/HealthMaterial", "visibility": 0}
        self.report = {"schema_version": 1, "status": "passed", "error": None, "actual_production_widget": True,
            "original_bp_baseline": True, "isolated_viewport_lifecycle": True, "business_migration_complete": False,
            "full_acceptance": False, "packaged_runtime": False, "physical_input_tested": False,
            "native_damage_producer_tested": False, "native_team_reassignment_tested": False,
            "native_projection_parity_tested": False, "native_unbind_observed": True, "no_late_delivery": True,
            "cases": [{"name": name, "passed": True, "class_preserved": True, "python": copy.deepcopy(visual),
                       "blueprint": copy.deepcopy(visual)} for name in contract.CASES],
            "shutdown": dict.fromkeys(contract.COUNTERS, 1)}
        self.report["shutdown"].update(active_count=0, active_widgets=[], errors=[], init_owner_released=0)

    def reject(self):
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_declared_bounded_report_only_passes_declared_scope(self):
        gate = contract.validate(self.report)
        self.assertEqual(gate["case_count"], 14)
        self.assertFalse(gate["full_acceptance"])

    def test_missing_or_reordered_case_is_rejected(self):
        self.report["cases"].reverse()
        self.reject()

    def test_identical_but_nonfinite_health_is_rejected(self):
        for side in ("python", "blueprint"):
            self.report["cases"][0][side]["health_progress"] = float("nan")
        self.reject()

    def test_caller_comparison_difference_is_rejected(self):
        self.report["cases"][3]["blueprint"]["health_resource"] = "/Wrong"
        self.reject()

    def test_unsupported_projection_or_package_claim_is_rejected(self):
        self.report["native_projection_parity_tested"] = True
        self.reject()

    def test_missing_native_unbind_proof_is_rejected(self):
        self.report["native_unbind_observed"] = False
        self.reject()

    def test_unbalanced_initstate_or_team_proxy_is_rejected(self):
        self.report["shutdown"]["init_unbound"] = 0
        self.reject()

    def test_native_owner_release_is_separate_from_explicit_unregister(self):
        self.report["shutdown"].update(init_bound=2, init_unbound=1, init_owner_released=1)
        self.assertTrue(contract.validate(self.report)["bounded_runtime_acceptance"])
        self.report["shutdown"].update(init_unbound=0, init_owner_released=2)
        self.reject()  # Losing every owner is not explicit native-unbind proof.

    def test_retained_scope_or_suppressed_error_is_rejected(self):
        self.report["shutdown"]["errors"] = ["cleanup failed"]
        self.reject()
