"""Contract negatives and fixture API checks, not eleven Engine passes."""
import ast
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud"
spec = importlib.util.spec_from_file_location("_np_component_contract", ROOT/"nameplate_components_contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class ComponentGate(unittest.TestCase):
    def setUp(self):
        self.report = {"schema_version": 1, "status": "passed", "error": None, "elapsed_seconds": 1.0,
            "actual_production_manager": True, "native_indicator_membership_read": True,
            "native_source_endplay": True, "native_nonlocal_destroy": True,
            "native_baseline_endplay": True, "legacy_duplicate_confirmed": True, "fixture_only_orphans_cleaned": True,
            "cases": [{"name": name, "passed": True, "same_class": True, "python": {"value": 1},
                       "blueprint": {"value": 1}} for name in contract.CASES]}
        for key in ("full_acceptance", "network_acceptance", "packaged_runtime", "fixture_lifecycle_event_invoked",
                    "native_health_team_inventory_written", "projection_parity_tested", "legacy_policy_silently_fixed"):
            self.report[key] = False
        for key in ("source_shutdown", "manager_shutdown"):
            self.report[key] = {"active_count": 0, "errors": [], "scopes_created": 2, "scopes_closed": 2,
                                "helpers_rooted": 2, "helpers_unrooted": 2}

    def reject(self):
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_gate_only_certifies_bounded_component_cases(self):
        result = contract.validate(self.report)
        self.assertEqual(result["case_count"], 11)
        self.assertFalse(result["full_acceptance"])

    def test_case_order_and_native_comparison_are_required(self):
        original = copy.deepcopy(self.report)
        self.report["cases"].reverse()
        self.reject()
        self.report = original
        self.report["cases"][2]["blueprint"]["value"] = 2
        self.reject()

    def test_class_identity_is_required(self):
        self.report["cases"][0]["same_class"] = False
        self.reject()

    def test_full_or_network_claim_is_rejected(self):
        self.report["network_acceptance"] = True
        self.reject()

    def test_actual_native_membership_and_lifecycle_are_required(self):
        for key in ("actual_production_manager", "native_indicator_membership_read", "native_source_endplay",
                    "native_baseline_endplay", "native_nonlocal_destroy", "legacy_duplicate_confirmed", "fixture_only_orphans_cleaned"):
            with self.subTest(key=key):
                self.report[key] = False
                self.reject()
                self.report[key] = True

    def test_scopes_roots_and_errors_gate_final_state(self):
        for key, value in (("scopes_closed", 1), ("helpers_unrooted", 0), ("active_count", 1), ("errors", ["failed"])):
            with self.subTest(key=key):
                original = self.report["source_shutdown"][key]
                self.report["source_shutdown"][key] = value
                self.reject()
                self.report["source_shutdown"][key] = original

    def test_nan_elapsed_is_rejected(self):
        self.report["elapsed_seconds"] = float("nan")
        self.reject()

    def test_fixture_owns_ticker_and_only_uses_native_lifecycle_entries(self):
        source = (ROOT/"nameplate_components_validation.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        owners = [node for node in tree.body if isinstance(node, ast.Assign) and
                  isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "add_ticker"]
        self.assertEqual(len(owners), 1)
        for api in ('"AddComponentByClass"', '"FinishAddComponent"', '"K2_GetComponentsByClass"', 'get_property("Indicators")'):
            self.assertIn(api, source)
        for unsupported in ('"GetIndicators"', '"GetIndicatorManagerComponent", self.native', '"ReceiveBeginPlay"', '"ReceiveEndPlay"', '.broadcast_event('):
            self.assertNotIn(unsupported, source)

    def test_soft_class_identity_is_a_path_not_debug_repr_with_refcounts(self):
        for source in ((ROOT/"nameplate_components_validation.py").read_text(encoding="utf-8"),
                       (ROOT.parent/"uep_lyra_nameplate_probe.py").read_text(encoding="utf-8")):
            self.assertNotIn('str(value.call_function("GetIndicatorClass"))', source)
            self.assertNotIn('str(item.call_function("GetIndicatorClass"))', source)
            self.assertRegex(source, r'path\((?:item|value)\.call_function\("GetIndicatorClass"\)\)')
