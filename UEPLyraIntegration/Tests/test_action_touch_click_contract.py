"""Reject fabricated native click/Jump evidence; these rows are models only."""
import copy
import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_hud/action_touch_click_contract.py"
spec = importlib.util.spec_from_file_location("action_touch_click_model", file)
contract = importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)


class ActionTouchClickContract(unittest.TestCase):
    def setUp(self):
        self.report = dict(status="passed", synthetic_commonui_activation=True, native_input_gas_jump_tested=True,
            player_restored=True, jump_observer_closed=True, player_pawn="native-owner", widgets_created=4,
            widget_roots_released=4, policy_shutdown=dict(active_count=0, errors=[]), cases=[])
        for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "physical_touch_tested",
                      "jump_or_launch_called_by_probe", "velocity_or_gravity_written", "ability_granted_by_probe"):
            self.report[field] = False
        for kind, profile in contract.PLAN:
            self.report["cases"].append(dict(kind=kind, profile=profile, native_commonui_activations=1,
                native_jump_events=1, jump_event_pawn="native-owner", rise=22., vertical_velocity=450., movement_mode=3,
                python_clicks=int(profile == "Python"), native_type_preserved=True))

    def test_complete_native_click_matrix(self):
        self.assertEqual(contract.validate(self.report)["cases"], 4)

    def test_callback_without_actual_jump_motion_rejected(self):
        for field, value in (("rise", 0.), ("vertical_velocity", 0.), ("movement_mode", 1), ("rise", float("nan"))):
            report = copy.deepcopy(self.report); report["cases"][0][field] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_wrong_owner_duplicate_event_or_python_bypass_rejected(self):
        for field, value in (("jump_event_pawn", "other-owner"), ("native_jump_events", 2), ("python_clicks", 0)):
            report = copy.deepcopy(self.report); report["cases"][1][field] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_manual_jump_velocity_write_hardware_claim_rejected(self):
        for field in ("jump_or_launch_called_by_probe", "velocity_or_gravity_written", "physical_touch_tested"):
            report = copy.deepcopy(self.report); report[field] = True
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_observer_root_and_player_restore_missing_rejected(self):
        for field, value in (("jump_observer_closed", False), ("widget_roots_released", 3), ("player_restored", False)):
            report = copy.deepcopy(self.report); report[field] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)
