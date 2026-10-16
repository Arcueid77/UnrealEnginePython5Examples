"""Two LocalOnly owners, actual foreign local UI and inactive authority gate."""
import argparse
import json
from pathlib import Path
from .widget_held_contract import NETWORK_PLAN, require, validate

PEERS = ("A", "B0")


def validate_network(reports):
    require(set(reports) == {"server", *PEERS}, "held-widget needs server and two actual clients")
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["peer"] == "server" and
            isinstance(server["run_id"], str) and bool(server["run_id"]) and server["server_waited_for_client_process_exit"] and
            server["original_player_states_restored"] and server["native_playing_gate"]["native_playing_phase"], "held-widget authority/readiness/exit proof incomplete")
    require([row["target"] for row in server["cases"]] == [peer for peer in PEERS for _ in range(len(NETWORK_PLAN) * 2)],
            "held-widget owner ordering/count differs")
    ids = set()
    for peer in PEERS:
        client = reports[peer]
        validate(client, ("tdm",), NETWORK_PLAN, False)
        require(client["peer"] == peer and client["run_id"] == server["run_id"] and
                client["native_owner_role"] == 2 and client["native_net_mode"] == "Client", "held-widget actual client identity differs")
        ids.add(client["player_id"])
        require(server["player_ids"][peer] == client["player_id"], "held-widget native authority owner differs")
        for field in ("packet_loss_tested", "travel_rejoin_tested", "gameplay_state_delivered_by_files", "localonly_ui_replication_claimed"):
            require(client[field] is False, "unsupported held-widget networking claim: " + field)
        passive = client["passive_held_observations"]
        require(len(passive) == len(NETWORK_PLAN) * 2 and sorted(row["index"] for row in passive) == list(range(len(NETWORK_PLAN) * 2)),
                "held-widget foreign UI was not independently observed for every held trial")
        for row in passive:
            require(row["peer"] == peer and row["target"] != peer and row["run_id"] == server["run_id"] and
                    row["native_owner_unchanged"] and row["native_ability_inactive"] and row["native_menu_empty"] and row["native_tasks"] == 0,
                    "held-widget foreign local UI/ability affected")
        rows = [row for row in server["cases"] if row["target"] == peer]
        for index, row in enumerate(rows):
            require(row["index"] == index and row["name"] == NETWORK_PLAN[index // 2] and
                    row["profile"] == ("BlueprintFallback", "Python")[index % 2], "held-widget network native matrix differs")
            require(row["authority_inactive_samples"] >= 2 and row["native_localonly_authority_unchanged"] and
                    row["foreign_local_owner_observed"], "LocalOnly authority/foreign-owner proof incomplete")
            ack, passive_row = row["client"], row["passive"]
            other = next(value for value in PEERS if value != peer)
            require((ack["run_id"], ack["peer"], ack["index"]) == (server["run_id"], peer, index),
                    "held-widget authority acknowledgement identity differs")
            require((passive_row["run_id"], passive_row["peer"], passive_row["target"], passive_row["index"], passive_row["stage"], passive_row["player_id"]) ==
                    (server["run_id"], other, peer, index, "held", server["player_ids"][other]) and
                    passive_row["native_owner_unchanged"] and passive_row["native_ability_inactive"] and
                    passive_row["native_menu_empty"] and passive_row["native_tasks"] == 0,
                    "held-widget authority foreign-local-UI acknowledgement differs")
            expected = client["cases"][index // 2][("blueprint", "python")[index % 2]]
            require(row["client"]["row"] == expected, "held-widget authority acknowledgement differs from final native client report")
    require(len(ids) == 2, "held-widget owners are not distinct native players")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "ability_activation_called_by_probe", "callback_replay",
                  "packet_loss_tested", "travel_rejoin_tested", "gameplay_state_delivered_by_files", "localonly_ui_replication_claimed", "network_pause_tested"):
        require(server[field] is False, "unsupported held-widget authority claim: " + field)
    stats = server["policy_shutdown"]
    require(stats["activations"] == stats["fallback_activations"] == stats["scopes_created"] == stats["scopes_closed"] == stats["active_count"] == 0 and
            stats["errors"] == [], "LocalOnly UI should never execute/subscribe on native authority")
    return dict(status="passed", bounded_network_acceptance=True, native_owner_count=2, native_rows=len(server["cases"]),
                localonly_authority_inactive=True, local_ui_replication_claimed=False, foreign_local_ui_observed=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate_network({peer: json.loads((root / (peer + ".json")).read_text(encoding="utf-8-sig")) for peer in ("server", *PEERS)})))
