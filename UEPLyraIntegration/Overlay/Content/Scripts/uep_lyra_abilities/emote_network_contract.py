"""Independent two-owner Emote input/GAS/native-animation evidence gate."""
import argparse
import json
from pathlib import Path
from .emote_contract import require, validate as validate_client

PLAN = ("natural-duration", "native-cancel", "external-native-end", "active-profile-switch", "repeat")
PEERS = ("A", "B0")


def validate(reports):
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["original_player_states_restored"] and
        server["original_profiles_restored"] and server["server_waited_for_client_process_exit"] and
        server["native_playing_gate"]["native_playing_phase"], "native Emote authority/restore/exit incomplete")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay",
                  "authoritative_movement_written", "ability_activation_called_by_probe", "native_rpc_bypassed",
                  "packet_loss_tested", "travel_rejoin_tested", "network_movement_interruption_tested",
                  "network_crouch_interruption_tested", "network_pause_tested", "gameplay_state_delivered_by_files"):
        require(server[field] is False, "unsupported Emote network claim: " + field)
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "Emote owners are not distinct")
    for peer in PEERS:
        client = reports[peer]
        validate_client(client, PLAN)
        require((client["peer"], client["run_id"], client["player_id"], client["native_net_mode"], client["native_owner_role"]) ==
            (peer, server["run_id"], server["player_ids"][peer], "Client", 2), "native Emote owner identity/mode/role differs")
        for field in ("native_rpc_bypassed", "packet_loss_tested", "travel_rejoin_tested", "network_movement_interruption_tested",
                      "network_crouch_interruption_tested", "network_pause_tested", "gameplay_state_delivered_by_files"):
            require(client[field] is False, "unsupported Emote owner claim: " + field)
    expected = [(peer, index) for peer in PEERS for index in range(len(PLAN) * 2)]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "Emote authority matrix incomplete")
    for row in server["cases"]:
        peer, index = row["target"], row["index"]
        require(row["name"] == PLAN[index // 2] and row["authoritative_role"] == 3 and row["authority_tasks_after"] == 0,
                "Emote native authority role/name/task cleanup differs")
        for field in ("native_active_observed", "native_montage_observed", "native_task_observed", "foreign_owner_unchanged",
                      "authority_original_restored", "native_type_source_preserved", "actual_authority_held"):
            require(row[field] is True, "Emote native authority observation missing: " + field)
        client = reports[peer]["cases"][index // 2]["python" if index % 2 else "blueprint"]
        ack = row["client"]
        require((ack["run_id"], ack["peer"], ack["index"]) == (server["run_id"], peer, index) and ack["row"] == client,
                "Emote authority acknowledgement differs from independently checked owner")
        stats = row["authority_counters"]
        if index % 2:
            require(stats["activations"] == stats["tasks_created"] == 1 and
                    stats["scopes_created"] == stats["scopes_closed"] == 2,
                    "authority Python Emote was bypassed or leaked")
        else:
            require(stats["fallback_activations"] == 1, "authority original BP activation was bypassed")
    stats = server["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [],
            "native Emote authority policy leak/error")
    return dict(status="passed", bounded_network_acceptance=True, owners=2, native_authority_trials=len(expected),
                native_rpc_bypassed=False, network_movement_interruption_tested=False,
                network_crouch_interruption_tested=False, network_pause_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root / (peer + ".json")).read_text(encoding="utf-8-sig")) for peer in ("server",) + PEERS})))
