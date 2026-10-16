"""Independent native authority plus two actual local ADS UI/input owners."""
import argparse
import json
from pathlib import Path
from .ads_contract import NETWORK_PLAN as PLAN, require, validate as validate_client

PEERS = ("A", "B0")


def validate(reports):
    server = reports["server"]
    require(server["status"] == "passed" and server["error"] is None and server["original_player_states_restored"] and
        server["server_waited_for_client_process_exit"] and server["native_playing_gate"]["native_playing_phase"], "native ADS authority/restore/exit incomplete")
    for field in ("full_acceptance", "packaged_runtime", "physical_input_tested", "callback_replay", "authoritative_movement_written",
        "native_rpc_bypassed", "camera_or_speed_written_by_probe", "mapping_context_written_by_probe", "ui_message_replication_tested"):
        require(server[field] is False, "unsupported ADS network claim: "+field)
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "ADS owners not distinct")
    for peer in PEERS:
        client = reports[peer]; validate_client(client, PLAN)
        require((client["peer"], client["run_id"], client["player_id"], client["native_net_mode"]) ==
            (peer, server["run_id"], server["player_ids"][peer], "Client"), "ADS native owner identity/mode differs")
        for field in ("local_camera_speed_mapping_written_by_probe", "ui_message_replication_tested", "native_rpc_bypassed", "packet_loss_tested", "travel_rejoin_tested"):
            require(client[field] is False, "ADS client bypass or overclaim: "+field)
        require(client["paused_world_scope"] == "standalone only; network pause not tested", "network/global pause overclaimed")
    expected = [(peer, index) for peer in PEERS for index in range(len(PLAN)*2)]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "ADS authority matrix incomplete")
    for row in server["cases"]:
        peer, index = row["target"], row["index"]
        require(row["name"] == PLAN[index//2] and row["authoritative_role"] == 3 and row["authority_tasks_after"] == 0, "ADS authority role/name/task cleanup differs")
        for field in ("native_active_observed", "native_half_speed_observed", "native_camera_mode_observed", "native_wait_task_observed", "foreign_owner_unchanged", "authority_original_restored"):
            require(row[field], "native ADS authority observation missing: "+field)
        client = reports[peer]["cases"][index//2]["python" if index % 2 else "blueprint"]
        ack = row["client"]
        require((ack["run_id"], ack["peer"], ack["index"]) == (server["run_id"], peer, index) and ack["row"] == client,
            "native ADS acknowledgement differs from independently checked owner")
        stats = row["authority_counters"]
        require(stats["ui_on"] == stats["ui_off"] == stats["mappings_added"] == stats["mappings_removed"] == 0,
            "dedicated authority incorrectly executed local UI/mapping business")
        if index % 2:
            require(stats["activations"] == stats["tasks_created"] == stats["scopes_created"] == stats["scopes_closed"] == 1,
                "authority ADS Python activation/task scope bypass or leak")
    stats = server["policy_shutdown"]
    require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and stats["errors"] == [] and
        stats["helpers_rooted"] == stats["helpers_unrooted"] == 0, "native ADS authority/local-only helper leak")
    return dict(status="passed", bounded_network_acceptance=True, owners=2, native_authority_trials=len(expected),
        client_profile_pairs=len(PLAN)*2, ui_message_replication_tested=False, network_pause_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
