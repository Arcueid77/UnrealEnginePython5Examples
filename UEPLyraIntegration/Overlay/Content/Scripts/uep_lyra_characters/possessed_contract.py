"""Natural native possession, exact selected factory and complete wait regressions."""
import argparse
import json
from pathlib import Path
from .inventory_wait_contract import validate as wait_validate
from .initial_inventory_contract import require


def counts(value, profile, controller, *, proxies=()):
    py = profile == "Python"
    require({key: value[key] for key in ("python_calls", "fallback_calls", "authority_noops", "factories", "binds", "activations", "null_factories")} ==
        dict(python_calls=int(py), fallback_calls=int(not py), authority_noops=0, factories=int(py), binds=int(py), activations=int(py), null_factories=0),
        "native possession did not select exactly one Profile/factory/bind/activation")
    require(controller and value["last_controller"] == controller and (not py or value["last_proxy"]), "native possession controller payload/proxy differs")
    if proxies and py: require(value["last_proxy"] in proxies, "Python reported proxy is not the actual independently observed native factory")


def scope(report):
    require(report["experience_ready_factory_migrated"] is True and report["native_possession_ingress_tested"] is True and
        report["possession_event_manually_called_by_fixture"] is False and report["begin_play_business_migrated"] is False,
        "possession factory report scope/ingress differs")


def validate(report):
    result = wait_validate(report, factory_migrated=True); scope(report)
    counts(report["natural_startup_possession"], "Python", report["natural_startup_controller"])
    for row in report["readiness_transition_cases"]:
        require(row["possession_event_manually_called_by_fixture"] is False and row["native_possession_factory_proxies_created"] == 2 and
            row["native_possession_factory_proxies_collected"] is True and len(row["native_possession_factory_proxy_paths"]) == 2 and
            len(set(row["native_possession_factory_proxy_paths"])) == 2, "actual native owned possessions/proxy cleanup incomplete")
        require(row["native_controller_bootstrap_experience_proxies_collected"] is True and
            len(set(row["native_controller_bootstrap_experience_proxy_paths"])) == len(row["native_controller_bootstrap_experience_proxy_paths"]) and
            not set(row["native_controller_bootstrap_experience_proxy_paths"]) & set(row["native_possession_factory_proxy_paths"]),
            "native Controller bootstrap task identities/cleanup differ")
        counts(row["native_possession_counters"], row["profile"], row["native_possession_controller"], proxies=row["native_possession_factory_proxy_paths"])
        counts(row["old_owned_pawn_natural_python_factory"], "Python", row["native_possession_controller"], proxies=row["native_possession_factory_proxy_paths"])
    return dict(result, native_possession_factory_accepted=True, native_owned_possessions=24, begin_play_business_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
