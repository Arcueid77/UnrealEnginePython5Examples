"""Factory migration needs real proxy/callback proof, not Python counters alone."""
import argparse
import json
from pathlib import Path
from .team_observer_contract import validate as observer_validate, require


def check_factory(row):
    calls, py = row["calls"], row["profile"] == "Python"
    require(row["listener_counters"] == dict(python_calls=calls*int(py), fallback_calls=calls*int(not py), factories=calls*int(py),
        binds=calls*int(py), activations=calls*int(py), null_factories=0), "native selected listener factory/bind/activation decisions differ")


def check_startup(report):
    for value in report["natural_startup_python_dispatch"].values():
        counts = value["listener_factory_counters"]
        require(counts["python_calls"] >= 1 and counts["factories"] == counts["binds"] == counts["activations"] == counts["python_calls"] and
            counts["fallback_calls"] == counts["null_factories"] == 0, "natural native BeginPlay did not create/bind/activate through Python listener")


def validate(report):
    result = observer_validate(report, listener=True)
    for row in report["cases"]: check_factory(row)
    check_startup(report)
    return dict(result, listener_factory_orchestration_migrated=True, native_named_callback_no_python_closure=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
