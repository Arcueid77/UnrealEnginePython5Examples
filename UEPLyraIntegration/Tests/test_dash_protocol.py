import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_dash_protocol import validate_dash, validate_scopes


class DashNetworkGateTests(unittest.TestCase):
    def setUp(self):
        self.ack = {"phase": "join_b", "player": {"controller_path": "controller", "pawn_path": "pawn", "world_token": "world"}}
        state = {"duration": 1.25, "start": 1.0, "charging": False, "visibility": 3, "glow": 1.0, "fill": 1.0}
        self.value = {"production_widget": True, "widget": "production", "class": "W_DashCooldown_C", "profile": "Python",
                      "controller": "controller", "pawn": "pawn", "world_token": "world", "phase": "join_b", "completed": True,
                      "synthetic_local_messages": True, "native_dash_producer_tested": False, "replicated_duration_message_tested": False,
                      "python_tick_called_by_probe": False, "foreign_instigator_kind": "owning-controller-not-pawn",
                      "owner_deliveries": 1, "foreign_rejections": 1, "automatic_tick_delta": 8, "comparisons": 6,
                      "visible_comparisons": 3, "python": state, "blueprint": copy.deepcopy(state)}
        self.final = {"active_count": 0, "scopes_created": 6, "scopes_closed": 6, "health_binds": 3, "health_unbinds": 3, "errors": []}
        self.pool = {"source": "read-only-native-UIExtension-active-entry-membership", "active_count": 0,
                     "ticker_active": False, "registered": 3, "unregistered": 3, "errors": []}
        self.final["pool_lifetime"] = self.pool

    def test_bounded_checkpoint_passes(self):
        validate_dash(self.value, self.ack)
        validate_scopes(self.final, "A")

    def test_foreign_owner_pawn_world_or_phase_rejected(self):
        for key in ("controller", "pawn", "world_token", "phase"):
            value = copy.deepcopy(self.value)
            value[key] = "foreign"
            with self.assertRaises(RuntimeError):
                validate_dash(value, self.ack)

    def test_missing_or_duplicate_delivery_tick_and_charging_proof_rejected(self):
        for key, replacement in (("owner_deliveries", 0), ("owner_deliveries", 2), ("owner_deliveries", True),
                                 ("foreign_rejections", 0), ("automatic_tick_delta", 1), ("visible_comparisons", 0)):
            value = copy.deepcopy(self.value)
            value[key] = replacement
            with self.assertRaises(RuntimeError):
                validate_dash(value, self.ack)

    def test_unsupported_native_replication_or_manual_tick_claim_rejected(self):
        for key in ("native_dash_producer_tested", "replicated_duration_message_tested", "python_tick_called_by_probe"):
            value = copy.deepcopy(self.value)
            value[key] = True
            with self.assertRaises(RuntimeError):
                validate_dash(value, self.ack)

    def test_final_visual_or_nonfinite_start_rejected(self):
        for key, replacement in (("fill", 0.5), ("charging", True), ("visibility", 1), ("start", float("inf"))):
            value = copy.deepcopy(self.value)
            value["python"][key] = replacement
            if key == "start":
                value["blueprint"][key] = replacement
            with self.assertRaises(RuntimeError):
                validate_dash(value, self.ack)

    def test_scope_and_health_cleanup_server_ownership_rejected(self):
        for key, replacement in (("active_count", 1), ("scopes_closed", 5), ("health_unbinds", 2), ("errors", ["failure"])):
            final = dict(self.final, **{key: replacement})
            with self.assertRaises(RuntimeError):
                validate_scopes(final, "A")
        with self.assertRaises(RuntimeError):
            validate_scopes(self.final, "server")
        validate_scopes({"active_count": 0, "scopes_created": 0, "scopes_closed": 0, "health_binds": 0, "health_unbinds": 0, "errors": [], "pool_lifetime": self.pool}, "server")

    def test_pool_sampler_residue_rejected(self):
        for key, value in (("active_count", 1), ("ticker_active", True), ("unregistered", 2), ("errors", ["failure"])):
            final = copy.deepcopy(self.final)
            final["pool_lifetime"][key] = value
            with self.assertRaises(RuntimeError):
                validate_scopes(final, "A")


if __name__ == "__main__":
    unittest.main()
