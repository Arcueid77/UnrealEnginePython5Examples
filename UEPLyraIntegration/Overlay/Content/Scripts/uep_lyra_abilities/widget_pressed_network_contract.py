"""Actual two-owner LocalOnly UI contract; not replicated menu gameplay."""
import argparse
import json
from pathlib import Path
from .widget_pressed_contract import NETWORK_PLAN, TARGETS, CLASSES, require, validate

PEERS = ("A", "B0")
TRIALS = len(TARGETS) * len(NETWORK_PLAN) * 2


def validate_network(reports):
    require(set(reports) == {"server", *PEERS}, "pressed UI requires server and two real clients")
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["peer"] == "server" and bool(server["run_id"]) and
            server["native_context_ready"] and server["original_authority_states_restored"] and server["server_waited_for_client_process_exit"],
            "pressed native context/authority/exit proof incomplete")
    require([row["target"] for row in server["cases"]] == [peer for peer in PEERS for _ in range(TRIALS)], "pressed native owner matrix incomplete")
    ids = set()
    for peer in PEERS:
        owner, other = reports[peer], next(value for value in PEERS if value != peer)
        validate(owner, NETWORK_PLAN, False)
        require(owner["peer"] == peer and owner["run_id"] == server["run_id"] and owner["native_owner_role"] == 2 and
                owner["native_net_mode"] == "Client" and owner["player_id"] == server["player_ids"][peer], "pressed native client identity/role differs")
        ids.add(owner["player_id"])
        for field in ("packet_loss_tested", "travel_rejoin_tested", "gameplay_state_delivered_by_files", "localonly_ui_replication_claimed"):
            require(owner[field] is False, "unsupported pressed UI networking claim: " + field)
        initial = server["native_authority_initial_states"][peer]
        require(initial["role"] == 3 and len(initial["abilities"]) == 4 and
                sorted(row["cls"] for row in initial["abilities"]) == sorted([path for path in CLASSES.values() for _ in range(2)]) and
                all(not row["active"] and row["tasks"] == 0 and row["net"] == 1 for row in initial["abilities"]), "native LocalOnly authority initial state differs")
        passive_rows = owner["passive_held_observations"]
        require(len(passive_rows) == TRIALS and sorted(row["index"] for row in passive_rows) == list(range(TRIALS)), "every foreign local UI trial must be independently observed")
        for row in passive_rows:
            require((row["run_id"], row["peer"], row["target"], row["player_id"], row["stage"]) ==
                    (server["run_id"], peer, other, owner["player_id"], "held") and row["native_ability_count"] == 4 and
                    all(row[field] is True for field in ("native_owner_unchanged", "native_menu_empty", "native_all_inactive", "native_profiles_preserved", "native_specs_preserved")),
                    "foreign native local UI/ability/Profile/spec changed")
        rows = [row for row in server["cases"] if row["target"] == peer]
        for index, row in enumerate(rows):
            require((row["index"], row["ui_target"], row["name"], row["profile"]) ==
                    (index, TARGETS[index // (len(NETWORK_PLAN) * 2)], NETWORK_PLAN[(index // 2) % len(NETWORK_PLAN)], ("BlueprintFallback", "Python")[index % 2]),
                    "pressed native matrix order/source differs")
            require(row["authority_inactive_samples"] >= 2 and row["native_authority_unchanged"] and row["foreign_local_owner_observed"], "native authority/foreign-owner proof missing")
            ack, passive = row["client"], row["passive"]
            require((ack["run_id"], ack["peer"], ack["index"]) == (server["run_id"], peer, index) and
                    ack["row"] == owner["cases"][index // 2][("blueprint", "python")[index % 2]], "pressed native acknowledgement differs from final client observations")
            require(passive in reports[other]["passive_held_observations"], "server foreign-UI ack missing from actual foreign client report")
    require(len(ids) == 2, "pressed UI needs distinct real native player identities")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "activation_handler_replayed", "task_callbacks_replayed",
                  "packet_loss_tested", "travel_rejoin_tested", "gameplay_state_delivered_by_files", "localonly_ui_replication_claimed"):
        require(server[field] is False, "unsupported pressed authority claim: " + field)
    stats = server["policy_shutdown"]
    require(stats["activations"] == stats["fallback_activations"] == stats["scopes_created"] == stats["scopes_closed"] == stats["active_count"] == 0 and
            stats["errors"] == [], "LocalOnly pressed UI must not execute/subscribe on authority")
    return dict(status="passed", bounded_network_acceptance=True, native_owner_count=2, native_owner_trials=len(server["cases"]),
                native_localonly_authority_inactive=True, local_ui_replication_claimed=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate_network({peer: json.loads((root / (peer + ".json")).read_text(encoding="utf-8-sig")) for peer in ("server", *PEERS)})))
