"""Immediate branch claims require real loadout and deferred-control evidence."""
import unittest
from test_character_initial_inventory_contract import report as loadout_report
from uep_lyra_characters.inventory_ready_contract import counts, validate


def upgrade(value):
    value.update(experience_callback_manually_called_by_typed_bp=False, native_experience_factory_signal_tested=True, experience_ready_factory_migrated=False,
        pending_inventory_wait_migrated=False, immediate_inventory_ready_branch_migrated=True, caller_roots=dict(created=1, released=1),
        owned_experience_proxies_created=14, owned_experience_proxies_collected=True)
    for item in value["cases"]:
        py = item["profile"] == "Python"; item["readiness_counters"] = counts(py=int(py), fallback=int(not py), immediate=int(py)); item["real_experience_factory_signal"] = True
    return value


def report():
    value = upgrade(loadout_report()); value["natural_startup_readiness"] = counts(py=1, immediate=1)
    value["deferred_original_cases"] = [dict(profile=profile, readiness_counters=counts(py=int(profile == "Python"), fallback=int(profile != "Python"), pending=int(profile == "Python")),
        no_inventory_grant_while_controller_missing=True, owned_actor_destroyed=True, no_callbacks_or_grants_after_destroy_and_engine_ticks=True,
        original_live_proxies_preserved=True, owned_startup_proxies_collected=True, actor_was_not_rooted=True) for profile in ("BlueprintFallback", "Python")]
    return value


class CharacterInventoryReadyReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(self.report)
    def test_complete_shape_is_only_a_model(self): self.assertEqual(validate(self.report)["native_experience_requests"], 14)
    def test_actual_natural_delivery_not_only_manual_success(self): self.report["natural_startup_readiness"]["python_calls"] = 0; self.reject()
    def test_no_claim_deferred_wait_has_migrated(self): self.report["pending_inventory_wait_migrated"] = True; self.reject()
    def test_no_claim_native_factory_has_migrated(self): self.report["experience_ready_factory_migrated"] = True; self.reject()
    def test_ready_branch_must_really_forward(self): self.report["cases"][1]["readiness_counters"]["immediate_grants"] = 0; self.reject()
    def test_native_inventory_result_still_required(self): self.report["cases"][3]["native_model"]["items"] = []; self.reject()
    def test_missing_controller_never_grants_early(self): self.report["deferred_original_cases"][1]["no_inventory_grant_while_controller_missing"] = False; self.reject()
    def test_destroyed_pending_actor_cannot_receive_late_grant(self): self.report["deferred_original_cases"][1]["no_callbacks_or_grants_after_destroy_and_engine_ticks"] = False; self.reject()
    def test_caller_root_released(self): self.report["caller_roots"]["released"] = 0; self.reject()
    def test_no_owned_experience_proxy_gc_leak(self): self.report["owned_experience_proxies_collected"] = False; self.reject()
    def test_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterReadyResult=x"]), "uep_lyra_characters.inventory_ready_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterReadyResult=x"]))
