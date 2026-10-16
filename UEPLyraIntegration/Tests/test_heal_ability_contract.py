"""Native heal proof gate negatives, modeled data only."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"
sys.path.insert(0, str(root))
from uep_lyra_world import heal_ability_contract as contract


class HealAbilityContract(unittest.TestCase):
    def setUp(self):
        self.report = dict(status="passed", native_inventory_equipment_ability_grant=True, original_player_restored=True,
            cases=[], policy_shutdown=dict(active_count=0, scopes_created=5, scopes_closed=5,
                timers_created=5, timers_cleared=5, errors=[]))
        for flag in ("network_acceptance", "full_acceptance", "packaged_runtime", "ability_activate_called_by_probe",
                     "task_callbacks_called_by_probe", "health_properties_written", "animation_assets_modified", "production_placement_tested"):
            self.report[flag] = False
        for name in contract.PLAN:
            outcome = dict(active_after=False, health_before=75., health_after=100., max_health=100., native_type_preserved=True)
            self.report["cases"].append(dict(name=name, passed=True, python=copy.deepcopy(outcome), blueprint=copy.deepcopy(outcome),
                python_counters=dict(activations=1, heals=1, scopes_created=1, scopes_closed=1, timers_created=1, timers_cleared=1,
                    timer_callbacks=int(name == "native-timer"), completed=int(name in ("original-montage", "paused-world-time")),
                    interrupted=int(name in ("native-cancel", "native-interrupt")), cancelled=0, native_ends=int(name != "active-profile-switch")), native_elapsed_seconds=[1., 1.],
                native_pause_observed=[name == "paused-world-time"]*2, inventory_rollbacks=[True, True]))
            self.report["cases"][-1]["native_profile_switch_exercised"] = [name == "active-profile-switch"]*2

    def test_complete_bounded_matrix(self):
        self.assertEqual(contract.validate(self.report)["cases"], 7)

    def test_matching_fake_health_and_active_leak_rejected(self):
        for field, value in (("health_after", 75.), ("active_after", True), ("native_type_preserved", False)):
            report = copy.deepcopy(self.report)
            for side in ("python", "blueprint"):
                report["cases"][0][side][field] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_task_timer_or_inventory_cleanup_missing_rejected(self):
        for field in ("scopes_closed", "timers_cleared"):
            report = copy.deepcopy(self.report); report["cases"][0]["python_counters"][field] = 0
            with self.assertRaises(RuntimeError):
                contract.validate(report)
        self.report["cases"][0]["inventory_rollbacks"] = [True, False]
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_shortened_timer_and_fake_pause_rejected(self):
        self.report["cases"][3]["native_elapsed_seconds"] = [.1, 1.]
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)
        self.report["cases"][3]["native_elapsed_seconds"] = [1., 1.]
        self.report["cases"][4]["native_pause_observed"] = [False, True]
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_direct_activation_callback_replay_or_attribute_write_rejected(self):
        for field in ("ability_activate_called_by_probe", "task_callbacks_called_by_probe", "health_properties_written"):
            report = copy.deepcopy(self.report); report[field] = True
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_matching_behavior_without_native_end_callback_proof_is_rejected(self):
        self.report["cases"][0]["python_counters"]["native_ends"] = 0
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)
