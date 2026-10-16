"""Two real owner BP calls, local GameplayEvents and native QuickBar RPC results."""
import argparse
import json
from pathlib import Path
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from .quickbar_input_contract import PLAN, validate as client_gate


def server_gate(report):
    require(report["status"] == "passed" and not report.get("error") and len(report["cases"]) == 2*len(PLAN),
        "Character slot authority matrix incomplete")
    require(report["native_playing_gate"]["native_playing_phase"] is True and report["server_waited_for_client_process_exit"] is True and
        report["original_inventory_restored"] is True and report["server_character_helpers_not_invoked"] is True and
        report["native_rpc_bypassed"] is False and report["gameplay_state_delivered_by_files"] is False,
        "Character slot native authority/restore/exit scope invalid")
    require(set(report["player_ids"]) == {"A", "B0"} and len(set(report["player_ids"].values())) == 2,
        "Character slot real owners not distinct")
    for position, row in enumerate(report["cases"]):
        peer, index = ("A", "B0")[position//len(PLAN)], position % len(PLAN)
        require(row["peer"] == peer and row["index"] == index and row["authority_role"] == 3 and
            row["other_owner_inventory_unchanged"] is True and row["authority_inventory"] == row["client"]["inventory"] and
            row["authority_inventory"]["active"] == PLAN[index][5], "Character slot native RPC/foreign-owner model differs")
    return dict(status="passed", authority_trials=2*len(PLAN))


def validate(reports):
    require(set(reports) == {"server", "A", "B0"}, "Character slot needs server and two actual clients")
    server = reports["server"]; server_gate(server)
    for peer in ("A", "B0"):
        report = reports[peer]; client_gate(report)
        require(report["run_id"] == server["run_id"] and report["peer"] == peer and
            report["player_id"] == server["player_ids"][peer] and report["native_role"] == 2 and report["native_net_mode"] == "Client" and
            report["authority_phase_gate_observed"] is True and report["network_acceptance"] is True and
            report["local_inventory_written"] is False and report["gameplay_state_delivered_by_files"] is False,
            "Character slot owner/native network context differs")
        authority = [row for row in server["cases"] if row["peer"] == peer]
        require([row["client"] for row in authority] == report["cases"], "Character slot client/authority report acknowledgement differs")
    return dict(status="passed", authority_trials=28, owner_trials=28, native_quickbar_rpc=True,
        gameplay_event_replication_claimed=False, hardware_input_tested=False, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
