import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts"))
from uep_lyra_world.effect_pad_network_protocol import PLAN, PEERS, expected_health, validate_ack, validate_server_cases


def cases():
    result = []
    for index, (cls, kind, target, profile) in enumerate(PLAN):
        row = {"run_id": "fixture", "case_index": index, "class": cls, "kind": kind, "target": target,
               "profile": profile, "server_world_token": "server", "inside_count": 1, "after_count": 0,
               "physical_events": ["begin", "end"], "expected_health": expected_health(kind, target),
               "health_after": expected_health(kind, target), "roster": {}, "client_pawns": {},
               "client_worlds": {}, "acks": {}, "python_constructions": 1,
               "python_begin_intents": 1, "python_end_intents": 1}
        for number, peer in enumerate(PEERS):
            health = row["health_after"][peer]
            row["roster"][peer] = {"player_id": number}
            row["client_pawns"][peer] = "pawn-" + peer
            row["client_worlds"][peer] = "world-" + peer
            row["acks"][peer] = {"run_id": "fixture", "case_index": index, "server_world_token": "server",
                                 "peer": peer, "player": {"player_id": number, "pawn_path": "pawn-" + peer,
                                 "world_token": "world-" + peer, "health": health, "max_health": 100},
                                 "health_visual": {"number": health, "target": health, "ratio": health / 100}}
        result.append(row)
    return result


class PadNetworkContracts(unittest.TestCase):
    def test_matrix_covers_two_classes_effects_owners_and_profiles(self):
        self.assertEqual(len(PLAN), 16)
        validate_server_cases(cases())

    def test_non_target_health_stays_at_baseline(self):
        self.assertEqual(expected_health("damage", "A"), {"A": 65, "B0": 75})
        self.assertEqual(expected_health("heal", "B0"), {"A": 75, "B0": 85})

    def test_reject_stale_ack(self):
        row = cases()[0]
        row["acks"]["A"]["case_index"] = -1
        with self.assertRaisesRegex(RuntimeError, "Stale pad ACK"):
            validate_ack(row, row["acks"]["A"], "A")

    def test_reject_wrong_owner(self):
        row = cases()[0]
        row["acks"]["A"]["player"]["player_id"] = 1
        with self.assertRaisesRegex(RuntimeError, "identity"):
            validate_ack(row, row["acks"]["A"], "A")

    def test_reject_lingering_effect_or_fake_collision(self):
        for key, value in (("after_count", 1), ("physical_events", ["begin"]), ("python_end_intents", 2)):
            rows = cases()
            rows[1][key] = value
            with self.assertRaises(RuntimeError):
                validate_server_cases(rows)

    def test_reject_wrong_native_health_or_widget(self):
        for field in ("number", "target", "ratio"):
            row = copy.deepcopy(cases()[0])
            row["acks"]["A"]["health_visual"][field] = 0
            with self.assertRaisesRegex(RuntimeError, "HUD differs"):
                validate_ack(row, row["acks"]["A"], "A")

    def test_reject_partial_matrix(self):
        with self.assertRaisesRegex(RuntimeError, "Incomplete"):
            validate_server_cases(cases()[:-1])


if __name__ == "__main__":
    unittest.main()
