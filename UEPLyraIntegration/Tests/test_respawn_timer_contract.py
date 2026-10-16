import copy
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/respawn_timer_contract.py"
spec = importlib.util.spec_from_file_location("respawn_report_contract", source)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def valid_report():
    report = {"schema_version": 1, "status": "passed", "error": None, "production_widget": "production",
              "synthetic_local_messages": True, "audio_component_tested": True, "material_absolute_tolerance": 0.00001,
              "paused_wall_seconds": 1.1, "remaining_observation": "derived native deadline, not BP function-local storage", "cases": []}
    report["lifecycle_entry"] = "test-owned same-class viewport pair; production mount uses UIExtension pool"
    report["reconstruct_entry"] = "native same-widget AddToViewport after RemoveFromParent; test-owned remount"
    for flag in ("full_acceptance", "network_acceptance", "native_respawn_producer_tested", "fixture_widget_event_invoked", "acoustic_parity_tested"):
        report[flag] = False
    for index, name in enumerate(contract.CASES):
        state = {"duration": 4.0, "start": 1.0, "remaining": 3.0, "respawning": True, "visibility": 0,
                 "numeric": 3.0, "text": "3", "glow": 0.75, "fill": 0.75, "audio_valid": True, "audio_playing": True, "timer_active": True}
        if index in (5, 6):
            state.update(respawning=index == 6, timer_active=False, visibility=1)
        if index == 10:
            state.update(timer_active=False, audio_playing=False)
        if index == 11:
            state.update(duration=1.0)
        report["cases"].append({"name": name, "python": state, "blueprint": dict(state),
                                "profile": "BlueprintFallback" if name == "blueprint-profile-resume" else "Python",
                                "test_owned_lifecycle_widget": index >= 10})
    report["shutdown"] = {"active_count": 0, "scopes_created": 4, "scopes_closed": 4, "errors": [],
                            "timer_updates": 8, "animation_completions": 1,
                            "pool_lifetime": {"active_count": 0, "ticker_active": False, "registered": 2, "unregistered": 2, "errors": []}}
    return report


class RespawnReportTests(unittest.TestCase):
    def test_bounded_report_passes(self):
        self.assertFalse(contract.validate(valid_report())["full_acceptance"])

    def test_missing_cases_or_failed_run_rejected(self):
        for mutate in (lambda report: report["cases"].pop(), lambda report: report.update(status="failed")):
            report = valid_report()
            mutate(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_fake_native_producer_or_broad_claims_rejected(self):
        for flag in ("full_acceptance", "network_acceptance", "native_respawn_producer_tested", "fixture_widget_event_invoked", "acoustic_parity_tested"):
            report = valid_report()
            report[flag] = True
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_material_audio_or_timer_mismatch_rejected(self):
        for key, value in (("fill", 0.25), ("glow", float("nan")), ("audio_valid", False), ("timer_active", False)):
            report = valid_report()
            report["cases"][1]["python"][key] = value
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_completed_flag_and_final_scope_errors_rejected(self):
        for mutate in (lambda report: report["cases"][6]["python"].update(respawning=False),
                       lambda report: report["shutdown"].update(scopes_closed=1),
                       lambda report: report["shutdown"]["pool_lifetime"].update(ticker_active=True)):
            report = valid_report()
            mutate(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_synthetic_bp_local_read_and_widened_tolerance_rejected(self):
        for key, value in (("remaining_observation", "BP stack read"), ("material_absolute_tolerance", 0.05)):
            report = valid_report()
            report[key] = value
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_lifecycle_scope_attribution_or_fake_remount_rejected(self):
        for mutate in (lambda report: report["cases"][-1].update(test_owned_lifecycle_widget=False),
                       lambda report: report.update(reconstruct_entry="manual Construct"),
                       lambda report: report["cases"][-2]["python"].update(timer_active=True)):
            report = valid_report()
            mutate(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)


if __name__ == "__main__":
    unittest.main()
