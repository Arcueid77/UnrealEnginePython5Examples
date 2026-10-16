"""Artificial checkpoint contract tests, not multiplayer proof."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_ability_failure_protocol import validate_failure, validate_scopes


class FailureNetworkContractTests(unittest.TestCase):
    def setUp(self):
        self.ack = {"peer": "A", "phase": "join_b", "player": {"controller_path": "PC_A", "pawn_path": "Pawn_A", "world_token": "World1"}}
        self.value = {"production_widget": True, "class": "W_AbilityFailureFeedback_C", "profile": "Python",
            "controller": "PC_A", "pawn": "Pawn_A", "world_token": "World1", "phase": "join_b", "completed": True,
            "synthetic_local_messages": True, "native_ability_producer_tested": False, "replicated_failure_message_tested": False,
            "fixture_event_invoked": False, "timer_clock": "native-retriggerable-delay", "foreign_controller_kind": "null-controller",
            "comparisons": 30, "visible_comparisons": 10, "owner_deliveries": 1, "foreign_rejections": 1,
            "expected_synthetic_reason": "UEP A join_b", "python": {"text": "UEP A join_b", "visibility": 1},
            "blueprint": {"text": "UEP A join_b", "visibility": 1}}

    def test_completed_local_checkpoint_is_valid(self):
        validate_failure(self.value, self.ack)

    def test_foreign_owner_or_old_world_is_rejected(self):
        for key, value in (("controller", "PC_B"), ("pawn", "Pawn_B"), ("world_token", "OldWorld")):
            changed = copy.deepcopy(self.value)
            changed[key] = value
            with self.assertRaises(RuntimeError):
                validate_failure(changed, self.ack)

    def test_no_visible_comparison_or_no_filter_is_rejected(self):
        for key in ("visible_comparisons", "foreign_rejections", "owner_deliveries"):
            changed = copy.deepcopy(self.value)
            changed[key] = 0
            with self.assertRaises(RuntimeError):
                validate_failure(changed, self.ack)

    def test_local_fixture_cannot_claim_native_producer_or_replication(self):
        for key in ("native_ability_producer_tested", "replicated_failure_message_tested", "fixture_event_invoked"):
            changed = copy.deepcopy(self.value)
            changed[key] = True
            with self.assertRaises(RuntimeError):
                validate_failure(changed, self.ack)

    def test_ui_mismatch_or_not_finished_is_rejected(self):
        self.value["blueprint"]["visibility"] = 3
        with self.assertRaises(RuntimeError):
            validate_failure(self.value, self.ack)

    def test_server_has_no_ui_and_client_scopes_must_close(self):
        empty = {"active_count": 0, "scopes_created": 0, "scopes_closed": 0, "errors": []}
        validate_scopes(empty, "server")
        with self.assertRaises(RuntimeError):
            validate_scopes(empty, "A")
        owned = {"active_count": 0, "scopes_created": 6, "scopes_closed": 6, "errors": []}
        validate_scopes(owned, "A")
        owned["scopes_closed"] = 5
        with self.assertRaises(RuntimeError):
            validate_scopes(owned, "A")


if __name__ == "__main__":
    unittest.main()
