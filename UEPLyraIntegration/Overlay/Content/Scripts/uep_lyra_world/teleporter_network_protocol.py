"""Two real owner teleport/launch observations; no synthetic client snapshots."""
import math
from .launcher_network_protocol import PEERS, near, distance, require

SCENARIOS = ("launch", "no-launch", "relative-offset")
PLAN = tuple((peer, scenario, profile) for peer in PEERS for scenario in SCENARIOS
             for profile in ("BlueprintFallback", "Python"))


def validate_ack(packet, ack, peer, stage):
    require(ack["run_id"] == packet["run_id"] and ack["case_index"] == packet["case_index"] and
            ack["peer"] == peer and ack["stage"] == stage, "foreign teleporter ACK")
    player, motion = ack["player"], ack["motion"]
    require(player["player_id"] == packet["roster"][peer]["player_id"] and
            player["pawn_path"] == packet["client_pawns"][peer] and player["world_token"] == packet["client_worlds"][peer],
            "teleporter ACK crossed owner/Pawn/world")
    require(near(player["health"], packet["roster"][peer]["health"]), "teleporter changed native Health")
    visual = ack["health_visual"]
    require(near(visual["number"], player["health"]) and near(visual["target"], player["health"]) and
            near(visual["ratio"], player["health"]/player["max_health"]), "teleporter native owner HUD differs")
    if stage in ("armed", "restored") or peer != packet["target"]:
        require(distance(motion["location"], packet["positions"][peer]) < 10. and motion["movement_mode"] == 0 and
                distance(motion["velocity"], [0.]*3) < 1., "teleporter baseline/other-owner/restore differs")
        return
    require(stage == "moving" and motion["movement_mode"] == 3, "teleporter owner did not receive native movement")
    require(distance(motion["location"], packet["positions"][peer]) > 800., "teleporter owner remained at entry")
    delta = [a-b for a, b in zip(motion["location"], packet["expected_location"])]
    forward = packet["forward"]
    along = delta[0]*forward[0]+delta[1]*forward[1]
    across = delta[0]*forward[1]-delta[1]*forward[0]
    require(abs(across) < 35. and abs(delta[2]) < 1500., "teleporter client exit/trajectory differs")
    if packet["scenario"] == "no-launch":
        require(math.hypot(delta[0], delta[1]) < 20. and math.hypot(*motion["velocity"][:2]) < 1.,
                "teleporter no-launch client has horizontal launch")
    else:
        require(along > 2. and math.hypot(*motion["velocity"][:2]) > 100., "teleporter native owner launch not observed")


def validate_cases(cases):
    require(len(cases) == len(PLAN), "teleporter two-client matrix incomplete")
    for index, (row, identity) in enumerate(zip(cases, PLAN)):
        target, scenario, profile = identity
        require((row["target"], row["scenario"], row["profile"]) == identity and row["case_index"] == index,
                "teleporter case identity/order differs")
        require(row["physical_events"] == ["end", "begin"] and row["fixture_scope_closed"] is True and
                row["portals_destroyed"] is True and row["portal_replicates"] is False,
                "teleporter physical lifecycle/original replication differs")
        require(row["position_error"] < .01 and row["rotation_error"] < .01 and row["control_error"] < .01 and
                row["destination_selected"] is True and row["receiving_pawn"] is True and row["receiver_box_destroyed"] is True,
                "teleporter native server transform/target differs")
        expected = int(scenario != "no-launch")
        require(row["launch_event_count"] == expected and row["other_owner_launch_events"] == 0,
                "teleporter native launch crossed owner/replayed")
        if expected:
            event = row["launch_event"]
            require(event["pawn"] == row["roster"][target]["pawn_path"] and
                    event["xy_override"] is True and event["z_override"] is True and
                    distance(event["requested"], row["expected_requested"]) < .01,
                    "teleporter native requested launch differs")
        motion = row["server_motion"]
        require(motion["movement_mode"] == 3 and distance(motion["location"], row["positions"][target]) > 800.,
                "teleporter native server physics missing")
        vx, vy = motion["velocity"][:2]
        rx, ry = row["expected_requested"][:2]
        requested_speed, speed = math.hypot(rx, ry), math.hypot(vx, vy)
        if expected:
            # Real Lyra retains native braking/air friction; unlike zero-gravity
            # fixtures its later velocity is not the original launch request.
            # Require actual forward flight without artificial acceleration or
            # sideways motion. Exact native request/override parity is above.
            require(100. < speed <= requested_speed+.1 and vx*rx+vy*ry > 0. and
                    abs(vx*ry-vy*rx)/requested_speed < .1,
                    "teleporter native server flight direction/braking differs")
        else:
            require(speed < 1., "teleporter no-launch native server gained horizontal velocity")
        for stage in ("armed", "moving", "restored"):
            packet = dict(row, positions=row["restore_positions"] if stage == "restored" else row["positions"])
            require(set(row["acks"][stage]) == set(PEERS), "teleporter ACK peer missing")
            for peer in PEERS:
                validate_ack(packet, row["acks"][stage][peer], peer, stage)
        count = row["python_counters"]
        if profile == "Python":
            require(count["begins"] == count["destinations"] == count["character_entries"] == count["teleports"] ==
                    count["pawn_audio"] == count["rotations"] == 1 and count["launches"] == expected,
                    "teleporter Python business bypassed/replayed")
            previous = cases[index-1]
            require(distance(row["expected_requested"], previous["expected_requested"]) < .01,
                    "teleporter BP/Python native launch differs")
    return True
