"""Factory decisions and original native lifetime in each real network world."""
import unittest
from test_character_team_observer_network_contract import reports as observer_reports
from test_character_team_listener_contract import upgrade
from uep_lyra_characters.team_listener_network_contract import validate


class CharacterTeamListenerNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = [upgrade(value) for value in observer_reports()]
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(*self.reports)
    def test_complete_shape_is_model_not_native_acceptance(self): self.assertEqual(validate(*self.reports)["native_observer_callbacks"], 36)
    def test_foreign_actor_also_runs_selected_factory(self): self.reports[1]["cases"][1]["listener_counters"]["fallback_calls"] = 0; self.reject()
    def test_authority_natural_listener_must_run(self): self.reports[0]["natural_startup_python_dispatch"]["owner"]["listener_factory_counters"]["activations"] = 0; self.reject()
    def test_native_callback_still_required_on_both_clients(self): self.reports[2]["cases"][0]["counters"]["python_calls"] = 0; self.reject()
    def test_no_server_device_output_invented_by_python(self): self.reports[0]["cleanup"]["device_roots_created"] = 1; self.reject()
    def test_all_owned_observers_collect_before_release(self): self.reports[2]["cleanup"]["native_latest_cancelled_proxies_retained"] = 1; self.reject()
    def test_server_last_still_required(self): self.reports[0]["server_waited_for_client_process_exit"] = False; self.reject()
    def test_private_network_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterListenerNetworkResult=x"]), "uep_lyra_characters.team_listener_network_validation")
