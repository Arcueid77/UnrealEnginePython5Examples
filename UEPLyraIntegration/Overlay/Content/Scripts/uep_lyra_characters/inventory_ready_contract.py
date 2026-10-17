"""Immediate branch/native inventory; deferred wait is explicitly still BP."""
import argparse
import json
from pathlib import Path
from .initial_inventory_contract import validate as loadout_validate, require


def counts(*, py=0, fallback=0, immediate=0, pending=0):
    return dict(python_calls=py, fallback_calls=fallback, immediate_grants=immediate, original_wait_fallbacks=pending,
        missing_controller=pending, missing_inventory=0, missing_quickbar=0)


def check_ready(row):
    py = row["profile"] == "Python"
    require(row["readiness_counters"] == counts(py=int(py), fallback=int(not py), immediate=int(py)) and row["real_experience_factory_signal"] is True, "ready continuation did not select actual native Experience signal/immediate inventory forwarding")


def natural(value, authority):
    if not authority:
        require(value == counts(), "native remote startup unexpectedly received authority-only ExperienceReady continuation")
        return
    require(value["python_calls"] >= 1 and value["fallback_calls"] == 0 and value["python_calls"] == value["immediate_grants"]+value["original_wait_fallbacks"],
        "natural ExperienceReady did not enter selected Python continuation")


def scope(report):
    require(report["experience_callback_manually_called_by_typed_bp"] is False and report["native_experience_factory_signal_tested"] is True and report["experience_ready_factory_migrated"] is False and
        report["pending_inventory_wait_migrated"] is False and report["immediate_inventory_ready_branch_migrated"] is True,
        "ready branch report overclaims original factory/deferred wait migration")
    require(report["caller_roots"] == dict(created=1, released=1), "ready typed BP caller root leaked")
    require(report["owned_experience_proxies_collected"] is True, "owned native ExperienceReady proxies survived engine GC")


def validate(report):
    result = loadout_validate(report)
    for row in report["cases"]: check_ready(row)
    natural(report["natural_startup_readiness"], True); scope(report)
    require(report["owned_experience_proxies_created"] == 14, "native ExperienceReady request matrix differs")
    require(len(report["deferred_original_cases"]) == 2, "ready deferred original wait controls missing")
    for row, profile in zip(report["deferred_original_cases"], ("BlueprintFallback", "Python")):
        py = profile == "Python"
        require(row["profile"] == profile and row["readiness_counters"] == counts(py=int(py), fallback=int(not py), pending=int(py)) and
            row["no_inventory_grant_while_controller_missing"] is True and row["owned_actor_destroyed"] is True and
            row["no_callbacks_or_grants_after_destroy_and_engine_ticks"] is True and row["original_live_proxies_preserved"] is True and
            row["owned_startup_proxies_collected"] is True and row["actor_was_not_rooted"] is True,
            "ready deferred original wait/destruction comparison differs")
    return dict(result, native_experience_ready_delivery=True, native_experience_requests=14, native_original_pending_wait_controls=2, pending_wait_migrated=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
