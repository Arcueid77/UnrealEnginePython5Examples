import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_combat_hud_protocol import validate_reticle_host
from uep_lyra_weapon_protocol import validate_reports
from test_production_reticle_protocol import fixture as production_fixture


def checkpoint(kind="Pistol"):
    ack = {"player": {"controller_path": "pc-a"}, "weapon": {"item": "item-a"},
           "combat_hud": {"production_reticle": {"kind": kind}}}
    classes = ["W_Reticle_" + kind + "_C", "W_AmmoCounter_" + kind + "_C"]
    host = {"production_widget": True, "class": "W_WeaponReticleHost_C", "profile": "Python",
            "controller": "pc-a", "item": "item-a", "weapon_instance": "weapon-a",
            "automatic_python_ticks": 10, "python_tick_called_by_probe": False, "weapon_event_called_by_probe": False,
            "native_config_classes": classes, "overlay_children": 2, "native_dead": False, "visibility": 0,
            "children": [{"class": cls, "item": "item-a", "weapon_instance": "weapon-a", "horizontal": 0, "vertical": 0}
                         for cls in classes]}
    return host, ack


def reports_fixture():
    reports = production_fixture()
    for row in reports["server"]["phases"]:
        for ack in row["acks"].values():
            host, _ = checkpoint(ack["combat_hud"]["production_reticle"]["kind"])
            host["controller"], host["item"] = ack["player"]["controller_path"], ack["weapon"]["item"]
            for child in host["children"]:
                child["item"] = host["item"]
            ack["combat_hud"]["reticle_host"] = host
    for peer, report in reports.items():
        report["reticle_host_slice"] = {"enabled": True}
        report["shutdown"]["reticle_host_observers"] = {"active_count": 0, "scopes_created": 0 if peer == "server" else 3,
                                                      "scopes_closed": 0 if peer == "server" else 3, "errors": []}
        if peer != "server":
            report["phases"] = copy.deepcopy([row for row in reports["server"]["phases"] if peer in row["acks"]])
    return reports


class ReticleHostProtocolTests(unittest.TestCase):
    def test_three_authored_weapon_configs(self):
        for kind in ("Pistol", "Rifle", "Shotgun"):
            validate_reticle_host(*checkpoint(kind))

    def test_foreign_owner_or_item_fails(self):
        for field in ("controller", "item"):
            host, ack = checkpoint()
            host[field] = "foreign"
            with self.assertRaises(RuntimeError):
                validate_reticle_host(host, ack)

    def test_foreign_child_or_bad_alignment_fails(self):
        for field, value in (("item", "foreign"), ("weapon_instance", "foreign"), ("horizontal", 2), ("vertical", 2)):
            host, ack = checkpoint()
            host["children"][0][field] = value
            with self.assertRaises(RuntimeError):
                validate_reticle_host(host, ack)

    def test_stale_overlay_or_wrong_configuration_fails(self):
        for field, value in (("overlay_children", 3), ("native_config_classes", ["W_Reticle_Pistol_C"]), ("children", [])):
            host, ack = checkpoint()
            host[field] = value
            with self.assertRaises(RuntimeError):
                validate_reticle_host(host, ack)

    def test_manufactured_tick_or_weapon_entry_fails(self):
        for field, value in (("automatic_python_ticks", 0), ("automatic_python_ticks", True),
                             ("python_tick_called_by_probe", True), ("weapon_event_called_by_probe", True)):
            host, ack = checkpoint()
            host[field] = value
            with self.assertRaises(RuntimeError):
                validate_reticle_host(host, ack)

    def test_visibility_must_follow_native_death(self):
        host, ack = checkpoint()
        host["native_dead"], host["visibility"] = True, 1
        validate_reticle_host(host, ack)
        host["visibility"] = 0
        with self.assertRaises(RuntimeError):
            validate_reticle_host(host, ack)

    def test_host_lane_requires_production_reticles(self):
        with self.assertRaisesRegex(RuntimeError, "require production reticle"):
            validate_reports({}, "run", reticle_hosts=True)

    def test_complete_synthetic_host_lane(self):
        result = validate_reports(reports_fixture(), "run", combat_hud=True, production_reticles=True, reticle_hosts=True)
        self.assertTrue(result["reticle_host_acceptance"])

    def test_old_production_lane_cannot_certify_hosts(self):
        with self.assertRaisesRegex(RuntimeError, "host validation lane"):
            validate_reports(production_fixture(), "run", combat_hud=True, production_reticles=True, reticle_hosts=True)

    def test_missing_host_checkpoint_fails(self):
        reports = reports_fixture()
        del reports["server"]["phases"][0]["acks"]["A"]["combat_hud"]["reticle_host"]
        with self.assertRaisesRegex(RuntimeError, "host checkpoint"):
            validate_reports(reports, "run", combat_hud=True, production_reticles=True, reticle_hosts=True)

    def test_host_scope_leak_fails(self):
        reports = reports_fixture()
        reports["A"]["shutdown"]["reticle_host_observers"]["scopes_closed"] = 2
        with self.assertRaisesRegex(RuntimeError, "host scope leak"):
            validate_reports(reports, "run", combat_hud=True, production_reticles=True, reticle_hosts=True)

    def test_server_ui_or_zero_client_host_evidence_fails(self):
        for peer, count in (("server", 1), ("A", 0)):
            reports = reports_fixture()
            final = reports[peer]["shutdown"]["reticle_host_observers"]
            final["scopes_created"] = final["scopes_closed"] = count
            with self.assertRaisesRegex(RuntimeError, "server UI or missing client"):
                validate_reports(reports, "run", combat_hud=True, production_reticles=True, reticle_hosts=True)

    def test_invalid_host_counter_type_fails(self):
        reports = reports_fixture()
        reports["A"]["shutdown"]["reticle_host_observers"]["active_count"] = False
        with self.assertRaisesRegex(RuntimeError, "host counters"):
            validate_reports(reports, "run", combat_hud=True, production_reticles=True, reticle_hosts=True)


if __name__ == "__main__":
    unittest.main()
