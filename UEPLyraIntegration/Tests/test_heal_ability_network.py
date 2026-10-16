"""Reject incomplete, crossed-owner or fake heal evidence without Unreal."""
import ast
import copy
from pathlib import Path
import sys
import unittest
root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"
sys.path.insert(0, str(root))
from uep_lyra_world import heal_ability_network_protocol as protocol
from uep_lyra_hud.startup import validation_module


def counts(expected):
    values = {key: expected for key in ("activations", "heals", "tasks_created", "scopes_created", "scopes_closed",
                                       "timers_created", "timers_cleared", "native_ends")}
    return dict(values, cost_rejections=0, commit_rejections=0, timer_callbacks=expected)


class HealAbilityNetwork(unittest.TestCase):
    def setUp(self):
        self.rows = []
        original = {peer: {"items": ["rifle"], "active": 0, "magazine": 12} for peer in protocol.PEERS}
        for index, (target, scenario, profile) in enumerate(protocol.PLAN):
            prepared = copy.deepcopy(original); prepared[target] = dict(items=["rifle", "heal"], active=1, magazine=1)
            after = copy.deepcopy(prepared); after[target]["magazine"] = 0
            row = dict(run_id="run", case_index=index, target=target, scenario=scenario, profile=profile,
                ability_class="native-heal", roster={peer: dict(player_id=i) for i, peer in enumerate(protocol.PEERS)},
                client_pawns={peer: "pawn-"+peer for peer in protocol.PEERS},
                client_worlds={peer: "world-"+peer for peer in protocol.PEERS},
                original_inventory=copy.deepcopy(original), prepared_inventory=prepared, after_inventory=after,
                original_health={peer: 100. for peer in protocol.PEERS}, prepared_health={peer: 75. if peer == target else 100. for peer in protocol.PEERS},
                after_health={peer: 100. for peer in protocol.PEERS}, acks={}, original_inventory_restored=True,
                native_inventory_equipment_ability_grant=True, native_source_verified=True, native_type_preserved=True,
                server_native_active_observed=True, server_ability_active_after=False, instancing_policy=1, net_execution_policy=0,
                server_python_counters=counts(int(profile == "Python")))
            for stage in ("observe", "rollback"):
                row["acks"][stage] = {}
                for i, peer in enumerate(protocol.PEERS):
                    own = peer == target
                    ack = dict(run_id="run", case_index=index, peer=peer, stage=stage,
                        player=dict(player_id=i, pawn_path="pawn-"+peer, world_token="world-"+peer, health=100., max_health=100.),
                        health_visual=dict(number=100., target=100., ratio=1.), ability_active=False,
                        inventory=copy.deepcopy(original[peer] if stage == "rollback" else after[peer]),
                        native_asc_activation_requests=int(own), native_active_observed=own, native_source_verified=own,
                        native_cancel_requested=own and scenario == "native-cancel", python_counters=counts(int(own and profile == "Python")),
                        ability_class="native-heal", native_type_preserved=True, instancing_policy=1, net_execution_policy=0,
                        montage_was_playing=own, montage_still_playing=own and scenario == "native-timer", native_elapsed_seconds=1.)
                    row["acks"][stage][peer] = ack
            self.rows.append(row)

    def test_complete_native_matrix(self):
        self.assertEqual(len(protocol.PLAN), 12)
        self.assertTrue(protocol.validate_cases(self.rows))

    def test_missing_owner_server_source_or_native_end_rejected(self):
        for field, value in (("native_source_verified", False), ("server_native_active_observed", False),
                             ("server_ability_active_after", True), ("net_execution_policy", 1), ("original_inventory_restored", False)):
            rows = copy.deepcopy(self.rows); rows[1][field] = value
            with self.assertRaises(RuntimeError):
                protocol.validate_cases(rows)
        self.rows[1]["server_python_counters"]["native_ends"] = 0
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(self.rows)

    def test_cross_owner_replay_and_fake_hud_rejected(self):
        for field, value in (("native_asc_activation_requests", 1), ("native_source_verified", True),
                             ("health_visual", dict(number=75., target=100., ratio=1.))):
            rows = copy.deepcopy(self.rows); rows[0]["acks"]["observe"]["B0"][field] = value
            with self.assertRaises(RuntimeError):
                protocol.validate_cases(rows)

    def test_shortened_native_timer_or_hidden_montage_rejected(self):
        for field, value in (("native_elapsed_seconds", .2), ("montage_still_playing", False), ("montage_was_playing", False)):
            rows = copy.deepcopy(self.rows); rows[5]["acks"]["observe"]["A"][field] = value
            with self.assertRaises(RuntimeError):
                protocol.validate_cases(rows)

    def test_native_commit_consumes_exactly_one_owner_use_without_changing_other_inventory(self):
        for peer, value in (("A", 1), ("B0", 11)):
            rows = copy.deepcopy(self.rows); rows[0]["after_inventory"][peer]["magazine"] = value
            with self.assertRaises(RuntimeError):
                protocol.validate_cases(rows)
        self.rows[0]["prepared_inventory"]["A"]["magazine"] = 2
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(self.rows)

    def test_mutated_original_inventory_or_world_rejected(self):
        self.rows[0]["acks"]["rollback"]["A"]["inventory"]["active"] = 1
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(self.rows)
        self.rows[0]["acks"]["rollback"]["A"]["inventory"]["active"] = 0
        self.rows[0]["acks"]["observe"]["A"]["player"]["world_token"] = "world-B0"
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(self.rows)

    def test_parse_exclusive_bootstrap_and_no_handler_replay(self):
        source = (root/"uep_lyra_world/heal_ability_network_validation.py").read_text(encoding="utf-8-sig")
        ast.parse(source)
        tree = ast.parse(source)
        prepare = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "prepare")
        self.assertIn("self.phase_started = time.monotonic()", ast.unparse(prepare))
        self.assertNotIn('call_function("K2_ActivateAbility"', source)
        self.assertNotIn('call_function("ReadyForActivation"', source)
        for file in (root/"uep_lyra_network.py", root/"uep_lyra_world/effect_pad_network_validation.py"):
            guard = next(node for node in reversed(ast.parse(file.read_text(encoding="utf-8-sig")).body) if isinstance(node, ast.If))
            self.assertIn("-UEPHealAbilityNetwork", ast.unparse(guard.test))
        self.assertEqual(validation_module(["-UEPHealAbilityNetwork", "-UEPLyraMultiClient"]), "uep_lyra_world.heal_ability_network_validation")
