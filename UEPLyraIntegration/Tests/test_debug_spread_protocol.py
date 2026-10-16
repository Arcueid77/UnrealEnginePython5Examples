import copy
import unittest

from test_combat_hud_protocol import combat_fixture
from uep_lyra_weapon_protocol import validate_reports


def fixture():
    reports = combat_fixture()
    for row in reports["server"]["phases"]:
        for peer, ack in row["acks"].items():
            ack["combat_hud"]["debug_spread"] = {
                "class": "W_DebugWeaponSpreadWidget_C", "profile": "Python",
                "controller": ack["player"]["controller_path"], "item": ack["weapon"]["item"],
                "weapon_instance": "native-weapon", "python": "1.234", "blueprint": "1.234", "native": "1.234",
                "python_ticks": 5, "samples": 2, "native_angle": 1.234, "peak_angle": 1.234,
                "production_widget": False, "origin": "test-owned-debug-spread-overlay",
                "python_tick_called_by_probe": False, "spread_written": False}
    for peer, report in reports.items():
        report["debug_spread_slice"] = {"enabled": True}
        if peer != "server":
            report["phases"] = copy.deepcopy([row for row in reports["server"]["phases"] if peer in row["acks"]])
    return reports


class DebugSpreadProtocols(unittest.TestCase):
    def test_complete_synthetic_lane(self):
        self.assertTrue(validate_reports(fixture(), "run", combat_hud=True, debug_spread=True)["debug_spread_acceptance"])

    def test_old_report_cannot_certify_new_lane(self):
        with self.assertRaisesRegex(RuntimeError, "lane"):
            validate_reports(combat_fixture(), "run", combat_hud=True, debug_spread=True)

    def test_missing_sample_does_not_silently_pass(self):
        reports = fixture()
        del reports["server"]["phases"][0]["acks"]["A"]["combat_hud"]["debug_spread"]
        with self.assertRaisesRegex(RuntimeError, "Missing debug"):
            validate_reports(reports, "run", combat_hud=True, debug_spread=True)

    def test_reject_manual_tick_or_state_writes(self):
        for name in ("python_tick_called_by_probe", "spread_written", "production_widget"):
            reports = fixture()
            reports["server"]["phases"][0]["acks"]["A"]["combat_hud"]["debug_spread"][name] = True
            with self.assertRaises(RuntimeError):
                validate_reports(reports, "run", combat_hud=True, debug_spread=True)

    def test_reject_text_difference(self):
        reports = fixture()
        reports["server"]["phases"][0]["acks"]["A"]["combat_hud"]["debug_spread"]["python"] = "0"
        with self.assertRaisesRegex(RuntimeError, "text differs"):
            validate_reports(reports, "run", combat_hud=True, debug_spread=True)


if __name__ == "__main__":
    unittest.main()
