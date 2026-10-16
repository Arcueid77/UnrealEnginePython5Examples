import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_respawn_protocol import validate_respawn, validate_scopes, foreign_delivery_evidence


class RespawnForeignDeliveryEvidence(unittest.TestCase):
    def test_synchronous_pair_is_separate_from_later_native_foreign_delivery(self):
        self.assertEqual(foreign_delivery_evidence(8, 11, 2), {"foreign_rejections": 2,
            "total_foreign_rejections": 3, "additional_foreign_rejections": 1})

    def test_missing_pair_cannot_be_replaced_by_later_native_messages(self):
        for before, current, pair in ((8, 11, 1), (8, 9, 2), (8, 12, 3), (8, True, 2)):
            with self.assertRaises(RuntimeError):
                foreign_delivery_evidence(before, current, pair)


class RespawnNetworkGateTests(unittest.TestCase):
    def setUp(self):
        self.ack = {"phase": "join_b", "player": {"controller_path": "controller", "pawn_path": "pawn", "world_token": "world"}}
        state = {"duration": 3.0, "start": 1.0, "respawning": False, "visibility": 1,
                 "numeric": 0.0, "text": "0", "glow": 0.01, "fill": 0.01, "timer_active": False}
        self.value = {"production_widget": True, "class": "W_RespawnTimer_C", "profile": "Python",
                      "controller": "controller", "pawn": "pawn", "world_token": "world", "phase": "join_b", "completed": True,
                      "synthetic_local_messages": True, "native_respawn_producer_tested": False, "replicated_message_tested": False,
                      "fixture_event_invoked": False, "owner_deliveries": 1, "foreign_rejections": 2,
                      "foreign_instigator_kind": "owning-pawn-not-playerstate", "comparisons": 8, "visible_comparisons": 3,
                      "python": state, "blueprint": copy.deepcopy(state)}
        self.final = {"active_count": 0, "scopes_created": 3, "scopes_closed": 3, "errors": [],
                      "pool_lifetime": {"active_count": 0, "ticker_active": False, "registered": 3, "unregistered": 3, "errors": []}}

    def test_bounded_checkpoint_and_dedicated_no_ui_pass(self):
        validate_respawn(self.value, self.ack)
        validate_scopes(self.final, "A")
        server = copy.deepcopy(self.final)
        server.update(scopes_created=0, scopes_closed=0)
        validate_scopes(server, "server")

    def test_foreign_owner_world_phase_class_and_profile_rejected(self):
        for key in ("controller", "pawn", "world_token", "phase", "class", "profile"):
            value = copy.deepcopy(self.value)
            value[key] = "foreign"
            with self.assertRaises(RuntimeError):
                validate_respawn(value, self.ack)

    def test_delivery_counts_must_be_real_exact_integers(self):
        for key, replacement in (("owner_deliveries", 0), ("owner_deliveries", 2), ("owner_deliveries", True),
                                 ("foreign_rejections", 1), ("foreign_rejections", True), ("comparisons", 1),
                                 ("visible_comparisons", 0), ("visible_comparisons", True)):
            value = copy.deepcopy(self.value)
            value[key] = replacement
            with self.assertRaises(RuntimeError):
                validate_respawn(value, self.ack)

    def test_native_replication_or_manual_event_claim_rejected(self):
        for key in ("native_respawn_producer_tested", "replicated_message_tested", "fixture_event_invoked"):
            value = copy.deepcopy(self.value)
            value[key] = True
            with self.assertRaises(RuntimeError):
                validate_respawn(value, self.ack)

    def test_visual_timer_or_nonfinite_values_rejected(self):
        for key, replacement in (("fill", 0.5), ("timer_active", True), ("respawning", True), ("visibility", 0),
                                 ("start", float("inf")), ("glow", float("nan"))):
            value = copy.deepcopy(self.value)
            value["python"][key] = replacement
            if key in ("start", "glow"):
                value["blueprint"][key] = replacement
            with self.assertRaises(RuntimeError):
                validate_respawn(value, self.ack)

    def test_scopes_pool_residue_and_server_ui_rejected(self):
        for key, replacement in (("active_count", 1), ("scopes_closed", 2), ("errors", ["failure"])):
            final = copy.deepcopy(self.final)
            final[key] = replacement
            with self.assertRaises(RuntimeError):
                validate_scopes(final, "A")
        for key, replacement in (("active_count", 1), ("ticker_active", True), ("unregistered", 2), ("errors", ["failure"])):
            final = copy.deepcopy(self.final)
            final["pool_lifetime"][key] = replacement
            with self.assertRaises(RuntimeError):
                validate_scopes(final, "A")
        with self.assertRaises(RuntimeError):
            validate_scopes(self.final, "server")


if __name__ == "__main__":
    unittest.main()
