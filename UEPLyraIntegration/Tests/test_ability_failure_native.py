"""Modeled gates must reject fake native-producer acceptance."""
import ast
import copy
from pathlib import Path
import sys
import unittest
root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"
sys.path.insert(0, str(root))
from uep_lyra_hud import ability_failure_native_contract as contract
from uep_lyra_hud.startup import validation_module


class NativeFailureProof(unittest.TestCase):
    def setUp(self):
        state = dict(text="Already Full of Ammo", visibility=3)
        self.report = dict(status="passed", error=None, native_ability_producer_tested=True, native_source_verified=True,
            original_inventory_unchanged=True, original_health_unchanged=True, cases=[],
            shutdown=dict(active_count=0, scopes_created=2, scopes_closed=2, tickers_created=0, tickers_closed=0, errors=[]))
        self.report.update({field: False for field in contract.FALSE_CLAIMS})
        for name in contract.CASES[:2]:
            self.report["cases"].append(dict(name=name, native_asc_accepted=False, native_deliveries=1, same_class=True,
                native_opaque_text_equal=True, native_payload_owner_correct=True, native_failure_tags=["Ability.ActivateFail.MagazineFull"],
                python=copy.deepcopy(state), blueprint=copy.deepcopy(state), python_intros_delta=0))
        self.report["cases"].append(dict(name=contract.CASES[2], python=dict(state, visibility=1), blueprint=dict(state, visibility=1),
            native_delay_callbacks=1, elapsed_seconds=1.2))
        self.report["cases"].append(dict(name=contract.CASES[3], state_unchanged=True, no_pending_animations=True,
            old_python_scope_closed=True, original_proxy_inactive=True))

    def test_complete_native_gate(self):
        self.assertEqual(contract.validate(self.report)["cases"], 4)

    def test_native_source_or_unchanged_state_required(self):
        for field in ("native_source_verified", "original_inventory_unchanged", "original_health_unchanged"):
            report = copy.deepcopy(self.report); report[field] = False
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_fake_broadcast_handler_replay_or_stat_write_rejected(self):
        for field in contract.FALSE_CLAIMS:
            report = copy.deepcopy(self.report); report[field] = True
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_wrong_native_tag_owner_or_replayed_message_rejected(self):
        for field, value in (("native_failure_tags", []), ("native_payload_owner_correct", False),
                             ("native_asc_accepted", True), ("native_deliveries", 2), ("native_opaque_text_equal", False)):
            report = copy.deepcopy(self.report); report["cases"][0][field] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)

    def test_missing_animation_completion_or_scope_cleanup_rejected(self):
        self.report["cases"][2]["native_delay_callbacks"] = 0
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)
        self.report["cases"][2]["native_delay_callbacks"] = 1
        self.report["cases"][3]["original_proxy_inactive"] = False
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)

    def test_native_fixture_parse_no_broadcast_and_single_startup(self):
        source = (root/"uep_lyra_hud/ability_failure_native_validation.py").read_text(encoding="utf-8-sig")
        ast.parse(source)
        self.assertNotIn('call_function("BroadcastFailure"', source)
        self.assertNotIn("failure.received(", source)
        self.assertIn('call_function("TryActivateAbilityByClass"', source)
        base = ast.parse((root/"uep_lyra_hud/ability_failure_validation.py").read_text(encoding="utf-8-sig"))
        self.assertIn("-UEPAbilityFailureNativeProducer", ast.unparse(base.body[-1].test))
        self.assertEqual(validation_module(["-UEPAbilityFailureResult=r", "-UEPAbilityFailureNativeProducer"]),
                         "uep_lyra_hud.ability_failure_native_validation")

    def test_real_other_controller_requires_native_local_player_and_removal(self):
        row = dict(name=contract.FOREIGN_CASE, native_second_local_player=True, native_player_ids_distinct=True,
            native_asc_accepted=False, target_native_deliveries=1, first_owner_deliveries=0, first_owner_foreign_deliveries=1,
            first_owner_state_unchanged=True, first_original_bp_state_unchanged=True, native_payload_owner_correct=True)
        self.report["cases"].insert(3, row)
        self.report.update(real_foreign_controller_tested=True, native_secondary_player_removed=True,
                           secondary_inventory_health_unchanged=True, synthetic_native_slate_user_bootstrap=True, native_slate_user_index=1)
        self.assertTrue(contract.validate(self.report)["real_other_controller"])
        for field, value in (("native_second_local_player", False), ("native_player_ids_distinct", False),
                             ("first_owner_deliveries", 1), ("first_owner_foreign_deliveries", 0),
                             ("first_original_bp_state_unchanged", False)):
            report = copy.deepcopy(self.report); report["cases"][3][field] = value
            with self.assertRaises(RuntimeError):
                contract.validate(report)
        self.report["native_secondary_player_removed"] = False
        with self.assertRaises(RuntimeError):
            contract.validate(self.report)
