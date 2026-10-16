import copy
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/respawn_native_contract.py"
spec = importlib.util.spec_from_file_location("respawn_native_contract_tests", source)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def valid_report():
    report = {"mode": "native-gas-auto-respawn", "status": "passed", "error": None, "native_respawn_producer_tested": True,
              "native_player_restart_tested": True, "production_widget": "production", "native_duration_seconds": 5.0}
    for flag in ("full_acceptance", "network_acceptance", "synthetic_local_messages", "lethal_damage_tested",
                 "ability_or_health_properties_written", "duration_or_completion_broadcast_called_by_fixture",
                 "fixture_widget_event_invoked", "acoustic_parity_tested"):
        report[flag] = False
    state = {"duration": 5.0, "start": 10.0, "remaining": 4.8, "numeric": 5.0, "text": "5", "glow": 0.96, "fill": 0.96,
             "visibility": 0, "timer_active": True, "respawning": True, "audio_valid": True, "audio_playing": True}
    final_state = dict(state, remaining=-0.2, numeric=0.0, text="0", visibility=1, timer_active=False, respawning=False)
    report["cases"] = [{"name": "native-death-started", "death_state": 1},
                       {"name": "native-respawn-duration", "profile": "Python", "python": state, "blueprint": dict(state)},
                       {"name": "native-player-restarted", "old_pawn": "old", "new_pawn": "new", "health": 100.0,
                        "native_completion_deliveries": 1, "python": final_state, "blueprint": dict(final_state)}]
    report["shutdown"] = {"active_count": 0, "scopes_created": 1, "scopes_closed": 1, "errors": [],
                           "pool_lifetime": {"active_count": 0, "ticker_active": False, "registered": 2, "unregistered": 2, "errors": []}}
    return report


class RespawnNativeReportTests(unittest.TestCase):
    def test_native_producer_is_bounded_acceptance(self):
        self.assertTrue(contract.validate(valid_report())["bounded_runtime_acceptance"])
        self.assertFalse(contract.validate(valid_report())["full_acceptance"])

    def test_synthetic_or_mutated_source_cannot_claim_native_producer(self):
        for flag in ("synthetic_local_messages", "ability_or_health_properties_written",
                     "duration_or_completion_broadcast_called_by_fixture", "fixture_widget_event_invoked",
                     "network_acceptance", "lethal_damage_tested", "acoustic_parity_tested"):
            report = valid_report()
            report[flag] = True
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_missing_restart_death_or_exact_completion_rejected(self):
        for mutation in (lambda r: r.update(native_player_restart_tested=False),
                         lambda r: r["cases"][0].update(death_state=0),
                         lambda r: r["cases"][2].update(new_pawn="old"),
                         lambda r: r["cases"][2].update(native_completion_deliveries=2),
                         lambda r: r["cases"][2].update(native_completion_deliveries=True)):
            report = valid_report()
            mutation(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)

    def test_material_audio_or_nonfinite_values_rejected(self):
        for key, value in (("fill", 0.25), ("audio_valid", False), ("start", float("inf")), ("glow", float("nan"))):
            report = valid_report()
            report["cases"][1]["python"][key] = value
            with self.assertRaises(AssertionError):
                contract.validate(report)
        report = valid_report()
        report["native_duration_seconds"] = float("inf")
        with self.assertRaises(AssertionError):
            contract.validate(report)

    def test_failed_inventory_or_final_scope_residue_rejected(self):
        for mutation in (lambda r: r.update(status="failed"), lambda r: r["cases"].pop(),
                         lambda r: r["shutdown"].update(scopes_created=0, scopes_closed=0),
                         lambda r: r["shutdown"]["pool_lifetime"].update(ticker_active=True)):
            report = valid_report()
            mutation(report)
            with self.assertRaises(AssertionError):
                contract.validate(report)


if __name__ == "__main__":
    unittest.main()
