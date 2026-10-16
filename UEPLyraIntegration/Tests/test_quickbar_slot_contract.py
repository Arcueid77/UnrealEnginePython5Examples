import copy
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/quickbar_slot_contract.py"
spec = importlib.util.spec_from_file_location("quickbar_report_contract_tests", source)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def valid_report():
    report = {"status": "passed", "error": None, "production_widgets": ["slot0", "slot1", "slot2"], "cases": [],
              "baseline_init_policy": "default Python initialization, then BP Profile and explicit listener resume",
              "mouse_reply_observation": "native EventReply type; internal handled bit not reflected"}
    for flag in ("full_acceptance", "network_acceptance", "native_inventory_properties_written", "fixture_lifecycle_event_invoked",
                 "physical_mouse_tested", "native_weapon_switch_tested", "bp_initialization_parity_tested"):
        report[flag] = False
    report["external_named_query_migrated"] = True
    for name in contract.CASES:
        values = []
        count = 1 if name in ("invalid-index-preserves-slot",)+contract.CASES[-2:] else 3
        for index in range(count):
            state = {"index": index, "empty": name == "empty-slot-message" or index > 0, "selected": index == 0,
                     "numeric": 60.0 if index == 0 else 0.0, "text": "60" if index == 0 else "0",
                     "icon": "icon", "ammo_icon": "ammo", "animations": [False, False, False]}
            values.append({"python": state, "blueprint": dict(state),
                           "profile": "BlueprintFallback" if name == "blueprint-profile-resume" else "Python"})
        report["cases"].append({"name": name, "slots": values, "test_owned_lifecycle_widget": name in contract.CASES[-2:]})
    report["shutdown"] = {"active_count": 0, "scopes_created": 12, "scopes_closed": 12, "ticks": 10, "slot_messages": 20,
                           "mouse_calls": 1, "external_named_query_migrated": True, "named_query_calls": 4, "errors": [],
                           "pool_lifetime": {"active_count": 0, "ticker_active": False, "registered": 3, "unregistered": 3, "errors": []}}
    return report


class QuickBarReportTests(unittest.TestCase):
    def test_bounded_report_requires_named_query_proof(self):
        result = contract.validate(valid_report())
        self.assertTrue(result["bounded_runtime_acceptance"])
        self.assertTrue(result["external_named_query_migrated"])
        self.assertFalse(result["full_acceptance"])

    def test_missing_production_slot_or_case_rejected(self):
        for mutation in (lambda r: r["production_widgets"].pop(), lambda r: r["cases"].pop(),
                         lambda r: r["cases"][0]["slots"].pop()):
            report = valid_report()
            mutation(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_broad_query_switch_initialization_and_physical_input_claims_rejected(self):
        for flag in ("full_acceptance", "network_acceptance", "physical_mouse_tested",
                     "native_weapon_switch_tested", "bp_initialization_parity_tested"):
            report = valid_report()
            report[flag] = True
            with self.assertRaises(AssertionError):
                contract.validate(report)
        report = valid_report()
        report["external_named_query_migrated"] = False
        with self.assertRaises(AssertionError):
            contract.validate(report)

    def test_numeric_texture_animation_or_profile_mismatch_rejected(self):
        for key, value in (("numeric", float("nan")), ("icon", "other"), ("animations", [True, False, False])):
            report = valid_report()
            report["cases"][0]["slots"][0]["python"][key] = value
            with self.assertRaises(AssertionError):
                contract.validate(report)
        report = valid_report()
        report["cases"][7]["slots"][0]["profile"] = "Python"
        with self.assertRaises(AssertionError):
            contract.validate(report)

    def test_fake_lifecycle_or_unreflected_handled_bit_claim_rejected(self):
        for mutation in (lambda r: r["cases"][-1].update(test_owned_lifecycle_widget=False),
                         lambda r: r.update(mouse_reply_observation="handled bit read"),
                         lambda r: r.update(baseline_init_policy="original BP OnInitialized")):
            report = valid_report()
            mutation(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_scope_pool_or_missing_mouse_entry_rejected(self):
        for mutation in (lambda r: r["shutdown"].update(active_count=1), lambda r: r["shutdown"].update(scopes_closed=11),
                         lambda r: r["shutdown"].update(mouse_calls=0),
                         lambda r: r["shutdown"]["pool_lifetime"].update(ticker_active=True)):
            report = valid_report()
            mutation(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)


if __name__ == "__main__":
    unittest.main()
