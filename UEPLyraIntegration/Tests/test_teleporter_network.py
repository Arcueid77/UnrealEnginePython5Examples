"""Network proof-gate negatives; model ACKs never count as runtime tests."""
import ast
import copy
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"
sys.path.insert(0, str(root))
from uep_lyra_world import teleporter_network_protocol as protocol
from uep_lyra_hud.startup import validation_module


class TeleporterNetworkProtocol(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for index, (target, scenario, profile) in enumerate(protocol.PLAN):
            roster = {peer: dict(player_id=peer, pawn_path="server-"+peer, health=100.) for peer in protocol.PEERS}
            positions = {peer: [0., 0., 2000.] if peer == target else [-1000., 0., 2000.] for peer in protocol.PEERS}
            restore = {peer: [-1000., 0., 2000.] for peer in protocol.PEERS}
            launched = scenario != "no-launch"
            requested = [0., 1250., 0.] if launched else [0.]*3
            row = dict(run_id="run", case_index=index, target=target, scenario=scenario, profile=profile, roster=roster,
                client_pawns={peer: "client-"+peer for peer in protocol.PEERS},
                client_worlds={peer: "world-"+peer for peer in protocol.PEERS}, positions=positions,
                restore_positions=restore, expected_location=[0., 1800., 2000.], forward=[0., 1., 0.],
                expected_requested=requested, physical_events=["end", "begin"], fixture_scope_closed=True,
                portals_destroyed=True, portal_replicates=False, position_error=0., rotation_error=0., control_error=0.,
                destination_selected=True, receiving_pawn=True, receiver_box_destroyed=True,
                launch_event_count=int(launched), other_owner_launch_events=0,
                launch_event=dict(pawn="server-"+target, xy_override=True, z_override=True, requested=requested) if launched else None,
                server_motion=dict(location=[0., 1900. if launched else 1800., 1998.], velocity=requested, movement_mode=3),
                python_counters=dict(begins=1, destinations=1, character_entries=1, teleports=1, pawn_audio=1, rotations=1, launches=int(launched)),
                acks={})
            for stage in ("armed", "moving", "restored"):
                row["acks"][stage] = {}
                for peer in protocol.PEERS:
                    moving = stage == "moving" and peer == target
                    motion = row["server_motion"] if moving else dict(location=(restore if stage == "restored" else positions)[peer],
                        velocity=[0.]*3, movement_mode=0)
                    row["acks"][stage][peer] = dict(run_id="run", case_index=index, stage=stage, peer=peer,
                        motion=copy.deepcopy(motion), player=dict(player_id=peer, pawn_path="client-"+peer,
                            world_token="world-"+peer, health=100., max_health=100.), health_visual=dict(number=100., target=100., ratio=1.))
            self.rows.append(row)

    def test_complete_two_owner_matrix(self):
        self.assertEqual(len(self.rows), 12)
        self.assertTrue(protocol.validate_cases(self.rows))

    def test_actual_client_entry_position_not_server_data_required(self):
        self.rows[0]["acks"]["moving"]["A"]["motion"]["location"] = [0., 0., 2000.]
        with self.assertRaisesRegex(RuntimeError, "remained at entry"):
            protocol.validate_cases(self.rows)

    def test_wrong_owner_world_hud_and_health_rejected(self):
        for field, value in (("player_id", "B0"), ("pawn_path", "server-A"), ("world_token", "old-world"), ("health", 75.)):
            rows = copy.deepcopy(self.rows); rows[0]["acks"]["moving"]["A"]["player"][field] = value
            with self.assertRaises(RuntimeError):
                protocol.validate_cases(rows)
        self.rows[0]["acks"]["moving"]["A"]["health_visual"]["ratio"] = .75
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(self.rows)

    def test_other_owner_movement_or_duplicate_native_launch_rejected(self):
        self.rows[0]["acks"]["moving"]["B0"]["motion"]["location"] = [0., 1800., 2000.]
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(self.rows)
        self.rows[0]["acks"]["moving"]["B0"]["motion"]["location"] = [-1000., 0., 2000.]
        self.rows[0]["launch_event_count"] = 2
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(self.rows)

    def test_server_wrong_position_and_launch_flags_rejected(self):
        for field in ("position_error", "rotation_error", "control_error"):
            rows = copy.deepcopy(self.rows); rows[0][field] = 2.
            with self.assertRaises(RuntimeError):
                protocol.validate_cases(rows)
        self.rows[0]["launch_event"]["xy_override"] = False
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(self.rows)

    def test_native_braking_is_retained_but_wrong_direction_speed_and_fake_motion_fail(self):
        self.rows[0]["server_motion"]["velocity"] = [0., 944., -88.]
        self.assertTrue(protocol.validate_cases(self.rows))
        for velocity in ([0., -944., -88.], [30., 944., -88.], [0., 1400., -88.], [0., 0., -88.]):
            rows = copy.deepcopy(self.rows); rows[0]["server_motion"]["velocity"] = velocity
            with self.assertRaises(RuntimeError):
                protocol.validate_cases(rows)

    def test_missing_cleanup_python_dispatch_and_no_launch_branch_rejected(self):
        for field in ("fixture_scope_closed", "portals_destroyed", "receiver_box_destroyed"):
            rows = copy.deepcopy(self.rows); rows[0][field] = False
            with self.assertRaises(RuntimeError):
                protocol.validate_cases(rows)
        rows = copy.deepcopy(self.rows); rows[1]["python_counters"]["teleports"] = 0
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(rows)
        self.rows[2]["launch_event_count"] = 1
        with self.assertRaises(RuntimeError):
            protocol.validate_cases(self.rows)

    def test_runtime_ast_and_exclusive_entry_guards(self):
        ast.parse((root/"uep_lyra_world/teleporter_network_validation.py").read_text(encoding="utf-8-sig"))
        for file in (root/"uep_lyra_network.py", root/"uep_lyra_world/effect_pad_network_validation.py"):
            tree = ast.parse(file.read_text(encoding="utf-8-sig"))
            guard = next(node for node in reversed(tree.body) if isinstance(node, ast.If))
            self.assertIn("-UEPTeleporterNetwork", ast.unparse(guard.test))
        self.assertEqual(validation_module(["-UEPTeleporterNetwork", "-UEPLyraMultiClient"]), "uep_lyra_world.teleporter_network_validation")
