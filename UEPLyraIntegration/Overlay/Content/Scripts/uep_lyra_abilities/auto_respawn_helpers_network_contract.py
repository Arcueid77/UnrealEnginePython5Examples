"""Independent authority/owner/foreign-owner AutoRespawn helper report gate."""
import argparse
import json
from pathlib import Path
from .auto_respawn_helpers_contract import NETWORK_PLAN, FALSE_FLAGS, require, validate_row, validate_pair

PEERS, TRIALS = ("A", "B0"), len(NETWORK_PLAN)*2


def validate(reports, *, event_business=False):
    require(set(reports) == {"server", *PEERS}, "two real AutoRespawn clients required")
    server = reports["server"]
    require(server["server_waited_for_client_process_exit"] and server["all_owners_restored"] and server["owners_restored_before_client_release"] and
        server["native_playing_gate"]["native_playing_phase"], "authority Playing/restore/exit barrier missing")
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "native AutoRespawn owner identities not distinct")
    require(set(server["owner_restoration"]) == set(PEERS) and all(set(row) == {"profile", "specs", "delay", "alive"} and
        all(value is True for value in row.values()) for row in server["owner_restoration"].values()), "native owner restoration incomplete")
    for peer, report in reports.items():
        require(report["status"] == "passed" and report["error"] is None and report["network_acceptance"] and
            report["original_profile_restored"] and report["original_specs_restored"] and report["real_lethal_gas_damage"], "native helper peer report incomplete")
        require(report["peer"] == peer and report["run_id"] == server["run_id"], "wrong native helper peer/run identity")
        for field in FALSE_FLAGS+("gameplay_state_delivered_by_files", "native_rpc_bypassed", "packet_loss_tested", "travel_rejoin_tested"):
            expected_flag = event_business if field == "death_listener_timer_restart_business_migrated" else False
            require(report[field] is expected_flag, "unsupported helper network claim: "+field)
    expected = [(peer, index) for peer in PEERS for index in range(TRIALS)]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "native helper authority matrix incomplete")
    for peer in PEERS:
        client = reports[peer]
        require(client["player_id"] == server["player_ids"][peer] and client["native_net_mode"] == "Client" and
            client["local_damage_applied"] is False and client["local_ability_activation_called"] is False and
            client["authority_phase_gate_observed"] is True, "client bypassed native authority/readiness")
        require([(row["target"], row["index"]) for row in client["cases"]] == [(peer, index) for index in range(TRIALS)], "owning native helper cases incomplete")
        other = PEERS[1] if peer == PEERS[0] else PEERS[0]
        foreign = client["foreign_cases"]
        require([(row["position"], row["target"]) for row in foreign] == [(position, target) for position, (target, index) in enumerate(expected) if target == other] and
            all(row["local_owner_unchanged"] is True for row in foreign), "foreign local helper/Profile/spec observation missing")
    for position, row in enumerate(server["cases"]):
        peer, index = expected[position]; name, profile = NETWORK_PLAN[index//2], ("BlueprintFallback", "Python")[index % 2]
        require((row["position"], row["name"], row["profile"]) == (position, name, profile) and row["foreign_owner_unchanged"] is True, "authority helper identity/isolation differs")
        validate_row(row, name, profile, authority=True, auto_active_required=False)
        client = reports[peer]["cases"][index]
        require((client["position"], client["name"], client["profile"]) == (position, name, profile), "owner/helper scheduling differs")
        validate_row(client, name, profile, authority=False, auto_active_required=False)
        if index % 2:
            validate_pair(server["cases"][position-1], row)
            validate_pair(reports[peer]["cases"][index-1], client)
        ack = row["owner_ack"]
        require((ack["run_id"], ack["peer"], ack["position"], ack["index"]) == (server["run_id"], peer, position, index) and
            ack["row"] == client, "authority ack does not match the independently read owner report")
        other = PEERS[1] if peer == PEERS[0] else PEERS[0]
        foreign_ack = row["foreign_ack"]
        foreign = next(value for value in reports[other]["foreign_cases"] if value["position"] == position)
        require((foreign_ack["run_id"], foreign_ack["peer"], foreign_ack["position"]) == (server["run_id"], other, position) and
            foreign_ack["row"] == foreign, "foreign-owner ack/report mismatch")
    return dict(status="passed", bounded_network_acceptance=True, authority_trials=len(expected), owners=2,
        owner_trials=len(expected), foreign_owner_observations=len(expected), whole_auto_respawn_migrated=False,
        paused_network_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
