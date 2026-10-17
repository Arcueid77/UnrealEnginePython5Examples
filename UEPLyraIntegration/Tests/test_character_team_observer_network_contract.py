"""Two real Pawn identities, opposite profiles and actual server/client ownership."""
import unittest
from test_character_team_observer_contract import row, report
from uep_lyra_characters.team_observer_network_contract import PLAN, validate


def reports():
    result = []
    for peer in ("server", "A", "B0"):
        value = report(); authority = peer == "server"
        value.update(peer=peer, run_id="observer-model", player_ids=dict(A=21, B0=22), player_id=21 if peer == "A" else 22,
            native_net_mode="DedicatedServer" if authority else "Client", cases=[])
        for name, target, calls, profile in PLAN:
            item = row(profile, calls, True, target == peer); item.update(name=name, target=target, calls=calls, native_role=3 if authority else (2 if target == peer else 1)); value["cases"].append(item)
        value["cleanup"].update(native_observation_markers=0 if authority else 24, device_roots_created=0 if authority else 30,
            device_roots_released=0 if authority else 30, native_latest_cancelled_proxies_retained=0)
        if authority: value.update(server_waited_for_client_process_exit=True, all_cleanup_frozen_before_release=True)
        result.append(value)
    return result


class CharacterTeamObserverNetworkReportModels(unittest.TestCase):
    def setUp(self): self.reports = reports()
    def reject(self):
        with self.assertRaises((AssertionError, RuntimeError, ValueError)): validate(*self.reports)
    def test_complete_shape_only_model_not_runtime(self): self.assertEqual(validate(*self.reports)["native_observer_callbacks"], 36)
    def test_missing_second_native_client_rejected(self): self.reports[2]["cases"] = []; self.reject()
    def test_actual_mode_not_only_peer_label(self): self.reports[0]["native_net_mode"] = "Client"; self.reject()
    def test_local_foreign_actor_roles_checked(self): self.reports[1]["cases"][1]["native_role"] = 2; self.reject()
    def test_server_cannot_create_device_subsystem(self): self.reports[0]["cleanup"]["device_roots_created"] = 1; self.reject()
    def test_foreign_pawn_cannot_be_valid_local_device_user(self): self.reports[1]["cases"][1]["native_device_properties_created"] = 1; self.reject()
    def test_owned_async_tasks_cancel_and_deregister_everywhere(self): self.reports[2]["cleanup"]["owned_observers_cancelled_and_deregistered"] = False; self.reject()
    def test_no_older_proxy_retention_in_any_world(self): self.reports[1]["cleanup"]["older_owned_proxies_collected"] = False; self.reject()
    def test_no_latest_return_retained_on_any_peer(self): self.reports[2]["cleanup"]["native_latest_cancelled_proxies_retained"] = 1; self.reject()
    def test_network_gc_request_is_not_completed_gc(self): self.reports[0]["cases"][0]["native_collection_checked_after_engine_ticks"] = False; self.reject()
    def test_cleanup_frozen_before_release(self): self.reports[0]["all_cleanup_frozen_before_release"] = False; self.reject()
    def test_server_last_actual_process_order(self): self.reports[0]["server_waited_for_client_process_exit"] = False; self.reject()
    def test_native_initial_factory_not_team_replication_claim(self): self.reports[1]["replicated_team_changes_tested"] = True; self.reject()
    def test_network_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterObserverNetworkResult=x"]), "uep_lyra_characters.team_observer_network_validation")
