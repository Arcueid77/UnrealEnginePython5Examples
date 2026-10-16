"""Independent real owner/authority reload gate, not a replicated event bus."""
import argparse
import json
from pathlib import Path
from .reload_magazine_contract import NETWORK_PLAN as PLAN, REFUSED, EARLY, require, validate as validate_client

PEERS = ("A", "B0")


def validate(reports):
    server = reports["server"]
    weapon = server.get("weapon", "pistol")
    if weapon != "pistol":
        require(server["equipped_fixture_states_restored"] and server["temporary_weapons_removed"] and
            set(server["native_weapon_fixtures"]) == set(PEERS) and
            all(state["weapon"] == weapon for state in server["native_weapon_fixtures"].values()), "native family equipment fixture not restored")
    if weapon == "netshooter":
        require(server["native_equipped_autoreload_grants"] == {peer: 0 for peer in PEERS}, "prototype authority AutoReload absence changed")
    require(server["status"] == "passed" and server["error"] is None and server["original_player_states_restored"] and
        server["server_waited_for_client_process_exit"] and server["native_playing_gate"]["native_playing_phase"] and
        server["fixture_authority_inventory_setup"], "native authority reload fixture/restore/exit incomplete")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "native_rpc_bypassed", "inventory_properties_written", "gameplay_event_replication_tested", "network_pause_tested", "ability_activation_called_by_probe"):
        require(server[field] is False, "unsupported native authority reload claim: "+field)
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "reload owner IDs not distinct")
    for peer in PEERS:
        owner = reports[peer]; validate_client(owner, authority=False, plan=PLAN)
        require(owner.get("weapon", "pistol") == weapon, "native owner/authority weapon family differs")
        require((owner["peer"], owner["run_id"], owner["player_id"], owner["native_net_mode"]) ==
            (peer, server["run_id"], server["player_ids"][peer], "Client"), "native reload client identity differs")
        for field in ("local_inventory_written", "native_rpc_bypassed", "gameplay_event_replication_tested", "packet_loss_tested", "travel_rejoin_tested", "network_pause_tested"):
            require(owner[field] is False, "native reload owner bypass/overclaim: "+field)
    require([(row["target"], row["index"]) for row in server["cases"]] ==
        [(peer, index) for peer in PEERS for index in range(len(PLAN)*2)], "native authority reload matrix incomplete")
    for row in server["cases"]:
        peer, index, name = row["target"], row["index"], row["name"]
        require(name == PLAN[index//2] and row["authoritative_role"] == 3 and row["foreign_owner_unchanged"] and
            row["authority_original_restored"] and row["native_ability_inactive"] and row["authority_tasks_after"] == 0 and
            row["authority_no_firing_after_end"] is False, "native authority reload role/foreign owner/end/tag/restore differs")
        owner = reports[peer]["cases"][index//2]["python" if index % 2 else "blueprint"]; ack = row["client"]
        require((ack["run_id"], ack["peer"], ack["index"]) == (server["run_id"], peer, index) and
            ack["row"] == {key: value for key, value in owner.items() if key != "fixture_ammo_restored"} and
            row["authority_final_ammo"] == owner["final_ammo"] and row["authority_inventory_model"] == owner["native_inventory_model"],
            "native authority ammo/equipment and replicated owner differ")
        stats = row["authority_counters"]
        if name in REFUSED:
            require(not row["authority_active_observed"] and stats["activations"] == stats["fallback_activations"] == 0 and
                row["authority_final_ammo"] == row["initial_ammo"], "client-refused reload mutated/activated native authority")
            continue
        require(row["authority_active_observed"] and row["authority_tasks_observed"] == 2 and row["authority_montage_playing_observed"] and
            row["authority_expected_no_firing_observed"] and row["held_barrier_published"], "native authority reload task/montage/tag/barrier missing")
        if index % 2:
            require(stats["activations"] == stats["scopes_created"] == stats["scopes_closed"] == stats["native_ends"] == 1 and
                stats["tasks_created"] == 2 and stats["authority_reloads"] == int(name not in EARLY) and stats["client_events"] == 0,
                "native authority Python reload/task/end decision bypassed")
        else:
            require(stats["fallback_activations"] == stats["fallback_native_ends"] == 1 and stats["fallback_reloads"] == int(name not in EARLY),
                "retained original authority BP reload/End bypassed")
    final = server["policy_shutdown"]
    require(final["active_count"] == 0 and final["scopes_created"] == final["scopes_closed"] and final["errors"] == [], "authority reload scope/error leak")
    return dict(status="passed", bounded_network_acceptance=True, owners=2, native_authority_trials=len(PLAN)*4,
        client_profile_pairs=len(PLAN)*2, gameplay_event_replication_tested=False, network_pause_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
