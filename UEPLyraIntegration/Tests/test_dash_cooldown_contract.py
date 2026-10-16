import copy
import importlib.util
from pathlib import Path
import unittest


source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/dash_cooldown_contract.py"
spec = importlib.util.spec_from_file_location("dash_report_contract", source)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def valid_report():
    report = {"schema_version": 1, "status": "passed", "error": None, "production_widget": "/actual/production/widget",
              "full_acceptance": False, "network_acceptance": False, "native_dash_producer_tested": False,
              "dead_health_tested": False, "widget_tick_invoked_by_fixture": False, "lifecycle_event_invoked_by_fixture": False,
              "compiled_vm_transport": True, "material_absolute_tolerance": 0.00001, "paused_wall_seconds": 1.1,
              "reconstruct_entry": "native same-widget AddToViewport after RemoveFromParent; test-owned remount",
              "lifecycle_entry": "test-owned same-class viewport pair; production mount uses UIExtension pool",
              "shutdown": {"scopes_created": 8, "scopes_closed": 8, "active_count": 0, "errors": [], "health_binds": 4, "health_unbinds": 4}, "cases": []}
    for name in contract.CASES:
        if name == "destruct-no-late-delivery":
            report["cases"].append({"name": name, "messages_before": 3, "messages_after": 3})
            continue
        duration = 4.0 if name == "typed-owner-duration" else 1.0 if name == "same-widget-native-reconstruct" else 2.5
        charging = name != "native-countdown-completed"
        state = {"duration": duration, "start": 1.0, "charging": charging, "visibility": 3,
                 "glow": 0.5, "fill": 0.5, "active_animation": False, "inactive_animation": False}
        lifecycle = name == "same-widget-native-reconstruct"
        report["cases"].append({"name": name, "profile": "BlueprintFallback" if name == "blueprint-profile-resume" else "Python",
                                "test_owned_lifecycle_widget": lifecycle, "widget": "/test/owned/widget" if lifecycle else report["production_widget"],
                                "automatic_ticks": 3, "python": state, "blueprint": copy.deepcopy(state)})
    report["shutdown"]["pool_lifetime"] = {"source": "read-only-native-UIExtension-active-entry-membership",
                                             "registered": 2, "unregistered": 2, "active_count": 0,
                                             "ticker_active": False, "errors": []}
    return report


class DashReportGateTests(unittest.TestCase):
    def test_bounded_report_passes_without_broad_claim(self):
        self.assertFalse(contract.validate(valid_report())["full_acceptance"])

    def test_missing_reordered_or_failed_report_rejected(self):
        for change in (lambda report: report["cases"].pop(), lambda report: report["cases"].reverse(),
                       lambda report: report.update(status="failed")):
            report = valid_report()
            change(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_unsupported_claims_rejected(self):
        for flag in ("full_acceptance", "network_acceptance", "native_dash_producer_tested", "dead_health_tested",
                     "widget_tick_invoked_by_fixture", "lifecycle_event_invoked_by_fixture"):
            report = valid_report()
            report[flag] = True
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_presentation_or_animation_mismatch_rejected(self):
        for key, value in (("fill", 0.7), ("active_animation", True), ("visibility", 1), ("charging", False)):
            report = valid_report()
            report["cases"][1]["python"][key] = value
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_nonfinite_material_and_widened_tolerance_rejected(self):
        for value in (float("nan"), float("inf")):
            report = valid_report()
            report["cases"][1]["python"]["glow"] = value
            with self.assertRaises(AssertionError):
                contract.validate(report)
        report = valid_report()
        report["material_absolute_tolerance"] = 0.025
        with self.assertRaises(AssertionError):
            contract.validate(report)

    def test_missing_native_remount_production_or_pause_rejected(self):
        for key in ("production_widget", "reconstruct_entry", "paused_wall_seconds", "lifecycle_entry"):
            report = valid_report()
            del report[key]
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_late_messages_and_unbalanced_health_scopes_rejected(self):
        for change in (lambda report: report["cases"][-2].update(messages_after=4),
                       lambda report: report["shutdown"].update(health_unbinds=3),
                       lambda report: report["shutdown"].update(scopes_closed=7),
                       lambda report: report["shutdown"].update(active_count=1)):
            report = valid_report()
            change(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_pool_sampler_residue_rejected(self):
        for key, value in (("active_count", 1), ("ticker_active", True), ("unregistered", 1), ("errors", ["failure"])):
            report = valid_report()
            report["shutdown"]["pool_lifetime"][key] = value
            with self.assertRaises(AssertionError):
                contract.validate(report)


if __name__ == "__main__":
    unittest.main()
