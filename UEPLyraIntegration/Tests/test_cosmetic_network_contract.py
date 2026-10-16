"""Native network report rejection models, never runtime evidence."""
import copy
from pathlib import Path
import sys
import unittest
from test_cosmetic_contract import trial
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_characters import cosmetic_network_contract as gate


def reports():
    base = dict(status="passed", error=None, run_id="native-cosmetic-run", cases=[], policy_shutdown=dict(errors=[]))
    base.update({field: False for field in ("full_acceptance", "packaged_runtime", "animation_assets_modified", "part_arrays_written",
        "part_actors_spawned_by_python", "native_replication_bypassed", "beginplay_handler_replayed", "rng_seed_or_result_written",
        "packet_loss_tested", "travel_rejoin_tested")})
    server = dict(copy.deepcopy(base), peer="server", server_waited_for_client_process_exit=True,
        native_playing_gate=dict(native_playing_phase=True), player_ids=dict(A=1, B0=2), owners={})
    clients = {peer: dict(copy.deepcopy(base), peer=peer, player_id=index+1, observer_scopes_created=48, observer_scopes_closed=48)
        for index, peer in enumerate(gate.PEERS)}
    for peer in gate.PEERS:
        owner = dict(cases=[], random_trials=[], original_player_restored=True); source = []
        for name, parts in gate.PLAN:
            pair = dict(name=name)
            for key, profile in (("blueprint", "BlueprintFallback"), ("python", "Python")):
                value = trial(parts[2 % len(parts)], profile)
                pair[key] = value; source.append(value)
            owner["cases"].append(pair)
        for index in range(16):
            value = trial((gate.MANNY, gate.QUINN)[index//2 % 2], ("BlueprintFallback", "Python")[index % 2], "random")
            owner["random_trials"].append(value); source.append(value)
        for index, value in enumerate(source):
            position = len(server["cases"])
            value.update(position=position, target=peer, index=index, other_owner_unchanged=True)
            for view in clients.values():
                view["cases"].append(dict(position=position, target=peer, index=index, pawn=value["pawn"],
                    native_part=copy.deepcopy(value["native_part"]), native_add_delegate_seen=True,
                    native_delegate_deliveries=2, native_cleanup_restored_original_ids=True))
            value["native_part"]["actor"] = value["native_part"]["child"] = None
            server["cases"].append(copy.deepcopy(value))
        server["owners"][peer] = owner
    return server, clients


class CosmeticNetworkGate(unittest.TestCase):
    def test_full_native_network_model(self): self.assertEqual(gate.validate_reports(*reports())["authority_trials"], 48)

    def test_reject_single_viewer_or_missing_native_actor(self):
        server, clients = reports(); del clients["B0"]
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)
        server, clients = reports(); clients["B0"]["cases"][0]["native_part"]["actor"] = None
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)

    def test_reject_native_delegate_and_rollback_gaps(self):
        for field, value in (("native_add_delegate_seen", False), ("native_delegate_deliveries", 1), ("native_cleanup_restored_original_ids", False)):
            server, clients = reports(); clients["A"]["cases"][0][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError): gate.validate_reports(server, clients)

    def test_reject_wrong_owner_and_unclosed_scope(self):
        server, clients = reports(); clients["A"]["player_id"] = 2
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)
        server, clients = reports(); clients["B0"]["observer_scopes_closed"] = 47
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)

    def test_reject_replication_bypass_and_early_server_exit(self):
        server, clients = reports(); server["native_replication_bypassed"] = True
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)
        server, clients = reports(); server["server_waited_for_client_process_exit"] = False
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)

    def test_reject_modified_authority_choice(self):
        server, clients = reports(); server["cases"][0]["chosen_class"] = "foreign"
        with self.assertRaises(RuntimeError): gate.validate_reports(server, clients)
