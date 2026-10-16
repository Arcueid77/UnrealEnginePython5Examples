"""Independent native predicted Hero Heal authority/owner report gate."""
import argparse
import json
from pathlib import Path
from .hero_heal_contract import NETWORK_PLAN, require, validate as validate_client

PEERS = ("A", "B0")


def validate(reports):
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["original_player_states_restored"] and
        server["original_ability_specs_restored"] and server["server_waited_for_client_process_exit"] and
        server["native_playing_gate"]["native_playing_phase"] and server["fixture_authority_grant_and_health"], "Hero Heal native authority/restore/exit incomplete")
    require(server["authority_input_baseline_fixture"] and set(server["native_input_locks_suspended"]) == set(PEERS) and
        server["native_input_locks_suspended"] == server["native_input_locks_restored"] and
        all(type(count) is int and 0 <= count <= 16 for count in server["native_input_locks_suspended"].values()),
        "native authority input-stack fixture was not restored exactly")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "health_properties_written", "native_rpc_bypassed", "activation_handler_replayed", "task_callbacks_replayed", "animation_assets_modified",
        "original_montage_or_effect_written", "gameplay_event_replication_tested"):
        require(server[field] is False, "unsupported Hero Heal authority claim: "+field)
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "Hero Heal owner identities not distinct")
    for peer in PEERS:
        client = reports[peer]; validate_client(client, NETWORK_PLAN, network=True)
        require((client["peer"], client["run_id"], client["player_id"]) == (peer, server["run_id"], server["player_ids"][peer]), "Hero Heal owner identity differs")
        for field in ("local_health_written", "local_ability_granted", "native_rpc_bypassed", "gameplay_event_replication_tested", "packet_loss_tested", "travel_rejoin_tested"):
            require(client[field] is False, "Hero Heal client bypass/overclaim: "+field)
    expected = [(peer, index) for peer in PEERS for index in range(len(NETWORK_PLAN)*2)]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "Hero Heal authority matrix incomplete")
    for row in server["cases"]:
        peer, index = row["target"], row["index"]
        require((row["name"], row["profile"]) == (NETWORK_PLAN[index//2], ("BlueprintFallback", "Python")[index % 2]) and row["authoritative_role"] == 3,
            "Hero Heal authority case/profile/role mismatch")
        for field in ("native_active_observed", "native_effect_observed", "native_movement_lock_observed", "native_task_triple_observed",
            "foreign_owner_unchanged", "authority_movement_baseline_restored", "authority_original_restored", "native_first_heal_observed"):
            require(row[field], "Hero Heal authority native observation missing: "+field)
        require(row["authority_effects_after"] == row["authority_tasks_after"] == 0, "authority Hero Heal retained native tasks/effect")
        client = reports[peer]["cases"][index//2]["python" if index % 2 else "blueprint"]
        ack = row["client"]
        require((ack["run_id"], ack["peer"], ack["index"]) == (server["run_id"], peer, index), "foreign Hero Heal authority ack")
        require(ack["row"] == {key: value for key, value in client.items() if key != "fixture_health_restored"} and
            client["authority_health_confirmed"] and abs(row["authority_health"]-client["health_after"]) < .01, "Hero Heal owner/authority Health differs")
        if index % 2:
            stats = row["authority_counters"]
            require(stats["activations"] == stats["effects_applied"] == 1 and stats["tasks_created"] == 3 and
                stats["scopes_created"] == stats["scopes_closed"] == 1, "authority Hero Heal Python bypass/scope leak")
    stats = server["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [], "authority Hero Heal shutdown scope leak")
    return dict(status="passed", bounded_network_acceptance=True, native_authority_trials=len(expected), owners=2,
        client_profile_pairs=len(NETWORK_PLAN)*2, paused_world_network_tested=False, gameplay_event_replication_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
