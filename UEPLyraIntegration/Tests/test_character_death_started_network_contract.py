"""New profile's existing multiplayer regression must not claim new death ingress."""
import unittest
import test_character_ragdoll_network_contract as ragdoll_models
from test_character_death_started_contract import upgrade
from uep_lyra_characters.death_started_network_contract import validate


def reports():
    values = ragdoll_models.reports()
    for value in values.values(): upgrade(value); value["network_death_receiver_ingress_tested"] = False
    return values


class CharacterDeathStartedNetworkRegressionModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.reports)
    def test_existing_lane_shape_is_regression_not_death_acceptance(self): self.assertFalse(validate(self.reports)["network_death_receiver_ingress_tested"])
    def test_no_unexercised_network_death_claim(self): self.reports["A"]["network_death_receiver_ingress_tested"] = True; self.reject()
    def test_native_local_actor_lifetime_regression_still_required(self): self.reports["B0"]["local_ragdoll_cases"][1]["owned_actor_destroyed"] = False; self.reject()
    def test_new_profile_migration_flag_required(self): self.reports["server"]["death_started_business_migrated"] = False; self.reject()
    def test_private_selectors_only(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterDeathStartedResult=x"]), "uep_lyra_characters.death_started_validation")
        self.assertEqual(validation_module(["-UEPCharacterDeathStartedNetworkResult=x"]), "uep_lyra_characters.death_started_network_validation")
        self.assertIsNone(validation_module([])); self.assertIsNone(validation_module(["-run=Py", "-UEPCharacterDeathStartedResult=x"]))
