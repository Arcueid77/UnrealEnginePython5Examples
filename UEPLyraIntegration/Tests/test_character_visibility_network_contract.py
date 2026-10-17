"""Native startup visibility plus real inventory replicas, not network pixels."""
import unittest
import test_character_possessed_network_contract as possession_models
from test_character_visibility_contract import upgrade, evidence
from uep_lyra_characters.visibility_network_contract import validate


def reports():
    values = possession_models.reports()
    for peer, value in values.items():
        upgrade(value); value["network_visibility_repeat_destroy_matrix_tested"] = False
        if peer == "server": value["natural_startup_visibility"] = {key: dict(counters=evidence(actor=key), actor=key, hidden=False) for key in ("A", "B0")}
        else: value["natural_startup_visibility"] = dict(counters=evidence(actor=peer), actor=peer, hidden=False)
    return values


class CharacterVisibilityNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.reports)
    def test_complete_shape_is_a_model(self): self.assertTrue(validate(self.reports)["native_network_startup_visibility"])
    def test_owner_must_be_shown(self): self.reports["A"]["natural_startup_visibility"]["hidden"] = True; self.reject()
    def test_both_authority_pawns_show(self): self.reports["server"]["natural_startup_visibility"]["B0"]["counters"]["show_calls"] = 0; self.reject()
    def test_native_initstate_callback_required_on_client(self): self.reports["B0"]["natural_startup_visibility"]["counters"]["python_calls"] = 0; self.reject()
    def test_visibility_repeat_network_not_overclaimed(self): self.reports["server"]["network_visibility_repeat_destroy_matrix_tested"] = True; self.reject()
    def test_pixel_claim_rejected(self): self.reports["A"]["visibility_physical_pixels_tested"] = True; self.reject()
    def test_inventory_replica_regression_still_required(self): self.reports["A"]["cases"][0]["replica_model"]["items"] = []; self.reject()
    def test_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterVisibilityNetworkResult=x"]), "uep_lyra_characters.visibility_network_validation")
