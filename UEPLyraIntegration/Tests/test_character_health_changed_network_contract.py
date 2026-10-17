"""Two native clients, real replica delegates and authority-only damage sense."""
import copy
import unittest
from test_character_health_changed_contract import case, report
from uep_lyra_characters.health_changed_network_contract import PLAN, validate


def reports():
    values = []
    for peer in ("server", "A", "B0"):
        value = report(); authority = peer == "server"
        value.update(peer=peer, run_id="health-model", player_ids=dict(A=41, B0=42), network_acceptance=True,
            native_net_mode="DedicatedServer" if authority else "Client", cases=[case(*entry, authority=authority, keys=("A", "B0", "AI"), local=peer) for entry in PLAN])
        value["cleanup"]["observer"].update(bindings_created=4 if authority else 3, bindings_closed=4 if authority else 3,
            health_deliveries=30, sense_deliveries=4 if authority else 0)
        if authority: value.update(server_waited_for_client_process_exit=True, all_cleanup_frozen_before_release=True)
        else: value["player_id"] = value["player_ids"][peer]
        values.append(value)
    return values


class CharacterHealthChangedNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(*self.reports)
    def test_complete_native_shape_passes_model_not_runtime(self): self.assertEqual(validate(*self.reports)["client_native_health_observations"], 28)
    def test_no_missing_second_client(self): self.reports[2]["cases"] = []; self.reject()
    def test_actual_distinct_player_ids_required(self): self.reports[0]["player_ids"]["B0"] = 41; self.reject()
    def test_client_cannot_produce_gas_mutation(self): self.reports[1]["cases"][0]["native_gas_producer_called"] = True; self.reject()
    def test_client_must_not_invent_effect_context_source(self): self.reports[1]["cases"][0]["actors"]["A"]["delegates"][0]["instigator"] = "source-state"; self.reject()
    def test_client_guard_is_authority_not_playerstate_cast(self):
        stats = self.reports[1]["cases"][1]["actors"]["A"]["counters"]; stats.update(authority_noops=0, instigator_noops=1); self.reject()
    def test_local_and_foreign_native_roles_required(self): self.reports[1]["cases"][0]["actors"]["B0"]["native_role"] = 2; self.reject()
    def test_server_must_not_exit_before_clients(self): self.reports[0]["server_waited_for_client_process_exit"] = False; self.reject()
    def test_no_cleanup_after_controller_disconnect(self): self.reports[0]["all_cleanup_frozen_before_release"] = False; self.reject()
    def test_clients_must_have_replication_not_file_delivered_state(self): self.reports[2]["gameplay_state_delivered_by_files"] = True; self.reject()
    def test_missing_restore_replica_delegate_rejected(self): self.reports[2]["cleanup"]["observer"]["health_deliveries"] = 33; self.reject()
    def test_client_native_ai_stimulus_forbidden(self): self.reports[1]["cases"][6]["native_ai_perception_memory"] = True; self.reject()
    def test_health_network_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterHealthNetworkResult=x"]), "uep_lyra_characters.health_changed_network_validation")
