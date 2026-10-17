"""Actual network startup entry and old ownership/replication gates."""
import unittest
import test_character_visibility_network_contract as visibility_models
from test_character_begin_play_contract import upgrade, counters
from uep_lyra_characters.begin_play_network_contract import validate


def reports():
    values = visibility_models.reports()
    for peer, value in values.items():
        upgrade(value); value["fixture_cdo_profile_modified_on_network"] = False
        value["natural_startup_begin_play"] = {key: counters() for key in ("A", "B0")} if peer == "server" else counters()
    return values


class CharacterBeginPlayNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.reports)
    def test_complete_shape_is_model(self): self.assertTrue(validate(self.reports)["native_network_begin_play"])
    def test_natural_owner_entry_required(self): self.reports["A"]["natural_startup_begin_play"]["python_calls"] = 0; self.reject()
    def test_both_authority_entries_required(self): self.reports["server"]["natural_startup_begin_play"]["B0"]["register_calls"] = 0; self.reject()
    def test_no_network_cdo_mutation(self): self.reports["server"]["fixture_cdo_profile_modified_on_network"] = True; self.reject()
    def test_old_replication_still_required(self): self.reports["A"]["cases"][0]["replica_model"]["items"] = []; self.reject()
