import copy
import unittest

from test_combat_hud_protocol import combat_fixture
from uep_lyra_weapon_protocol import validate_reports


def fixture():
    reports = combat_fixture()
    for row in reports["server"]["phases"]:
        for peer, ack in row["acks"].items():
            kind = "Rifle" if row["phase"] in ("switch_a", "fire_switched_a") and peer == "A" else "Pistol"
            values = {"radius": 12.0, "width": 48.0 if kind == "Rifle" else 40.0, "height": 48.0 if kind == "Rifle" else 40.0}
            ack["combat_hud"]["production_reticle"] = {
                "class": "W_Reticle_" + kind + "_C", "profile": "Python", "kind": kind,
                "controller": ack["player"]["controller_path"], "item": ack["weapon"]["item"],
                "production_widget": True, "python": dict(values), "blueprint": dict(values), "native": dict(values),
                "automatic_python_ticks": 10}
    for peer, report in reports.items():
        report["production_reticle_slice"] = {"enabled": True}
        report["shutdown"]["weapon_reticle_observers"] = {"active_count": 0, "scopes_created": 3, "scopes_closed": 3, "errors": []}
        if peer != "server":
            report["phases"] = copy.deepcopy([row for row in reports["server"]["phases"] if peer in row["acks"]])
    return reports


class ProductionReticleProtocols(unittest.TestCase):
    def test_complete_synthetic_lane(self):
        self.assertTrue(validate_reports(fixture(), "run", combat_hud=True, production_reticles=True)["production_reticle_acceptance"])

    def test_old_overlay_report_cannot_certify_production(self):
        with self.assertRaisesRegex(RuntimeError, "lane"):
            validate_reports(combat_fixture(), "run", combat_hud=True, production_reticles=True)

    def test_scope_leak_fails(self):
        reports = fixture()
        reports["A"]["shutdown"]["weapon_reticle_observers"]["scopes_closed"] = 2
        with self.assertRaisesRegex(RuntimeError, "scope leak"):
            validate_reports(reports, "run", combat_hud=True, production_reticles=True)

    def test_missing_or_nonproduction_widget_fails(self):
        for remove in (True, False):
            reports = fixture()
            combat = reports["server"]["phases"][0]["acks"]["A"]["combat_hud"]
            if remove:
                del combat["production_reticle"]
            else:
                combat["production_reticle"]["production_widget"] = False
            with self.assertRaises(RuntimeError):
                validate_reports(reports, "run", combat_hud=True, production_reticles=True)

    def test_geometry_difference_fails(self):
        reports = fixture()
        reports["server"]["phases"][0]["acks"]["A"]["combat_hud"]["production_reticle"]["python"]["radius"] = 0
        with self.assertRaisesRegex(RuntimeError, "geometry differs"):
            validate_reports(reports, "run", combat_hud=True, production_reticles=True)


if __name__ == "__main__":
    unittest.main()
