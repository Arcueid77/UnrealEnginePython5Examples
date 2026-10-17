"""Fresh local nonreplicated bodies per world, not replicated owner ragdolls."""
import argparse
import json
from pathlib import Path
from .equipment_hide_network_contract import server_gate as hide_server, client_gate as hide_client, validate as hide_validate
from .ragdoll_contract import scope, native_body, counts
from .initial_inventory_contract import require, CLASS


def check(report):
    scope(report)
    require(report["ragdoll_caller_roots"] == dict(created=1, released=1) and report["ragdoll_physics_replication_tested"] is False and
        report["network_owner_death_ragdoll_ingress_tested"] is False and len(report["local_ragdoll_cases"]) == 2, "network Ragdoll local-only matrix/scope differs")
    for row, profile in zip(report["local_ragdoll_cases"], ("BlueprintFallback", "Python")):
        require(row["profile"] == profile and row["actual_character_class"] == CLASS and row["native_role"] == 3 and row["owned_team_proxies_created"] == 1,
            "local test Actor actual type/native role/observer count differs")
        for key in ("bp_reference_call", "test_owned_nonreplicated_local_actor", "actor_was_not_rooted", "owned_actor_destroyed",
            "owned_team_proxies_collected", "original_active_proxies_preserved", "ragdoll_quiet_after_destroy", "latent_script_quiet_after_destroy"):
            require(row[key] is True, "local network Ragdoll state/cleanup differs: "+key)
        counts(row["counters"], profile, 1); native_body(row["native_after"])


def server_gate(report): result = hide_server(report); check(report); return result
def client_gate(report): result = hide_client(report); check(report); return result
def validate(reports):
    result = hide_validate(reports); server_gate(reports["server"])
    for peer in ("A", "B0"): client_gate(reports[peer])
    return dict(result, native_local_network_ragdoll_calls=6, ragdoll_physics_replication_tested=False, network_owner_death_ragdoll_ingress_tested=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True); root = Path(parser.parse_args().directory)
    print(json.dumps(validate({peer: json.loads((root/(peer+".json")).read_text(encoding="utf-8-sig")) for peer in ("server", "A", "B0")})))
