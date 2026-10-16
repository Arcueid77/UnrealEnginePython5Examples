"""Synthetic adversarial gates only; the live three-process lane is separate."""
import ast
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"Overlay/Content/Scripts"))
from uep_lyra_world.inventory_pad_network_protocol import PLAN, PEERS, validate_ack, validate_cases, baseline_ready
from uep_lyra_hud.startup import validation_module


class InventoryNetworkGate(unittest.TestCase):
    def setUp(self):
        self.cases = []
        for index, (cls, kind, target, profile) in enumerate(PLAN):
            native = {"items": ["pistol"], "magazine": 12}
            baseline = {peer: copy.deepcopy(native) for peer in PEERS}
            expected = copy.deepcopy(baseline)
            expected[target]["items"] += ["pistol"]*(1 if kind == "pickup" else 2)
            after = copy.deepcopy(expected)
            if kind == "pickup":
                after[target]["magazine"] -= 1
            row = {"run_id": "run", "case_index": index, "class": cls, "kind": kind, "target": target, "profile": profile,
                "roster": {peer: {"player_id": number} for number, peer in enumerate(PEERS)},
                "client_pawns": {peer: "pawn-"+peer for peer in PEERS}, "client_worlds": {peer: "world-"+peer for peer in PEERS},
                "baseline": baseline, "expected": expected, "after": after, "physical_events": ["begin", "end"],
                "pad_destroyed": True, "fixture_scope_closed": True, "acks": {}, "rollbacks": {},
                "python_grants": int(profile == "Python" and kind == "pickup"),
                "python_full_rejections": int(profile == "Python" and kind == "full")}
            for number, peer in enumerate(PEERS):
                row["acks"][peer] = {"run_id": "run", "case_index": index, "peer": peer,
                    "player": {"player_id": number, "pawn_path": "pawn-"+peer, "world_token": "world-"+peer},
                    "inventory": copy.deepcopy(after[peer]), "input_frames": 1 if peer == target and kind == "pickup" else 0}
                row["rollbacks"][peer] = {"run_id": "run", "case_index": index, "peer": peer, "inventory": copy.deepcopy(native)}
            self.cases.append(row)

    def test_sixteen_complete_combinations(self):
        self.assertEqual(len(PLAN), 16)
        validate_cases(self.cases)

    def test_transient_missing_status_waits_without_reusing_old_state(self):
        baseline = {peer: {"magazine": 12} for peer in PEERS}
        statuses = {peer: {"inventory": dict(baseline[peer])} for peer in PEERS}
        self.assertTrue(baseline_ready(statuses, baseline))
        for value in (None, {}, {"inventory": None}, {"inventory": {"magazine": 11}}):
            changed = dict(statuses, B0=value)
            self.assertFalse(baseline_ready(changed, baseline))
        self.assertFalse(baseline_ready({"A": statuses["A"]}, baseline))

    def test_foreign_player_pawn_world_or_run_rejected(self):
        row = self.cases[0]
        for mutate in (lambda a: a.update(run_id="other"), lambda a: a["player"].update(player_id=7),
                       lambda a: a["player"].update(pawn_path="old"), lambda a: a["player"].update(world_token="old")):
            ack = copy.deepcopy(row["acks"]["A"])
            mutate(ack)
            with self.assertRaises(RuntimeError):
                validate_ack(row, ack, "A")

    def test_unfired_unreplicated_or_wrong_owner_rejected(self):
        row = self.cases[0]
        for mutate in (lambda a: a.update(input_frames=0), lambda a: a["inventory"].update(magazine=12),
                       lambda a: a["inventory"]["items"].append("foreign")):
            ack = copy.deepcopy(row["acks"]["A"])
            mutate(ack)
            with self.assertRaises(RuntimeError):
                validate_ack(row, ack, "A")

    def test_lifecycle_or_native_rollback_missing_rejected(self):
        for mutate in (lambda c: c[0].update(physical_events=["begin"]), lambda c: c[0].update(pad_destroyed=False),
                       lambda c: c[0]["rollbacks"]["B0"]["inventory"].update(magazine=11)):
            cases = copy.deepcopy(self.cases)
            mutate(cases)
            with self.assertRaises(RuntimeError):
                validate_cases(cases)

    def test_entry_and_native_source_boundaries(self):
        self.assertEqual(validation_module(["-UEPInventoryPadNetwork"]), "uep_lyra_world.inventory_pad_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPInventoryPadNetwork"]))
        text = (ROOT/"Overlay/Content/Scripts/uep_lyra_world/inventory_pad_network_validation.py").read_text(encoding="utf-8")
        ast.parse(text)
        for token in ('"OnComponentBeginOverlap"', '"OnComponentEndOverlap"', 'inject_enhanced_input_for_action(', '"RemoveItemInstance"'):
            self.assertIn(token, text)
        for token in ('"ReceiveTick"', '"ReceiveBeginPlay"', '"ReceiveEndPlay"', '"SetStatTagStack"', '"RemoveStatTagStack"', 'set_actor_replicates('):
            self.assertNotIn(token, text)

    def test_base_network_does_not_start_a_competing_ticker(self):
        source = (ROOT/"Overlay/Content/Scripts/uep_lyra_network.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        guard = tree.body[-1]
        self.assertIsInstance(guard, ast.If)
        expression = ast.Expression(guard.test)
        for flag in ("-UEPLyraWeaponNetwork", "-UEPEffectPadNetwork", "-UEPInventoryPadNetwork", "-UEPGrantGENetwork"):
            with self.subTest(flag=flag):
                self.assertFalse(eval(compile(expression, "guard", "eval"), {"sys": type("Args", (), {"argv": [flag]})()}))
        self.assertTrue(eval(compile(expression, "guard", "eval"), {"sys": type("Args", (), {"argv": ["-UEPLyraMultiClient"]})()}))
