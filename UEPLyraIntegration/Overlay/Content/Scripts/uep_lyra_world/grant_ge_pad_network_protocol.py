"""Instant-heal owner isolation, inactive reentry and default cooldown gates."""
import math
from .effect_pad_network_protocol import PEERS, near, require
PLAN = tuple((target, profile) for target in PEERS for profile in ("BlueprintFallback", "Python"))

def validate_ack(packet, ack, peer, stage):
    require(ack["run_id"] == packet["run_id"] and ack["case_index"] == packet["case_index"] and
            ack["peer"] == peer and ack["stage"] == stage, "wrong grant-GE ACK")
    player = ack["player"]
    require(player["player_id"] == packet["roster"][peer]["player_id"] and
            player["pawn_path"] == packet["client_pawns"][peer] and player["world_token"] == packet["client_worlds"][peer],
            "grant-GE ACK crossed owner/Pawn/world")
    expected = packet["pickup_health"] if stage == "pickup" else {key: 75.0 for key in PEERS}
    require(near(player["health"], expected[peer]), "grant-GE replicated Health differs")
    visual = ack["health_visual"]
    require(near(visual["number"], expected[peer]) and near(visual["target"], expected[peer]) and
            near(visual["ratio"], expected[peer]/player["max_health"]), "grant-GE owner HUD differs")

def validate_cases(cases):
    require(len(cases) == len(PLAN), "grant-GE network matrix incomplete")
    for index, (row, identity) in enumerate(zip(cases, PLAN)):
        require((row["target"], row["profile"]) == identity and row["case_index"] == index, "wrong grant-GE case order")
        expected = {peer: 100.0 if peer == row["target"] else 75.0 for peer in PEERS}
        require(row["pickup_health"] == expected and row["inactive_health"] == {peer: 75.0 for peer in PEERS},
                "grant-GE heal/owner/inactive rejection differs")
        require(row["physical_events"] == ["begin", "end", "begin", "end"] and row["fixture_scope_closed"] is True and
                row["pad_destroyed"] is True, "grant-GE native collision/lifetime missing")
        require(math.isfinite(row["cooldown_seconds"]) and 14.9 <= row["cooldown_seconds"] <= 15.5,
                "grant-GE native default cooldown differs")
        require(row["finish"] == {"active": True, "tick": True, "light": True, "mesh_hidden": False, "percent": 0.0},
                "grant-GE native finish state differs")
        for stage in ("pickup", "finished"):
            for peer in PEERS:
                validate_ack(row, row["acks"][stage][peer], peer, stage)
        if row["profile"] == "Python":
            require(row["python_actives"] == 2 and row["python_finishes"] == 1, "Python grant-GE path replayed/missing")
            require(row["pickup_health"] == cases[index-1]["pickup_health"] and row["finish"] == cases[index-1]["finish"],
                    "grant-GE BP/Python network differs")
