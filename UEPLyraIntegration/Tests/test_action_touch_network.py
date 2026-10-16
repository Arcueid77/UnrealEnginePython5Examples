"""Two-owner proof-gate models; no native or message-network claim."""
import ast
import copy
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"
sys.path.insert(0, str(root))
from uep_lyra_hud import action_touch_network_protocol as protocol
from uep_lyra_hud.startup import validation_module


class ActionTouchNetwork(unittest.TestCase):
    def setUp(self):
        self.rows = []
        roster = {peer: dict(player_id=index+100, health=100.) for index, peer in enumerate(protocol.PEERS)}
        for index, phase in enumerate(protocol.PHASES):
            packet = dict(run_id="run", phase_index=index, phase=phase, roster=roster, acks={})
            for peer in protocol.PEERS:
                target = phase[6:] if phase.startswith("owner-") else ("B0" if peer == "A" else "A")
                ack = dict(run_id="run", phase_index=index, phase=phase, peer=peer,
                    player=dict(player_id=roster[peer]["player_id"], pawn_path="pawn-"+peer, world_token="world-"+peer,
                        net_mode="Client", pawn_locally_controlled=True, health=100.),
                    synthetic_client_local_typed_message=True, message_network_replication_tested=False,
                    broadcast_player_id=roster[target]["player_id"], broadcast_instigator="pawn-"+target,
                    roots_released=4, owned_active_count=0, scopes_balanced=True, production_scopes_preserved=True, pairs={})
                for kind in ("base", "mobile"):
                    duration = 5. if phase == "baseline" else (2. if peer == "A" else (3. if phase != "owner-A" else 5.))
                    if phase in ("reconstructed", "profiles"):
                        duration = .7 if phase == "reconstructed" else 1.1
                    state = dict(duration=duration)
                    ack["pairs"][kind] = dict(same_class=True, owner_correct=True, python=copy.deepcopy(state), blueprint=copy.deepcopy(state),
                        python_messages=0 if phase == "baseline" else int(peer == "A" or phase != "owner-A"),
                        model_unchanged=True, python_scope_closed=phase == "unmounted", original_proxy_inactive=phase == "unmounted",
                        message_delta=1, old_python_scope_closed=True, old_original_proxy_inactive=True)
                packet["acks"][peer] = ack
            self.rows.append(packet)

    def test_complete_explicitly_local_two_owner_matrix(self):
        self.assertTrue(protocol.validate_phases(self.rows))

    def test_foreign_pawn_and_owner_message_crossing_rejected(self):
        self.rows[1]["acks"]["B0"]["broadcast_instigator"] = "pawn-B0"
        with self.assertRaises(RuntimeError):
            protocol.validate_phases(self.rows)

    def test_same_client_world_or_swapped_player_id_rejected(self):
        for row in self.rows:
            row["acks"]["B0"]["player"]["world_token"] = "world-A"
        with self.assertRaises(RuntimeError):
            protocol.validate_phases(self.rows)

    def test_mismatched_native_pair_or_message_replay_rejected(self):
        for field, value in (("python", dict(duration=7.)), ("python_messages", 2)):
            rows = copy.deepcopy(self.rows); rows[1]["acks"]["A"]["pairs"]["base"][field] = value
            with self.assertRaises(RuntimeError):
                protocol.validate_phases(rows)

    def test_old_listener_root_or_removed_widget_delivery_rejected(self):
        for index, field, value in ((4, "python_scope_closed", False), (4, "model_unchanged", False),
                                   (6, "old_original_proxy_inactive", False), (6, "message_delta", 2)):
            rows = copy.deepcopy(self.rows); rows[index]["acks"]["A"]["pairs"]["base"][field] = value
            with self.assertRaises(RuntimeError):
                protocol.validate_phases(rows)
        self.rows[7]["acks"]["A"]["roots_released"] = 3
        with self.assertRaises(RuntimeError):
            protocol.validate_phases(self.rows)

    def test_local_producer_must_not_be_claimed_as_message_network_replication(self):
        self.rows[1]["acks"]["A"]["message_network_replication_tested"] = True
        with self.assertRaises(RuntimeError):
            protocol.validate_phases(self.rows)

    def test_destroying_unrelated_live_production_scopes_is_not_cleanup(self):
        self.rows[7]["acks"]["A"]["production_scopes_preserved"] = False
        with self.assertRaises(RuntimeError):
            protocol.validate_phases(self.rows)

    def test_runtime_parse_and_exclusive_bootstrap(self):
        ast.parse((root/"uep_lyra_hud/action_touch_network_validation.py").read_text(encoding="utf-8-sig"))
        for file in (root/"uep_lyra_network.py", root/"uep_lyra_world/effect_pad_network_validation.py"):
            guard = next(node for node in reversed(ast.parse(file.read_text(encoding="utf-8-sig")).body) if isinstance(node, ast.If))
            self.assertIn("-UEPActionTouchNetwork", ast.unparse(guard.test))
        self.assertEqual(validation_module(["-UEPActionTouchNetwork", "-UEPLyraMultiClient"]), "uep_lyra_hud.action_touch_network_validation")
