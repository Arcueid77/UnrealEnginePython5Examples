"""Natural authority Experience delivery and actual native inventory replicas."""
import argparse
import json
from pathlib import Path
from .initial_inventory_network_contract import validate as loadout_validate, server_gate as loadout_server, client_gate as loadout_client
from .inventory_ready_contract import check_ready, natural, scope, require


def server_gate(report):
    result = loadout_server(report); scope(report)
    require(report["native_net_mode"] == "DedicatedServer", "ready authority mode differs")
    require(report["owned_experience_proxies_created"] == 24, "ready authority native proxy count differs")
    for value in report["natural_startup_readiness"].values(): natural(value, True)
    for row in report["cases"]: check_ready(row); check_ready(row["owner_observation"])
    return result


def client_gate(report):
    result = loadout_client(report); scope(report); natural(report["natural_startup_readiness"], False)
    require(report["owned_experience_proxies_created"] == 12, "ready owner native proxy count differs")
    for row in report["cases"]: check_ready(row)
    return result


def validate(reports):
    result = loadout_validate(reports); server_gate(reports["server"])
    for peer in ("A", "B0"): client_gate(reports[peer])
    return dict(result, native_experience_ready_delivery=True, native_ready_authority_trials=24, pending_wait_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
