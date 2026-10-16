"""Native Reset owner identity, authority filtering and reliable completion gate."""
import argparse
import json
from pathlib import Path
from .auto_respawn_helpers_contract import require
from .auto_respawn_events_contract import check_messages
from .auto_respawn_reset_contract import PLAN, check_row

PEERS, TRIALS = ("A", "B0"), len(PLAN)*2


def validate(reports):
    require(set(reports) == {"server", *PEERS}, "native Reset needs two real clients")
    server = reports["server"]
    require(server["server_waited_for_client_process_exit"] is True and server["all_owners_restored"] is True and
        server["owners_restored_before_client_release"] is True and server["native_playing_gate"]["native_playing_phase"] is True,
        "Reset authority Playing/restoration/exit barrier missing")
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2,
        "native Reset owners are not distinct")
    require(set(server["owner_restoration"]) == set(PEERS) and all(set(row) == {"profile", "specs", "delay", "alive"} and
        all(value is True for value in row.values()) for row in server["owner_restoration"].values()), "native Reset authority owners not restored")
    for peer, report in reports.items():
        require(report["status"] == "passed" and report["error"] is None and report["peer"] == peer and report["run_id"] == server["run_id"] and
            report["network_acceptance"] is True and report["native_reset_producer_tested"] is True and report["reset_broadcast_by_fixture"] is False and
            report["full_auto_respawn_acceptance"] is False and report["original_profile_restored"] is True and report["original_specs_restored"] is True and
            report["gameplay_state_delivered_by_files"] is False and report["native_rpc_bypassed"] is False,
            "native Reset peer evidence/restoration/scope differs")
        require(report["observer_shutdown"] == dict(created=TRIALS*2, closed=TRIALS*2, active=0), "native Reset message scopes leaked")
    expected = [(target, index) for target in PEERS for index in range(TRIALS)]
    require([(row["target"], row["index"]) for row in server["cases"]] == expected, "native Reset authority matrix incomplete")
    for peer in PEERS:
        client = reports[peer]
        require(client["player_id"] == server["player_ids"][peer] and client["native_net_mode"] == "Client" and
            client["local_reset_requests"] == 0 and client["local_damage_applied"] is False and client["authority_phase_gate_observed"] is True,
            "Reset client fabricated authority work or ownership")
        require([(row["target"], row["index"]) for row in client["cases"]] == [(peer, index) for index in range(TRIALS)],
            "native Reset owning client matrix incomplete")
        other = PEERS[1] if peer == PEERS[0] else PEERS[0]
        foreign = client["foreign_cases"]
        require([(row["position"], row["target"]) for row in foreign] == [(position, target) for position, (target, index) in enumerate(expected) if target == other],
            "native Reset passive foreign client matrix incomplete")
        for row in foreign:
            require(row["local_owner_unchanged"] is True and row["observer_closed"] is True and row["reset_messages"] == [] and
                all(count == 0 for count in row["activation_counters"].values()),
                "foreign client received replicated Reset router payload or changed local owner lifetime")
            check_messages(row["event_messages"], server["player_ids"][other], completion=True, foreign=True, duration_expected=False)
    for position, row in enumerate(server["cases"]):
        peer, index = expected[position]
        profile, name = ("BlueprintFallback", "Python")[index % 2], PLAN[index//2]
        require((row["position"], row["name"], row["profile"], row["player_id"]) == (position, name, profile, server["player_ids"][peer]) and
            row["foreign_owner_unchanged"] is True, "Reset authority trial identity/foreign state differs")
        check_row(row, server=True)
        foreign_stats = row["foreign_activation_counters"]
        require(foreign_stats["reset_messages"] == foreign_stats["foreign_resets"] == int(profile == "Python") and
            foreign_stats["fallback_reset_messages"] == int(profile == "BlueprintFallback") and foreign_stats["resets_handled"] ==
            foreign_stats["native_reset_starts"] == foreign_stats["native_reset_cancelled"] == foreign_stats["removed"] == foreign_stats["fallback_removed"] == 0,
            "server foreign ability did not filter exactly one real native Reset")
        client = reports[peer]["cases"][index]
        require((client["position"], client["name"], client["profile"], client["player_id"]) == (position, name, profile, server["player_ids"][peer]),
            "native Reset owner case identity differs")
        check_row(client, owner_client=True)
        for record, other_report in ((row["owner_ack"], client), (row["foreign_ack"], next(
            value for value in reports[PEERS[1] if peer == PEERS[0] else PEERS[0]]["foreign_cases"] if value["position"] == position))):
            expected_peer = peer if other_report is client else (PEERS[1] if peer == PEERS[0] else PEERS[0])
            require(record["run_id"] == server["run_id"] and record["peer"] == expected_peer and record["position"] == position and record["row"] == other_report,
                "Reset ack does not match independently read peer report")
        if index % 2: require(server["cases"][position-1]["specs_at_restart"] == row["specs_at_restart"], "native Reset raw BP/Python authority model differs")
    return dict(status="passed", native_reset_producer_tested=True, owners=2, authority_trials=len(expected), owner_trials=len(expected),
        passive_foreign_client_observations=len(expected), reset_router_payload_replicated_to_foreign_client=False, full_auto_respawn_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server",)+PEERS})))
