"""Authority BP loadout calls, actual owner replicas, remote no-op and exact undo."""
import argparse
import json
from pathlib import Path
from .initial_inventory_contract import PLAN, require, expected, check_trial, natural_grant


def owner_trial(row, index):
    name, profile, definitions, occupied = PLAN[index]
    require((row["index"], row["name"], row["profile"]) == (index, name, profile) and row["replica_model"] == expected(index) and
        row["native_role"] == 2 and row["native_authority"] is False and row["bp_reference_call"] is True and
        row["native_inventory_before_after_unchanged"] is True and row["original_item_retained"] is True and
        row["added_definitions"] == sorted(definitions) and row["profile_configuration_cdo_restored"] is True,
        "loadout owner replica/remote guard/native identities differ")
    counts = row["counters"]
    require(counts["python_calls"] == int(profile == "Python") and counts["fallback_calls"] == int(profile == "BlueprintFallback") and
        counts["authority_noops"] == int(profile == "Python") and
        all(counts[key] == 0 for key in ("grant_calls", "slot_add_attempts", "slot_zero_requests", "missing_controller_noops", "missing_inventory_noops", "missing_quickbar_noops")),
        "non-authority owner attempted a native loadout mutation")


def server_gate(report):
    require(report["status"] == "passed" and not report.get("error") and len(report["cases"]) == 2*len(PLAN) and
        report["native_playing_gate"]["native_playing_phase"] is True and report["server_waited_for_client_process_exit"] is True and
        report["all_original_inventory_identities_restored"] is True and report["restore_frozen_before_release"] is True and report["gameplay_state_delivered_by_files"] is False and
        report["inventory_properties_written"] is False and report["whole_character_migrated"] is False and report["full_acceptance"] is False,
        "loadout authority matrix/restore/scope invalid")
    require(set(report["player_ids"]) == {"A", "B0"} and len(set(report["player_ids"].values())) == 2, "loadout real owners not distinct")
    for peer in ("A", "B0"): natural_grant(report["natural_startup_grants"][peer])
    for position, row in enumerate(report["cases"]):
        peer, index = ("A", "B0")[position//len(PLAN)], position % len(PLAN)
        check_trial(row, index); owner_trial(row["owner_observation"], index)
        require(row["peer"] == peer and row["index"] == index and row["authority_role"] == 3 and
            row["other_authority_owner_unchanged"] is True and row["owner_observation"]["replica_model"] == row["native_model"],
            "native loadout authority/owner replication/foreign isolation differs")
    return dict(status="passed", native_authority_trials=24, native_replica_trials=24)


def client_gate(report):
    require(report["status"] == "passed" and not report.get("error") and len(report["cases"]) == len(PLAN) and
        report["native_net_mode"] == "Client" and report["native_role"] == 2 and report["authority_phase_gate_observed"] is True and
        report["original_inventory_identities_restored"] is True and report["profile_configuration_cdo_restored"] is True and
        report["foreign_turn_own_inventory_unchanged"] is True and report["inventory_observers"] == dict(created=1, closed=1, active=0) and
        bool(report["native_inventory_signals"]) and report["signal_payload_owner_claimed"] is False and
        report["local_inventory_written"] is False and report["gameplay_state_delivered_by_files"] is False and report["whole_character_migrated"] is False and
        report["full_acceptance"] is False and report["network_acceptance"] is True,
        "loadout owner scope/native readiness/observation/restore differs")
    startup = report["natural_remote_startup"]
    require(startup["fallback_calls"] == startup["grant_calls"] == 0 and startup["authority_noops"] == startup["python_calls"] and
        (startup["last_call"] is None if startup["python_calls"] == 0 else
            startup["last_call"]["authority"] is False and startup["last_call"]["role"] in (1, 2)),
        "observed natural client loadout bypassed native authority guard")
    for index, row in enumerate(report["cases"]): owner_trial(row, index)
    return dict(status="passed", native_owner_trials=12)


def validate(reports):
    require(set(reports) == {"server", "A", "B0"}, "loadout needs server and two actual clients")
    server = reports["server"]; server_gate(server)
    for peer in ("A", "B0"):
        value = reports[peer]; client_gate(value)
        require(value["peer"] == peer and value["run_id"] == server["run_id"] and value["player_id"] == server["player_ids"][peer] and
            value["cases"] == [row["owner_observation"] for row in server["cases"] if row["peer"] == peer], "loadout owner/authority acknowledgements differ")
    return dict(status="passed", native_authority_trials=24, native_owner_replica_and_noop_trials=24,
        native_fastarray_quickbar_replication=True, signal_payload_owner_claimed=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
