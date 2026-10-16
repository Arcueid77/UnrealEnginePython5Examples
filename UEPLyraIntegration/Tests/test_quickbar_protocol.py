import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_quickbar_protocol import validate_quickbar, validate_scopes


class QuickBarNetworkTests(unittest.TestCase):
    def setUp(self):
        self.ack = {"player": {"controller_path": "controller", "pawn_path": "pawn", "world_token": "world"}}
        self.value = {"controller": "controller", "pawn": "pawn", "world_token": "world", "slots": [],
                      "synthetic_local_messages": False, "native_inventory_properties_written": False,
                      "external_named_query_migrated": True, "bp_initialization_parity_tested": False,
                      "baseline_epoch_policy": "same-production-widget -> same BP baseline; native owner/remount/resume; no state copying",
                      "reused_baseline_epochs": 0}
        for index in range(3):
            state = {"index": index, "empty": index != 0, "selected": index == 0, "numeric": 60.0 if index == 0 else 0.0}
            self.value["slots"].append({"production_widget": True, "widget": "slot"+str(index), "class": "W_QuickBarSlot_C",
                                        "profile": "Python", "python": state, "blueprint": dict(state), "automatic_ticks": 6, "named_query_calls": 2,
                                        "native_item": "pistol" if index == 0 else None, "native_total": 60 if index == 0 else None,
                                        "native_active": index == 0})
        self.final = {"active_count": 0, "scopes_created": 12, "scopes_closed": 12, "errors": [],
                      "pool_lifetime": {"active_count": 0, "ticker_active": False, "registered": 3, "unregistered": 3, "errors": []}}

    def test_native_bounded_checkpoint_passes(self):
        validate_quickbar(self.value, self.ack)
        validate_scopes(self.final, "A")

    def test_foreign_owner_world_or_pawn_rejected(self):
        for key in ("controller", "pawn", "world_token"):
            value = copy.deepcopy(self.value)
            value[key] = "foreign"
            with self.assertRaises(RuntimeError):
                validate_quickbar(value, self.ack)

    def test_fake_complete_migration_or_synthetic_producer_claim_rejected(self):
        for flag in ("bp_initialization_parity_tested", "synthetic_local_messages", "native_inventory_properties_written"):
            value = copy.deepcopy(self.value)
            value[flag] = True
            with self.assertRaises(RuntimeError):
                validate_quickbar(value, self.ack)
        value = copy.deepcopy(self.value)
        value["external_named_query_migrated"] = False
        with self.assertRaises(RuntimeError):
            validate_quickbar(value, self.ack)

    def test_missing_duplicate_or_foreign_profile_slot_rejected(self):
        for mutation in (lambda r: r["slots"].pop(), lambda r: r["slots"][1].update(widget="slot0"),
                         lambda r: r["slots"][0].update(profile="BlueprintFallback"),
                         lambda r: r["slots"][0].update(automatic_ticks=True)):
            value = copy.deepcopy(self.value)
            mutation(value)
            with self.assertRaises(RuntimeError):
                validate_quickbar(value, self.ack)

    def test_native_ammo_selected_or_empty_mismatch_rejected(self):
        for mutation in (lambda r: r["slots"][0].update(native_total=59),
                         lambda r: r["slots"][0].update(native_active=False),
                         lambda r: r["slots"][1]["python"].update(empty=False),
                         lambda r: r["slots"][0]["python"].update(numeric=float("nan"))):
            value = copy.deepcopy(self.value)
            mutation(value)
            with self.assertRaises(RuntimeError):
                validate_quickbar(value, self.ack)

    def test_scope_pool_or_dedicated_ui_residue_rejected(self):
        for mutation in (lambda r: r.update(active_count=1), lambda r: r.update(scopes_closed=11),
                         lambda r: r["pool_lifetime"].update(ticker_active=True)):
            final = copy.deepcopy(self.final)
            mutation(final)
            with self.assertRaises(RuntimeError):
                validate_scopes(final, "A")
        with self.assertRaises(RuntimeError):
            validate_scopes(self.final, "server")


if __name__ == "__main__":
    unittest.main()
