"""Existing multiplayer regression only; new death-receiver ingress stays open."""
import argparse
import json
from pathlib import Path
from .ragdoll_network_contract import server_gate as ragdoll_server, client_gate as ragdoll_client, validate as ragdoll_validate
from .death_started_contract import scope
from .initial_inventory_contract import require


def check(report):
    scope(report)
    require(report["network_death_receiver_ingress_tested"] is False, "network regression cannot certify unexercised death ingress")


def server_gate(report): result = ragdoll_server(report); check(report); return result
def client_gate(report): result = ragdoll_client(report); check(report); return result
def validate(reports):
    result = ragdoll_validate(reports); server_gate(reports["server"])
    for peer in ("A", "B0"): client_gate(reports[peer])
    return dict(result, new_death_profile_multiplayer_regression=True, network_death_receiver_ingress_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
