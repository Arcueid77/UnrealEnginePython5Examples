"""Two real owners; BP/Python native launch requests and received movement."""
import math

PEERS = ("A", "B0")
SCENARIOS = ("push-forward", "push-target", "up-vertical")
PLAN = tuple((target, scenario, profile) for target in PEERS for scenario in SCENARIOS
             for profile in ("BlueprintFallback", "Python"))

def require(value, message):
    if not value:
        raise RuntimeError(message)

def near(a, b, tolerance=.01):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b) < tolerance

def distance(a, b):
    require(len(a) == len(b) == 3 and all(math.isfinite(v) for v in list(a)+list(b)), "invalid native launcher vector")
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def validate_ack(packet, ack, peer, stage):
    require(ack["run_id"] == packet["run_id"] and ack["case_index"] == packet["case_index"] and
            ack["peer"] == peer and ack["stage"] == stage, "foreign launcher network ACK")
    player, motion = ack["player"], ack["motion"]
    require(player["player_id"] == packet["roster"][peer]["player_id"] and
            player["pawn_path"] == packet["client_pawns"][peer] and
            player["world_token"] == packet["client_worlds"][peer], "launcher ACK crossed owner/Pawn/world")
    require(near(player["health"], packet["roster"][peer]["health"]), "launcher changed player Health")
    visual = ack["health_visual"]
    require(near(visual["number"], player["health"]) and near(visual["target"], player["health"]) and
            near(visual["ratio"], player["health"]/player["max_health"]), "launcher native owner HUD differs")
    if stage in ("armed", "restored"):
        require(distance(motion["location"], packet["positions"][peer]) < 10.0 and
                motion["movement_mode"] == 0 and distance(motion["velocity"], [0.0]*3) < 1.0,
                "launcher client did not receive stable native baseline/restore")
    elif peer == packet["target"]:
        require(motion["movement_mode"] == 3 and motion["location"][2] > packet["positions"][peer][2]+.5 and
                distance(motion["velocity"], [0.0]*3) > 10.0, "launcher owner did not observe actual native motion")
    else:
        require(distance(motion["location"], packet["positions"][peer]) < 10.0 and
                distance(motion["velocity"], [0.0]*3) < 1.0, "launcher affected the other owner")

def validate_cases(cases):
    require(len(cases) == len(PLAN), "launcher two-client case matrix incomplete")
    for index, (row, identity) in enumerate(zip(cases, PLAN)):
        target, scenario, profile = identity
        require((row["target"], row["scenario"], row["profile"]) == identity and row["case_index"] == index,
                "launcher case identity/order differs")
        require(row["physical_events"] == ["begin", "end"] and row["fixture_scope_closed"] is True and
                row["pad_destroyed"] is True and row["pad_replicates"] is False,
                "launcher collision/cleanup/original replication missing")
        event = row["launch_event"]
        require(event["pawn"] == row["roster"][target]["pawn_path"] and row["launch_event_count"] == 1,
                "launcher native event targeted wrong Pawn or replayed")
        require(event["xy_override"] is False and event["z_override"] is (scenario == "up-vertical"),
                "launcher native override flags differ")
        require(len(event["requested"]) == len(row["expected_requested"]) == 3 and
                all(near(a,b) for a,b in zip(event["requested"], row["expected_requested"])),
                "launcher native requested velocity differs")
        require(row["server_motion"]["movement_mode"] == 3 and row["server_motion"]["location"][2] >
                row["launch_position"][2]+.5, "native server did not execute launch physics")
        require(row["other_owner_launch_events"] == 0, "launcher crossed server owner")
        for stage in ("armed", "moving", "restored"):
            packet = dict(row, positions=row["restore_positions"] if stage == "restored" else row["positions"])
            require(set(row["acks"][stage]) == set(PEERS), "launcher ACK peer missing")
            for peer in PEERS:
                validate_ack(packet, row["acks"][stage][peer], peer, stage)
        if profile == "Python":
            require(row["python_launches"] == 1 and row["python_cues"] == 1, "Python launcher bypassed/replayed")
            previous = cases[index-1]
            require(all(near(a,b) for a,b in zip(event["requested"], previous["launch_event"]["requested"])),
                    "launcher BP/Python native launch request differs")
    return True
