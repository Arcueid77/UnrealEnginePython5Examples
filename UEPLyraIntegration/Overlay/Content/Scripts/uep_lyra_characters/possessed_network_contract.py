"""Actual authority possession; clients do not invent server-only ingress."""
import argparse
import json
from pathlib import Path
from .inventory_wait_network_contract import server_gate as wait_server, client_gate as wait_client, validate as wait_validate
from .possessed_contract import counts, scope
from .initial_inventory_contract import require


def server_gate(report):
    result = wait_server(report, factory_migrated=True); scope(report)
    require(set(report["natural_startup_possession"]) == {"A", "B0"}, "native possession authority players missing")
    for peer, value in report["natural_startup_possession"].items(): counts(value, "Python", report["natural_startup_controllers"][peer])
    return result


def client_gate(report):
    result = wait_client(report, factory_migrated=True); scope(report)
    value = report["natural_startup_possession"]
    require(all(value[key] == 0 for key in ("python_calls", "fallback_calls", "authority_noops", "factories", "binds", "activations", "null_factories")) and
        value["last_controller"] is value["last_proxy"] is None, "client invented native server-only ReceivePossessed/factory ingress")
    return result


def validate(reports):
    result = wait_validate(reports, factory_migrated=True); server_gate(reports["server"])
    for peer in ("A", "B0"): client_gate(reports[peer])
    return dict(result, native_authority_possession_factory=True, client_possession_event_invented=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
