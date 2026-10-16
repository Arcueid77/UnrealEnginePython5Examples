"""Documentation/ledger consistency only; never certifies a new native run."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]/"Migration"
CASES = (
    ("device_color_pilot", "/ShooterCore/Game/B_TeamColor_DeviceProperty.B_TeamColor_DeviceProperty", "29-device-color.json"),
    ("held_widget_ability_pilot", "/ShooterCore/Input/Abilities/GAB_ShowWidget_WhileInputHeld.GAB_ShowWidget_WhileInputHeld", "32-held-widget.json"),
    ("pressed_widget_ability_pilot", "/ShooterCore/Input/Abilities/GAB_ShowWidget_WhenInputPressed.GAB_ShowWidget_WhenInputPressed", "34-widget-pressed.json"),
)


class MigrationStatusConsistency(unittest.TestCase):
    def setUp(self): self.manifest = json.loads((ROOT/"batches.json").read_text(encoding="utf-8-sig"))

    def test_candidate_rows_match_already_accepted_pilots(self):
        for key, path, ledger in CASES:
            with self.subTest(pilot=key):
                row, = [row for row in self.manifest["assets"] if row["path"] == path]
                self.assertEqual(row["status"], self.manifest[key]["status"])
                self.assertTrue(row["scope_review"])

    def test_references_are_existing_passed_ledgers_not_new_execution(self):
        review = self.manifest["candidate_status_reconciliation"]
        self.assertIs(review["documentation_only"], True)
        self.assertIs(review["new_native_execution_claimed"], False)
        self.assertEqual(set(review["evidence_ledgers"]), {value[2] for value in CASES})
        for key, path, filename in CASES:
            ledger = json.loads((ROOT/"Acceptance"/filename).read_text(encoding="utf-8-sig"))
            self.assertEqual(ledger["status"], "evidence_snapshot")
            self.assertTrue(ledger["runs"])
            self.assertTrue(all(row["status"] == "passed" for row in ledger["runs"]))
            self.assertIs(ledger["full_version_acceptance"], False)

    def test_static_scope_counts_are_not_migration_percentages(self):
        self.assertEqual((self.manifest["runtime_candidates"], self.manifest["configuration_only"], self.manifest["retained"]), (246, 182, 63))
        self.assertIs(self.manifest["counts_are_static_candidates"], True)
        self.assertIs(self.manifest["migration_complete"], False)

    def test_unrun_widget_hardware_and_full_version_gates_stay_open(self):
        self.assertIs(self.manifest["pressed_widget_ability_pilot"]["inventory_map_widget_business_migrated"], False)
        self.assertIs(self.manifest["held_widget_ability_pilot"]["scoreboard_widget_business_migrated"], False)
        self.assertIs(self.manifest["device_color_pilot"]["hardware_output_tested"], False)
        self.assertIs(self.manifest["accepted_batch_commit_workflow"]["full_version_accepted"], False)

    def test_each_bounded_evidence_ledger_is_counted_once(self):
        files = list((ROOT/"Acceptance").glob("*.json"))
        self.assertEqual(len(files), self.manifest["accepted_batch_commit_workflow"]["bounded_evidence_ledgers"])
