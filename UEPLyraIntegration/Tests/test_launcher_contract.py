"""Reject incomplete or overstated launcher native reports (model inputs)."""
import copy
import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_world/launcher_contract.py"
spec = importlib.util.spec_from_file_location("launcher_contract_model", file)
contract = importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)

class LauncherContract(unittest.TestCase):
    def setUp(self):
        self.report = {"status": "passed", "native_physics_fixture_configured": True, "native_collision_pairs": 16,
            "actors_created": 36, "actors_destroyed": 36, "scopes_created": 16, "scopes_closed": 16,
            "original_replication_flags": [False]*3, "rpc_signature_preserved": True,
            "policy_shutdown": {"errors": []}, "cases": []}
        for flag in ("full_acceptance", "network_acceptance", "packaged_runtime", "collision_handler_called_by_probe",
                     "native_launch_called_by_probe", "velocity_written_after_entry", "player_modified", "cue_visual_parity_tested"):
            self.report[flag] = False
        for name, kind, launch in contract.PLAN:
            value = {"collision_begins": 1, "pawn_selected": True, "launched": launch, "velocity_error": 0.0,
                "class_preserved": True, "fall_condition_observed": "fall" in name, "native_ai_controller": "ai" in name}
            self.report["cases"].append({"name": name, "passed": True, "same_class": True, "python": copy.deepcopy(value),
                "blueprint": copy.deepcopy(value), "python_counters": {"constructions": 1, "begins": 1,
                    "launches": int(launch), "cues": int(launch or kind == "parent"), kind+"_overlaps": 0 if "ai" in name else 1}})

    def test_complete_bounded_matrix(self):
        self.assertEqual(contract.validate(self.report)["cases"], 8)

    def test_collision_replay_or_player_write_claim_rejected(self):
        for field in ("collision_handler_called_by_probe", "native_launch_called_by_probe", "velocity_written_after_entry", "player_modified"):
            report = copy.deepcopy(self.report);report[field] = True
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_missing_native_collision_or_cleanup_rejected(self):
        for field in ("native_collision_pairs", "actors_destroyed", "scopes_closed"):
            report = copy.deepcopy(self.report);report[field] -= 1
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_fall_filter_requires_real_baseline(self):
        for side in ("python", "blueprint"):
            self.report["cases"][4][side]["fall_condition_observed"] = False
        with self.assertRaisesRegex(RuntimeError, "falling filter"):
            contract.validate(self.report)

    def test_wrong_velocity_even_when_both_lanes_match_rejected(self):
        for side in ("python", "blueprint"):
            self.report["cases"][1][side]["velocity_error"] = 4.0
        with self.assertRaisesRegex(RuntimeError, "velocity/type"):
            contract.validate(self.report)

    def test_python_bypass_and_duplicate_case_rejected(self):
        self.report["cases"][1]["python_counters"]["push_overlaps"] = 0
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)
        self.report["cases"][1] = self.report["cases"][0]
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_replication_force_or_unsupported_visual_claim_rejected(self):
        self.report["original_replication_flags"][0] = True
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)
