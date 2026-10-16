"""Independent gate for LocalOnly decisions and native authoritative reloads."""
import argparse
import json
from pathlib import Path
from .autoreload_contract import PLAN, require, validate as validate_client

PEERS = ("A", "B0")


def validate(reports):
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["original_inventory_restored"] and
        server["server_waited_for_client_process_exit"] and server["native_playing_gate"]["native_playing_phase"] and
        server["fixture_authority_inventory_setup"], "AutoReload authority/restore/exit proof missing")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "inventory_properties_written", "local_only_authority_activation_called", "native_rpc_bypassed", "gameplay_event_replication_tested"):
        require(server[field] is False, "unsupported AutoReload network claim: "+field)
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "AutoReload owner IDs not distinct")
    for peer in PEERS:
        client = reports[peer]; validate_client(client)
        require((client["peer"], client["run_id"], client["player_id"]) == (peer, server["run_id"], server["player_ids"][peer]),
            "AutoReload client identity differs")
        for field in ("local_inventory_written", "gameplay_event_replication_tested", "native_rpc_bypassed", "packet_loss_tested", "travel_rejoin_tested"):
            require(client[field] is False, "client bypassed native authority or overclaimed network coverage")
    expected = [(peer, index) for peer in PEERS for index in range(len(PLAN)*2)]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "AutoReload authority matrix incomplete")
    for row in server["cases"]:
        peer, index = row["target"], row["index"]
        name = PLAN[index//2]
        require((row["name"], row["profile"]) == (name, ("BlueprintFallback", "Python")[index % 2]) and
            row["authoritative_role"] == 3 and row["other_inventory_unchanged"] and row["local_only_authority_stayed_inactive"] and
            row["authority_original_restored"], "AutoReload authority/foreign owner/LocalOnly/restore failed")
        client = reports[peer]["cases"][index//2]["python" if index % 2 else "blueprint"]
        ack = row["client"]
        require((ack["run_id"], ack["peer"], ack["index"]) == (server["run_id"], peer, index), "foreign AutoReload ack")
        expected_ack = {key: value for key, value in client.items() if key != "fixture_ammo_restored"}
        require(ack["row"] == expected_ack and row["authority_final_ammo"] == [client["final_magazine"], client["final_spare"]],
            "AutoReload authority ammo differs from independent owner observation")
        if name in ("empty-spare", "real-fire-auto-reload"):
            require(row["native_reload_active_observed"], "owner reload event did not activate native authority reload")
        if name == "real-fire-auto-reload":
            require(row["minimum_magazine"] == 0, "real input did not empty the authoritative magazine")
    stats = server["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [],
        "AutoReload authority/NPC shutdown scope leak")
    return dict(status="passed", bounded_network_acceptance=True, owners=2, native_authority_trials=len(expected),
        client_profile_pairs=len(PLAN)*2, gameplay_event_replication_tested=False, real_fire_to_empty_tested=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
