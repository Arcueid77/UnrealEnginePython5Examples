"""Synthetic failure gates; native collision/GAS/Timeline run is separate."""
import copy
import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_world/grant_ge_pad_contract.py"
spec = importlib.util.spec_from_file_location("_grant_ge_contract", file)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)

class GrantGEGate(unittest.TestCase):
    def setUp(self):
        values = [{"active": True}, {"yaw_rate": 50.0}, {"health": 100.0, "mesh_hidden": True},
            {"active": False, "text": "Charging", "tick": False, "light": False, "mesh_hidden": True},
            {"curve_matches": True, "actor_tick_paused": True, "timeline_playing": True},
            {"active": True, "tick": True, "light": True, "mesh_hidden": False, "percent": 0.0}]
        self.report = {"status": "passed", "error": None, "full_default_duration_tested": True,
            "fixture_duration": 15.0, "original_default_duration": 15.0, "fixture_scope_closed": True,
            "effect_duration_policy": 0, "native_player_restored": True, "actors_created": 2, "actors_destroyed": 2,
            "native_baseline_health": 75.0, "cooldown_seconds": {"python": 15.02, "blueprint": 15.01},
            "timeline_samples": {side: {"position": .4, "actual": .4, "native_expected": .4} for side in ("python", "blueprint")},
            "cases": [{"name": name, "passed": True, "same_class": True, "python": value, "blueprint": copy.deepcopy(value)}
                for name, value in zip(contract.CASES, values)],
            "policy_shutdown": dict(constructions=1, begins=1, ends=1, actives=1, updates=20, finishes=1, ticks=50, errors=[])}
        for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "manual_lifecycle_event", "handler_called_by_probe",
                     "timeline_driven_by_probe", "attributes_written_by_probe", "culture_switch_tested"):
            self.report[flag] = False

    def test_bounded_default_cooldown_lane(self):
        self.assertEqual(contract.validate(self.report)["case_count"], 6)
        self.assertFalse(contract.validate(self.report)["full_acceptance"])

    def test_early_or_missing_cooldown_completion_rejected(self):
        for value in (0.6, float("nan"), 17.0):
            report = copy.deepcopy(self.report)
            report["cooldown_seconds"]["python"] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_unhealed_unpaused_or_unfinished_rejected(self):
        for index, values in ((2, {"health": 75.0}), (3, {"active": True}), (4, {"actor_tick_paused": False}), (5, {"percent": 1.0})):
            report = copy.deepcopy(self.report)
            for side in ("python", "blueprint"):
                report["cases"][index][side].update(values)
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_fake_native_curve_or_scope_leak_rejected(self):
        self.report["timeline_samples"]["python"]["actual"] = .8
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)
        self.report["timeline_samples"]["python"]["actual"] = .4
        self.report["fixture_scope_closed"] = False
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_no_manual_event_or_attribute_shortcut(self):
        for flag in ("handler_called_by_probe", "timeline_driven_by_probe", "attributes_written_by_probe", "network_acceptance"):
            report = copy.deepcopy(self.report)
            report[flag] = True
            with self.assertRaises(RuntimeError):
                contract.validate(report)
