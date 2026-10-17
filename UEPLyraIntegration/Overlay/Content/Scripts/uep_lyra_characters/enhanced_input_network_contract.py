"""Two real input owners -> native RPC/equipment, never file-delivered gameplay."""
import argparse
import json
from pathlib import Path
from .enhanced_input_contract import ACTIONS, PLAN, check_trial, report_cleanup, require

PEERS = ("A", "B0")


def validate(server, a, b):
    require(server["status"] == "passed" and not server.get("error") and len(server["cases"]) == 2*len(PLAN) and
        server["server_waited_for_client_process_exit"] is True and server["all_cleanup_frozen_before_release"] is True and
        server["original_inventory_restored"] is True and server["server_character_receivers_and_helpers_not_invoked"] is True and
        server["native_rpc_bypassed"] is False and server["gameplay_state_delivered_by_files"] is False and server["full_acceptance"] is False,
        "native EnhancedInput server matrix/cleanup incomplete")
    require(len(set(server["player_ids"].values())) == 2, "input owners are not distinct")
    for peer, client in zip(PEERS, (a, b)):
        require(client["status"] == "passed" and not client.get("error") and client["peer"] == peer and client["run_id"] == server["run_id"] and
            client["player_id"] == server["player_ids"][peer] and client["native_net_mode"] == "Client" and client["native_role"] == 2 and len(client["cases"]) == len(PLAN), "native input client identity/role/report incomplete")
        require(client["native_input_bindings"] == server["native_input_bindings"] and set(client["native_input_bindings"]) == set(ACTIONS), "native input compiled bindings differ between processes")
        require(client["native_profile_method_counts"] == dict(Python=17, BlueprintFallback=12), "client original fallback/profile function set differs")
        for index, (row, expected) in enumerate(zip(client["cases"], PLAN)):
            require(row["native_bound_receiver"] == client["native_input_bindings"][row["action"]], "client actual native binding symbol differs")
            check_trial(row, expected)
            authority = server["cases"][PEERS.index(peer)*len(PLAN)+index]
            require(authority["peer"] == peer and authority["index"] == index and authority["authority_role"] == 3 and
                authority["other_owner_inventory_unchanged"] is True and authority["authority_inventory"] == row["inventory"] and
                row["foreign_actor_input_and_helper_counters_unchanged"] is True, "input native RPC/foreign owner isolation differs")
        report_cleanup(client)
    return dict(status="passed", native_input_owner_trials=2*len(PLAN), original_python_pairs=16, native_rpc_equipment_and_foreign_isolation=True, physical_keyboard_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate(*(json.loads((root/(name+".json")).read_text(encoding="utf-8-sig")) for name in ("server", "A", "B0")))))
