"""Role/Profile isolation and honest legacy RepNotify coverage boundary."""
import unittest
from test_character_team_observer_network_contract import reports as observer_reports
from test_character_legacy_player_info_contract import upgrade
from uep_lyra_characters.legacy_player_info_network_contract import validate


class CharacterLegacyPlayerInfoNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = [upgrade(value) for value in observer_reports()]
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(*self.reports)
    def test_complete_shape_only_model(self): self.assertEqual(validate(*self.reports)["typed_bp_legacy_calls"], 36)
    def test_no_repnotify_delivery_claim_on_either_client(self): self.reports[2]["real_legacy_repnotify_ingress_tested"] = True; self.reject()
    def test_server_cannot_fake_client_mode(self): self.reports[0]["native_net_mode"] = "Client"; self.reject()
    def test_foreign_identity_role(self): self.reports[1]["cases"][1]["native_role"] = 2; self.reject()
    def test_foreign_actor_no_local_device_output(self): self.reports[1]["cases"][1]["native_device_properties_created"] = 1; self.reject()
    def test_server_last_cleanup_order(self): self.reports[0]["all_cleanup_frozen_before_release"] = False; self.reject()
    def test_proxy_set_preserved_in_each_world(self): self.reports[2]["cleanup"]["original_active_proxies_preserved"] = False; self.reject()
    def test_network_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterLegacyNetworkResult=x"]), "uep_lyra_characters.legacy_player_info_network_validation")
