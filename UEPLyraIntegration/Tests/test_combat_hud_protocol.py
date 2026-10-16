"""Synthetic negative contracts are not proof of gameplay/network execution."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"))
from uep_lyra_combat_hud_protocol import CLICK_EVENT, FIRE_PROFILES
from uep_lyra_weapon_protocol import validate_reports
from test_weapon_network_protocol import fixture


def combat_fixture():
    reports = fixture()
    counters = {peer: {"Python": 0, "BlueprintFallback": 0} for peer in ("A", "B0", "B1")}
    profiles = dict.fromkeys(counters, "Python")
    for row in reports["server"]["phases"]:
        packet, phase = row["packet"], row["phase"]
        for peer, ack in row["acks"].items():
            ack["player"].update(health=100.0, max_health=100.0)
            packet["statuses_before"][peer]["combat_hud"] = {
                "fire_button": {"clicks": copy.deepcopy(counters[peer])}}
            if packet["target"] == peer and (phase.startswith("fire_") or phase == "empty_b"):
                profiles[peer] = FIRE_PROFILES.get(phase, "Python")
                counters[peer][profiles[peer]] += 10
            weapon = ack["weapon"]
            values = {"segments": float(weapon["maximum"] * 4 + 1),
                      "range": [0.0, weapon["magazine"] / weapon["maximum"] * 0.25, 0.0, 1.0]}
            ack["combat_hud"] = {
                "health_visuals": {"controller": ack["player"]["controller_path"],
                                   "current": 100.0, "target": 100.0, "updated": 1.0},
                "reticle": {"production_widget": False, "origin": "test-owned-ammo-bar-overlay",
                            "source_class": "W_AmmoCounter_Pistol_C", "source_widget": "native-ammo-counter",
                            "weapon_instance": "native-weapon-instance", "class": "W_Reticle_AmmoBar_C", "profile": "Python",
                            "controller": ack["player"]["controller_path"], "item": weapon["item"],
                            "python": copy.deepcopy(values), "blueprint": copy.deepcopy(values), "native": values},
                "fire_button": {"class": "W_FireButton_C", "controller": ack["player"]["controller_path"],
                                "entry": CLICK_EVENT, "physical_touch_tested": False, "inventory_written": False,
                                "profile": profiles[peer], "clicks": copy.deepcopy(counters[peer])}}
    for peer, report in reports.items():
        report["combat_hud_slice"] = {"enabled": True}
        if peer != "server":
            report["phases"] = copy.deepcopy([row for row in reports["server"]["phases"] if peer in row["acks"]])
    return reports


class CombatHUDContracts(unittest.TestCase):
    def setUp(self):
        self.reports = combat_fixture()
        self.ack = self.reports["server"]["phases"][2]["acks"]["A"]

    def test_complete_synthetic_contract(self):
        self.assertTrue(validate_reports(self.reports, "run", combat_hud=True)["combat_hud_acceptance"])

    def test_old_weapon_report_cannot_prove_combat_hud(self):
        with self.assertRaisesRegex(RuntimeError, "lane"):
            validate_reports(fixture(), "run", combat_hud=True)

    def test_combat_run_cannot_silently_use_old_validation_lane(self):
        with self.assertRaisesRegex(RuntimeError, "lane"):
            validate_reports(self.reports, "run")

    def test_reject_false_production_reticle_claim(self):
        self.ack["combat_hud"]["reticle"]["production_widget"] = True
        with self.assertRaisesRegex(RuntimeError, "production"):
            validate_reports(self.reports, "run", combat_hud=True)

    def test_reject_no_native_weapon_context(self):
        self.ack["combat_hud"]["reticle"]["weapon_instance"] = None
        with self.assertRaisesRegex(RuntimeError, "native weapon context"):
            validate_reports(self.reports, "run", combat_hud=True)

    def test_reject_reticle_from_other_inventory(self):
        self.ack["combat_hud"]["reticle"]["item"] = "other-item"
        with self.assertRaisesRegex(RuntimeError, "ownership"):
            validate_reports(self.reports, "run", combat_hud=True)

    def test_reject_stale_material(self):
        self.ack["combat_hud"]["reticle"]["python"]["range"][1] = 0.25
        with self.assertRaisesRegex(RuntimeError, "material mismatch"):
            validate_reports(self.reports, "run", combat_hud=True)

    def test_reject_nonfinite_material(self):
        self.ack["combat_hud"]["reticle"]["python"]["range"][1] = float("nan")
        with self.assertRaisesRegex(RuntimeError, "number"):
            validate_reports(self.reports, "run", combat_hud=True)

    def test_reject_no_python_click_entry(self):
        self.ack["combat_hud"]["fire_button"]["clicks"]["Python"] = 0
        with self.assertRaisesRegex(RuntimeError, "No selected"):
            validate_reports(self.reports, "run", combat_hud=True)

    def test_reject_numeric_ui_zero_with_healthy_native_pawn(self):
        self.ack["combat_hud"]["health_visuals"]["current"] = 0.0
        with self.assertRaisesRegex(RuntimeError, "Health numeric"):
            validate_reports(self.reports, "run", combat_hud=True)

    def test_reject_other_player_health_visuals(self):
        self.ack["combat_hud"]["health_visuals"]["controller"] = "other-controller"
        with self.assertRaisesRegex(RuntimeError, "Health visuals crossed"):
            validate_reports(self.reports, "run", combat_hud=True)

    def test_reject_uninvolved_client_click(self):
        ack = self.reports["server"]["phases"][2]["acks"]["B0"]
        ack["combat_hud"]["fire_button"]["clicks"]["Python"] = 1
        with self.assertRaisesRegex(RuntimeError, "other client"):
            validate_reports(self.reports, "run", combat_hud=True)

    def test_reject_physical_touch_claim(self):
        self.ack["combat_hud"]["fire_button"]["physical_touch_tested"] = True
        with self.assertRaisesRegex(RuntimeError, "boundary"):
            validate_reports(self.reports, "run", combat_hud=True)
