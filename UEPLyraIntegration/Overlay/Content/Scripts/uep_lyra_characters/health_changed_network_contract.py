"""Actual authority GAS -> replicated health delegates in two separate clients."""
import argparse
import json
from pathlib import Path
from .health_changed_contract import NAMES, check_case, cleanup_gate, require

PEERS = ("A", "B0")
PLAN = [(name, profile) for name in (*NAMES, "player-B0-self", "player-B0-foreign") for profile in ("BlueprintFallback", "Python")]


def validate(server, a, b):
    reports = {"server": server, "A": a, "B0": b}; run = server["run_id"]
    require(server["server_waited_for_client_process_exit"] is True and server["all_cleanup_frozen_before_release"] is True, "health peers did not freeze cleanup/exit server last")
    require(set(server["player_ids"]) == set(PEERS) and len(set(server["player_ids"].values())) == 2, "two real health player identities missing")
    for peer, report in reports.items():
        authority = peer == "server"
        require(report["status"] == "passed" and not report.get("error") and report["peer"] == peer and report["run_id"] == run and
            report["network_acceptance"] is True and report["native_net_mode"] == ("DedicatedServer" if authority else "Client") and
            len(report["cases"]) == len(PLAN), "health native multi-process reports incomplete")
        for row, expected in zip(report["cases"], PLAN): check_case(row, expected, authority=authority, actor_keys=("A", "B0", "AI"))
        cleanup_gate(report, ("A", "B0", "AI"), owned=authority)
        require(report["cleanup"]["observer"]["sense_deliveries"] == (4 if authority else 0), "native health sense callbacks leaked across authority")
        require(report["cleanup"]["observer"]["health_deliveries"] == 30, "primary/prime/restore native health replica delegates missing or duplicated")
        if not authority:
            require(report["player_id"] == server["player_ids"][peer], "health local client identity differs")
            for row in report["cases"]:
                require(row["actors"][peer]["native_role"] == 2 and all(row["actors"][key]["native_role"] == 1 for key in ("A", "B0", "AI") if key != peer), "native local/foreign health roles differ")
    return dict(status="passed", authority_native_gas_trials=len(PLAN), client_native_health_observations=len(PLAN)*2,
        authority_native_damage_stimuli=4, independent_health_replication_and_authority_guards=True, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate(*(json.loads((root/(name+".json")).read_text(encoding="utf-8-sig")) for name in ("server", "A", "B0")))))
