"""Negative proof-gate tests; model rows are not runtime acceptance evidence."""
import copy
import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_world/teleporter_contract.py"
spec = importlib.util.spec_from_file_location("teleporter_contract_model", file)
contract = importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)


class TeleporterContract(unittest.TestCase):
    def setUp(self):
        self.report = dict(status="passed", native_physics_fixture_configured=True,
            native_collision_pairs=14, actors_created=54, actors_destroyed=54,
            scopes_created=14, scopes_closed=14, original_replication_flag=False,
            original_signatures_preserved=True, policy_shutdown=dict(errors=[]), cases=[])
        self.report.update({flag: False for flag in contract.UNSUPPORTED})
        for name in contract.PLAN:
            outcome = dict(events=["end", "begin"], destination_selected=True, receiving_pawn=True,
                class_preserved=True, receiver_box_destroyed=True, position_error=0., rotation_error=0.,
                control_error=0., velocity_error=0., launched=name != "no-launch")
            self.report["cases"].append(dict(name=name, passed=True, same_class=True,
                blueprint=copy.deepcopy(outcome), python=copy.deepcopy(outcome),
                python_counters=dict(constructions=2, begins=1, destinations=1, character_entries=1,
                    teleports=1, pawn_audio=1, launches=int(name != "no-launch"),
                    rotations=int(name not in ("free-direction", "no-controller")))))

    def test_complete_bounded_report(self):
        self.assertEqual(contract.validate(self.report)["cases"], 7)

    def test_replay_or_overclaim_rejected(self):
        for field in contract.UNSUPPORTED:
            report = copy.deepcopy(self.report); report[field] = True
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_partial_cleanup_and_matrix_rejected(self):
        for field in ("native_collision_pairs", "actors_destroyed", "scopes_closed"):
            report = copy.deepcopy(self.report); report[field] -= 1
            with self.assertRaises(RuntimeError):
                contract.validate(report)
        self.report["cases"].pop()
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_matching_wrong_transform_is_rejected(self):
        for field in ("position_error", "rotation_error", "control_error", "velocity_error"):
            report = copy.deepcopy(self.report)
            for side in ("python", "blueprint"):
                report["cases"][0][side][field] = 2.
            with self.assertRaisesRegex(RuntimeError, "transform/control/launch"):
                contract.validate(report)

    def test_double_overlap_and_missing_receiver_rejected(self):
        for field, value in (("events", ["begin", "begin", "end"]), ("receiving_pawn", False), ("receiver_box_destroyed", False)):
            report = copy.deepcopy(self.report)
            for side in ("python", "blueprint"):
                report["cases"][0][side][field] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_python_bypass_rejected(self):
        for field in ("begins", "destinations", "character_entries", "teleports", "pawn_audio", "launches", "rotations"):
            report = copy.deepcopy(self.report); report["cases"][0]["python_counters"][field] = 0
            with self.assertRaises(RuntimeError):
                contract.validate(report)
