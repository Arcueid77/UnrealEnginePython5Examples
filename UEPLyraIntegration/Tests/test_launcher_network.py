"""Network report negatives and exclusive startup; not actual peer proof."""
import ast
import copy
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"Overlay/Content/Scripts"))
from uep_lyra_world.launcher_network_protocol import PLAN, PEERS, validate_cases
from uep_lyra_hud.startup import validation_module

class LauncherNetworkGate(unittest.TestCase):
    def setUp(self):
        self.cases = []
        for index, (target, scenario, profile) in enumerate(PLAN):
            positions = {peer: [0.0, 0.0, 1000.0] for peer in PEERS}
            row = {"run_id": "run", "case_index": index, "target": target, "scenario": scenario, "profile": profile,
                "positions": positions, "restore_positions": copy.deepcopy(positions), "launch_position": positions[target],
                "physical_events": ["begin", "end"], "fixture_scope_closed": True, "pad_destroyed": True, "pad_replicates": False,
                "roster": {peer: {"player_id": number, "health": 100.0, "pawn_path": "server-"+peer} for number, peer in enumerate(PEERS)},
                "client_pawns": {peer: "client-"+peer for peer in PEERS}, "client_worlds": {peer: "world-"+peer for peer in PEERS},
                "launch_event": {"pawn": "server-"+target, "requested": [1.0, 0.0, 250.0], "xy_override": False,
                                 "z_override": scenario == "up-vertical"}, "expected_requested": [1.0, 0.0, 250.0],
                "launch_event_count": 1, "other_owner_launch_events": 0,
                "server_motion": {"movement_mode": 3, "location": [0.0, 0.0, 1010.0]},
                "python_launches": int(profile == "Python"), "python_cues": int(profile == "Python"), "acks": {}}
            for stage in ("armed", "moving", "restored"):
                row["acks"][stage] = {}
                for number, peer in enumerate(PEERS):
                    moving = stage == "moving" and peer == target
                    row["acks"][stage][peer] = {"run_id": "run", "case_index": index, "peer": peer, "stage": stage,
                        "player": {"player_id": number, "health": 100.0, "max_health": 100.0,
                                   "pawn_path": "client-"+peer, "world_token": "world-"+peer},
                        "health_visual": {"number": 100.0, "target": 100.0, "ratio": 1.0},
                        "motion": {"movement_mode": 3 if moving else 0,
                                   "location": [0.0, 0.0, 1010.0 if moving else 1000.0],
                                   "velocity": [1.0, 0.0, 200.0] if moving else [0.0]*3}}
            self.cases.append(row)

    def test_complete_twelve_real_owner_cases(self):
        self.assertEqual(len(PLAN), 12)
        self.assertTrue(validate_cases(self.cases))

    def test_foreign_owner_stale_world_and_fake_stationary_target_rejected(self):
        for mutate in (lambda c: c[0]["acks"]["moving"]["A"]["player"].update(player_id=99),
                       lambda c: c[0]["acks"]["armed"]["B0"]["player"].update(world_token="old-world"),
                       lambda c: c[0]["acks"]["moving"]["A"]["motion"].update(velocity=[0.0]*3),
                       lambda c: c[0]["acks"]["moving"]["B0"]["motion"].update(velocity=[100.0]*3)):
            rows = copy.deepcopy(self.cases);mutate(rows)
            with self.assertRaises(RuntimeError):
                validate_cases(rows)

    def test_wrong_native_request_replay_and_replication_force_rejected(self):
        for mutate in (lambda c: c[0].update(launch_event_count=2), lambda c: c[0].update(pad_replicates=True),
                       lambda c: c[1].update(python_launches=0), lambda c: c[0]["launch_event"].update(requested=[2.0, 0.0, 250.0]),
                       lambda c: c[0]["acks"].pop("restored")):
            rows = copy.deepcopy(self.cases);mutate(rows)
            with self.assertRaises((RuntimeError, KeyError)):
                validate_cases(rows)

    def test_lifecycle_ui_and_nan_vector_rejected(self):
        for mutate in (lambda c: c[0].update(physical_events=["begin"]),
                       lambda c: c[0]["acks"]["moving"]["A"]["health_visual"].update(ratio=.75),
                       lambda c: c[0]["acks"]["restored"]["A"]["motion"].update(location=[float("nan")]*3)):
            rows = copy.deepcopy(self.cases);mutate(rows)
            with self.assertRaises(RuntimeError):
                validate_cases(rows)

    def test_only_launcher_entry_starts(self):
        self.assertEqual(validation_module(["-UEPLauncherNetwork", "-UEPLyraMultiClient"]), "uep_lyra_world.launcher_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPLauncherNetwork"]))
        for relative in ("uep_lyra_network.py", "uep_lyra_world/effect_pad_network_validation.py"):
            source = (ROOT/"Overlay/Content/Scripts"/relative).read_text(encoding="utf-8")
            guard = ast.Expression(ast.parse(source).body[-1].test)
            self.assertFalse(eval(compile(guard, "guard", "eval"), {"sys": types.SimpleNamespace(argv=["-UEPLauncherNetwork"])}))

    def test_network_modules_parse_before_native_launch(self):
        for name in ("launcher_observation.py", "launcher_network_protocol.py", "launcher_network_validation.py"):
            ast.parse((ROOT/"Overlay/Content/Scripts/uep_lyra_world"/name).read_text(encoding="utf-8"))

    def test_motion_does_not_resolve_unready_pawn(self):
        source = (ROOT/"Overlay/Content/Scripts/uep_lyra_world/launcher_network_validation.py").read_text(encoding="utf-8")
        cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef))
        motion = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "motion")
        def forbidden(*args):
            self.fail("unready native Pawn must not be resolved")
        namespace = {"ue": types.SimpleNamespace(find_object=forbidden)}
        exec(compile(ast.Module(body=[motion], type_ignores=[]), "motion-guard", "exec"), namespace)
        probe = types.SimpleNamespace(player={"pawn_path": ""}, _player_ready=lambda row: False)
        self.assertIsNone(namespace["motion"](probe))

    def test_verified_restore_does_not_touch_disconnected_pawns(self):
        source = (ROOT/"Overlay/Content/Scripts/uep_lyra_world/launcher_network_validation.py").read_text(encoding="utf-8")
        cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef))
        restore = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "restore")
        namespace = {}
        exec(compile(ast.Module(body=[restore], type_ignores=[]), "restore-guard", "exec"), namespace)
        probe = types.SimpleNamespace(peer="server", players_restored=True)
        self.assertIsNone(namespace["restore"](probe))

    def test_completed_client_does_not_rewrite_immutable_ready_file(self):
        source = (ROOT/"Overlay/Content/Scripts/uep_lyra_world/launcher_network_validation.py").read_text(encoding="utf-8")
        cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef))
        client = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "client_tick")
        def forbidden(*args):
            self.fail("completed client must publish readiness only once")
        namespace = {"read_json": lambda path: {"run_id": "run", "stage": "complete"},
                     "require": lambda condition, message: self.assertTrue(condition), "atomic_write": forbidden}
        exec(compile(ast.Module(body=[client], type_ignores=[]), "ready-once", "exec"), namespace)
        probe = types.SimpleNamespace(root=Path("."), run_id="run", current_visual={}, motion=lambda: None, players_restored=True)
        self.assertIsNone(namespace["client_tick"](probe))
