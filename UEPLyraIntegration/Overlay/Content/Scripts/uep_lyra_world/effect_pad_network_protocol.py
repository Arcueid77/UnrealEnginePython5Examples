"""Pure acceptance rules for server-side physical pads and two local owners."""

import math


PEERS = ("A", "B0")
CLASSES = ("BP_GameplayEffectPad_C", "B_GameplayEffectPad_Child_Healing_C")
PLAN = tuple((cls, kind, target, profile) for cls in CLASSES
             for kind in ("damage", "heal") for target in PEERS
             for profile in ("BlueprintFallback", "Python"))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def near(actual, expected):
    return type(actual) in (int, float) and math.isfinite(actual) and abs(actual - expected) <= 0.05


def expected_health(kind, target):
    require(kind in ("damage", "heal") and target in PEERS, "Invalid pad case")
    return {peer: (65.0 if kind == "damage" else 85.0) if peer == target else 75.0 for peer in PEERS}


def validate_ack(packet, ack, peer):
    for name in ("run_id", "case_index", "server_world_token"):
        require(ack.get(name) == packet[name], "Stale pad ACK: " + name)
    require(ack.get("peer") == peer and peer in PEERS, "Wrong pad ACK owner")
    player = ack["player"]
    require(player["player_id"] == packet["roster"][peer]["player_id"], "Pad ACK changed player identity")
    require(player["pawn_path"] == packet["client_pawns"][peer], "Pad ACK changed Pawn")
    require(player["world_token"] == packet["client_worlds"][peer], "Pad ACK changed World")
    require(near(player["health"], packet["expected_health"][peer]), "Replicated pad Health mismatch")
    visual = ack["health_visual"]
    require(near(visual["number"], player["health"]) and near(visual["target"], player["health"])
            and near(visual["ratio"], player["health"] / player["max_health"]), "Pad HUD differs from native owner")


def validate_server_cases(cases):
    require(len(cases) == len(PLAN), "Incomplete pad network matrix")
    for index, (case, identity) in enumerate(zip(cases, PLAN)):
        require((case["class"], case["kind"], case["target"], case["profile"]) == identity, "Pad matrix order differs")
        require(case["case_index"] == index and case["inside_count"] >= 1 and case["after_count"] == 0,
                "Pad GAS lifetime differs")
        require(case["physical_events"] == ["begin", "end"], "Missing real collision events")
        require(case["health_after"] == expected_health(case["kind"], case["target"]), "Pad ownership differs")
        for peer in PEERS:
            validate_ack(case, case["acks"][peer], peer)
        if case["profile"] == "Python":
            require(case["python_constructions"] == case["python_begin_intents"] == case["python_end_intents"] == 1,
                    "Python pad path bypassed or replayed")
            original = cases[index - 1]
            require(original["health_after"] == case["health_after"] and original["inside_count"] == case["inside_count"],
                    "BP/Python pad network outcome differs")
