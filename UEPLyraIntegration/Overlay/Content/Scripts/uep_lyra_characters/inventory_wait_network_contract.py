"""Existing real Experience/inventory replica matrix under full wait profile."""
import argparse
import json
from pathlib import Path
from .initial_inventory_network_contract import validate as loadout_validate, server_gate as loadout_server, client_gate as loadout_client
from .inventory_ready_contract import check_ready, natural, require
from .inventory_wait_contract import scope


def network_scope(report):
    scope(report)
    require(report["network_deferred_transitions_tested"] is False, "inventory replica lane cannot certify deferred transition replication")


def server_gate(report):
    result = loadout_server(report); network_scope(report)
    require(report["native_net_mode"] == "DedicatedServer" and report["owned_experience_proxies_created"] == 24, "wait authority native mode/request count differs")
    for value in report["natural_startup_readiness"].values(): natural(value, True)
    for row in report["cases"]: check_ready(row); check_ready(row["owner_observation"])
    return result


def client_gate(report):
    result = loadout_client(report); network_scope(report); natural(report["natural_startup_readiness"], False)
    require(report["owned_experience_proxies_created"] == 12, "wait owner native request count differs")
    for row in report["cases"]: check_ready(row)
    return result


def validate(reports):
    result = loadout_validate(reports); server_gate(reports["server"])
    for peer in ("A", "B0"): client_gate(reports[peer])
    return dict(result, pending_wait_profile_active=True, network_deferred_transitions_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
