"""Independent native client-prediction/authority-inventory DropWeapon gate."""
import argparse
import json
from pathlib import Path
from .drop_weapon_contract import PLAN, require, validate as validate_client

PEERS = ("A", "B0")


def validate(reports):
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["original_inventory_restored"] and
        server["server_waited_for_client_process_exit"] and server["native_playing_gate"]["native_playing_phase"] and server["fixture_authority_inventory_setup"],
        "DropWeapon authority fixture/restore/exit incomplete")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "native_rpc_bypassed", "inventory_properties_written", "gameplay_event_replication_tested"):
        require(server[field] is False, "unsupported DropWeapon authority claim: "+field)
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "DropWeapon owner IDs not distinct")
    for peer in PEERS:
        client = reports[peer]; validate_client(client, authority=False)
        require((client["peer"], client["run_id"], client["player_id"], client["native_net_mode"]) ==
            (peer, server["run_id"], server["player_ids"][peer], "Client"), "DropWeapon native client identity differs")
        for field in ("local_inventory_written", "native_rpc_bypassed", "gameplay_event_replication_tested", "packet_loss_tested", "travel_rejoin_tested"):
            require(client[field] is False, "DropWeapon client bypass or overclaim: "+field)
    expected = [(peer, index) for peer in PEERS for index in range(len(PLAN)*2)]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "DropWeapon authority matrix incomplete")
    for row in server["cases"]:
        peer, index = row["target"], row["index"]
        name, count, initial, expected_slot = PLAN[index//2]
        require(row["name"] == name and row["expected_slot"] == expected_slot and row["authoritative_role"] == 3, "DropWeapon role/case/slot differs")
        for field in ("foreign_owner_unchanged", "removed_item_absent", "dropped_slot_empty", "original_item_identities_preserved", "native_ability_inactive", "authority_original_restored"):
            require(row[field], "DropWeapon native authority observation missing: "+field)
        client = reports[peer]["cases"][index//2]["python" if index % 2 else "blueprint"]; ack = row["client"]
        require((ack["run_id"], ack["peer"], ack["index"]) == (server["run_id"], peer, index) and
            ack["row"] == {key: value for key, value in client.items() if key != "fixture_original_restored"} and
            row["authority_inventory_model"] == client["inventory_model"], "DropWeapon native authority/replicated owner equipment differs")
        stats = row["authority_counters"]
        if index % 2:
            require(stats["activations"] == stats["authority_branches"] == stats["cycles"] == stats["native_ends"] == 1 and
                stats["items_removed"] == int(count > 0) and stats["client_branches"] == 0, "authority Python inventory path/end was bypassed")
        else:
            require(stats["fallback_activations"] == stats["fallback_native_ends"] == 1 and
                client["counters"]["fallback_activations"] == client["counters"]["fallback_native_ends"] == 1, "retained BP native activation/end not observed")
    require(server["policy_shutdown"]["active_count"] == 0 and server["policy_shutdown"]["errors"] == [], "authority DropWeapon active/error leak")
    return dict(status="passed", bounded_network_acceptance=True, owners=2, native_authority_trials=len(expected),
        client_profile_pairs=len(PLAN)*2, gameplay_event_replication_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
