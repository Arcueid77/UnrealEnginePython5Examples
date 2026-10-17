"""Local native calls on server/owners, not transient hidden-flag replication."""
import argparse
import json
from pathlib import Path
from .begin_play_network_contract import server_gate as begin_server, client_gate as begin_client, validate as begin_validate
from .equipment_hide_contract import scope, network_row
from .initial_inventory_contract import require


def check(report, authority):
    scope(report)
    require(report["equipment_hide_caller_roots"] == dict(created=1, released=1) and report["equipment_hide_replication_tested"] is False and
        report["network_death_hide_ingress_tested"] is False, "native equipment-hide network scope/caller cleanup differs")
    targets = ("A", "B0") if authority else (report["peer"],)
    expected = [(target, profile) for target in targets for profile in ("BlueprintFallback", "Python")]
    require(len(report["network_equipment_hide_cases"]) == len(expected), "native network equipment-hide local case matrix incomplete")
    for row, (target, profile) in zip(report["network_equipment_hide_cases"], expected):
        network_row(row, target, profile); require(row["native_role"] == (3 if authority else 2), "native equipment-hide actual Role differs")


def server_gate(report): result = begin_server(report); check(report, True); return result
def client_gate(report): result = begin_client(report); check(report, False); return result
def validate(reports):
    result = begin_validate(reports); server_gate(reports["server"])
    for peer in ("A", "B0"): client_gate(reports[peer])
    return dict(result, local_native_network_equipment_hide_calls=8, equipment_hide_replication_tested=False, network_death_hide_ingress_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
