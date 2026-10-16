"""Adversarial matrix/entry checks; not a substitute for native networking."""
import ast
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"Overlay/Content/Scripts"))
from uep_lyra_world.grant_ge_pad_network_protocol import PLAN, PEERS, validate_cases
from uep_lyra_hud.startup import validation_module

class GrantGENetworkGate(unittest.TestCase):
    def setUp(self):
        self.cases = []
        for index, (target, profile) in enumerate(PLAN):
            health = {peer: 100.0 if peer == target else 75.0 for peer in PEERS}
            row = {"run_id": "run", "case_index": index, "target": target, "profile": profile, "pickup_health": health,
                "inactive_health": {peer: 75.0 for peer in PEERS}, "physical_events": ["begin", "end", "begin", "end"],
                "fixture_scope_closed": True, "pad_destroyed": True, "cooldown_seconds": 15.01,
                "finish": {"active": True, "tick": True, "light": True, "mesh_hidden": False, "percent": 0.0},
                "roster": {peer: {"player_id": number} for number, peer in enumerate(PEERS)},
                "client_pawns": {peer: "pawn-"+peer for peer in PEERS}, "client_worlds": {peer: "world-"+peer for peer in PEERS},
                "python_actives": 2 if profile == "Python" else 0, "python_finishes": 1 if profile == "Python" else 0, "acks": {}}
            for stage in ("pickup", "finished"):
                row["acks"][stage] = {}
                for number, peer in enumerate(PEERS):
                    value = health[peer] if stage == "pickup" else 75.0
                    row["acks"][stage][peer] = {"run_id": "run", "case_index": index, "peer": peer, "stage": stage,
                        "player": {"player_id": number, "pawn_path": "pawn-"+peer, "world_token": "world-"+peer,
                            "health": value, "max_health": 100.0}, "health_visual": {"number": value, "target": value, "ratio": value/100.0}}
            self.cases.append(row)

    def test_complete_default_cooldown_matrix(self):
        self.assertEqual(len(PLAN), 4)
        validate_cases(self.cases)

    def test_wrong_owner_reentry_heal_or_short_cooldown_rejected(self):
        for mutate in (lambda c: c[0]["pickup_health"].update(B0=100.0), lambda c: c[0]["inactive_health"].update(A=100.0),
                       lambda c: c[0].update(cooldown_seconds=.6), lambda c: c[1].update(python_actives=1)):
            cases = copy.deepcopy(self.cases)
            mutate(cases)
            with self.assertRaises(RuntimeError):
                validate_cases(cases)

    def test_missing_collision_or_native_ui_rejected(self):
        for mutate in (lambda c: c[0].update(physical_events=["begin", "end"]),
                       lambda c: c[0]["acks"]["finished"]["B0"]["health_visual"].update(number=100.0)):
            cases = copy.deepcopy(self.cases)
            mutate(cases)
            with self.assertRaises(RuntimeError):
                validate_cases(cases)

    def test_base_effect_lane_does_not_start_competing_ticker(self):
        self.assertEqual(validation_module(["-UEPGrantGENetwork"]), "uep_lyra_world.grant_ge_pad_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPGrantGENetwork"]))
        source = (ROOT/"Overlay/Content/Scripts/uep_lyra_world/effect_pad_network_validation.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        guard = ast.Expression(tree.body[-1].test)
        self.assertFalse(eval(compile(guard, "guard", "eval"), {"sys": type("Args", (), {"argv": ["-UEPGrantGENetwork"]})()}))
        self.assertTrue(eval(compile(guard, "guard", "eval"), {"sys": type("Args", (), {"argv": ["-UEPEffectPadNetwork"]})()}))
