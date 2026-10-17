"""Replica report models under the new profile; no deferred-network overclaim."""
import unittest
import test_character_inventory_ready_network_contract as ready_models
from uep_lyra_characters.inventory_wait_network_contract import validate


def reports():
    values = ready_models.reports()
    for value in values.values():
        value.update(pending_inventory_wait_migrated=True, native_wait_backend="DelayUntilNextTick",
            python_wait_ticker_registered=False, network_deferred_transitions_tested=False)
    return values


class CharacterInventoryWaitNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(self.reports)
    def test_complete_shape_only_a_model(self): self.assertTrue(validate(self.reports)["pending_wait_profile_active"])
    def test_network_deferred_transitions_not_fabricated(self): self.reports["server"]["network_deferred_transitions_tested"] = True; self.reject()
    def test_client_cannot_overclaim_deferred_network(self): self.reports["A"]["network_deferred_transitions_tested"] = True; self.reject()
    def test_profile_must_really_use_new_wait(self): self.reports["server"]["pending_inventory_wait_migrated"] = False; self.reject()
    def test_no_python_wait_ticker(self): self.reports["B0"]["python_wait_ticker_registered"] = True; self.reject()
    def test_native_latent_backend(self): self.reports["A"]["native_wait_backend"] = "mock"; self.reject()
    def test_owned_native_experience_proxies_must_collect(self): self.reports["server"]["owned_experience_proxies_collected"] = False; self.reject()
    def test_native_replica_required(self): self.reports["A"]["cases"][0]["replica_model"]["items"] = []; self.reject()
    def test_no_invented_client_startup_ready(self): self.reports["B0"]["natural_startup_readiness"]["python_calls"] = 1; self.reject()
    def test_natural_authority_required(self): self.reports["server"]["natural_startup_readiness"]["A"]["python_calls"] = 0; self.reject()
    def test_ready_count_cannot_hide_unrestored_inventory(self): self.reports["server"]["restore_frozen_before_release"] = False; self.reject()
    def test_private_selectors(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterWaitResult=x"]), "uep_lyra_characters.inventory_wait_validation")
        self.assertEqual(validation_module(["-UEPCharacterWaitNetworkResult=x"]), "uep_lyra_characters.inventory_wait_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterWaitResult=x"]))
