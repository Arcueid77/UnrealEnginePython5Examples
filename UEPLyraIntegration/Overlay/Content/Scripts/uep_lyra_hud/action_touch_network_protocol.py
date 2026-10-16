"""Two-owner client-local UI proof; GameplayMessageSubsystem is NOT replicated."""
import math
from .action_touch_contract import equal, require

PEERS = ("A", "B0")
PHASES = ("baseline", "owner-A", "owner-B0", "foreign", "unmounted", "reconstructed", "profiles", "cleanup")


def validate_ack(packet, ack, peer):
    phase = PHASES[packet["phase_index"]]
    require(ack["run_id"] == packet["run_id"] and ack["phase_index"] == packet["phase_index"] and
            ack["phase"] == phase and ack["peer"] == peer, "foreign action-touch ACK")
    player = ack["player"]
    require(player["player_id"] == packet["roster"][peer]["player_id"] and player["pawn_path"] and player["world_token"] and
            player["net_mode"] == "Client" and player["pawn_locally_controlled"] is True,
            "action-touch ACK crossed actual local owner")
    require(math.isfinite(player["health"]) and abs(player["health"]-packet["roster"][peer]["health"]) < .01,
            "action-touch altered player Health")
    require(ack["synthetic_client_local_typed_message"] is True and ack["message_network_replication_tested"] is False,
            "local gameplay message mislabeled as network replication")
    if phase == "cleanup":
        require(ack["roots_released"] == 4 and ack["owned_active_count"] == 0 and ack["scopes_balanced"] is True and
                ack["production_scopes_preserved"] is True,
                "action-touch client root/scope cleanup incomplete")
        return
    require(set(ack["pairs"]) == {"base", "mobile"}, "action-touch native pair missing")
    for kind, row in ack["pairs"].items():
        require(row["same_class"] is True and row["owner_correct"] is True and equal(row["python"], row["blueprint"]),
                "action-touch native BP/Python state/owner differs")
        if phase == "baseline":
            require(row["python_messages"] == 0 and row["python"]["duration"] == 5., "touch baseline already received a message")
        elif phase.startswith("owner-"):
            target = phase[6:]
            require(ack["broadcast_player_id"] == packet["roster"][target]["player_id"] and
                    ack["broadcast_instigator"] and (ack["broadcast_instigator"] == player["pawn_path"]) is (peer == target),
                    "touch producer did not use actual replicated target Pawn")
            expected = 2. if peer == "A" else (3. if target == "B0" else 5.)
            require(abs(row["python"]["duration"]-expected) < .0001 and row["python_messages"] == int(peer == "A" or target == "B0"),
                    "touch duration crossed owner or delivered more than once")
        elif phase == "foreign":
            require(row["model_unchanged"] is True and ack["broadcast_player_id"] != player["player_id"],
                    "actual foreign Pawn message affected local touch UI")
        elif phase == "unmounted":
            require(row["model_unchanged"] is True and row["python_scope_closed"] is True and row["original_proxy_inactive"] is True,
                    "unmounted touch UI still subscribed/received duration")
        elif phase in ("reconstructed", "profiles"):
            require(abs(row["python"]["duration"]-(.7 if phase == "reconstructed" else 1.1)) < .0001 and
                    row["message_delta"] == 1 and row["original_proxy_inactive"] is False,
                    "touch reconstruct/Profile message replay or missing native proxy")
            if phase == "profiles":
                require(row["old_python_scope_closed"] is True and row["old_original_proxy_inactive"] is True,
                        "touch Profile switch retained previous listener")


def validate_phases(rows):
    require(len(rows) == len(PHASES), "two-client touch phase matrix incomplete")
    identities = {}
    for index, row in enumerate(rows):
        require(row["phase_index"] == index and row["phase"] == PHASES[index] and set(row["acks"]) == set(PEERS),
                "two-client touch phase identity/order differs")
        for peer in PEERS:
            ack = row["acks"][peer]
            validate_ack(row, ack, peer)
            identity = (ack["player"]["pawn_path"], ack["player"]["world_token"])
            if peer in identities:
                require(identities[peer] == identity, "touch client Pawn/World changed during proof")
            identities[peer] = identity
    require(identities["A"][1] != identities["B0"][1], "touch evidence reused one client World")
    return True
