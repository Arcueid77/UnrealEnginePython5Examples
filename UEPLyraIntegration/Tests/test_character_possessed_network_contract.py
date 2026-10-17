"""Authority factory startup plus native owner replicas; no client event replay."""
import unittest
import test_character_inventory_wait_network_contract as wait_models
from test_character_possessed_contract import upgrade, counters
from uep_lyra_characters.possessed_network_contract import validate


def reports():
    values = wait_models.reports()
    for peer, value in values.items():
        upgrade(value)
        if peer == "server": value.update(natural_startup_possession={key: counters(controller=key) for key in ("A", "B0")}, natural_startup_controllers=dict(A="A", B0="B0"))
        else:
            value["natural_startup_possession"] = {key: 0 for key in ("python_calls", "fallback_calls", "authority_noops", "factories", "binds", "activations", "null_factories")}
            value["natural_startup_possession"].update(last_controller=None, last_proxy=None)
    return values


class CharacterPossessedNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.reports)
    def test_complete_shape_is_a_model(self): self.assertTrue(validate(self.reports)["native_authority_possession_factory"])
    def test_no_client_event_invented(self): self.reports["A"]["natural_startup_possession"]["python_calls"] = 1; self.reject()
    def test_no_client_factory(self): self.reports["B0"]["natural_startup_possession"]["factories"] = 1; self.reject()
    def test_authority_natural_factory_required(self): self.reports["server"]["natural_startup_possession"]["A"]["factories"] = 0; self.reject()
    def test_actual_authority_controller_payload(self): self.reports["server"]["natural_startup_possession"]["B0"]["last_controller"] = "A"; self.reject()
    def test_replica_result_still_required(self): self.reports["A"]["cases"][0]["replica_model"]["items"] = []; self.reject()
    def test_pending_component_replication_not_fabricated(self): self.reports["server"]["network_deferred_transitions_tested"] = True; self.reject()
    def test_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterPossessedNetworkResult=x"]), "uep_lyra_characters.possessed_network_validation")
