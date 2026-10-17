"""Same native three-world observer matrix plus selected factory ownership."""
import argparse
import json
from pathlib import Path
from .team_observer_network_contract import validate as observer_validate
from .team_listener_contract import check_factory, check_startup


def validate(server, a, b):
    result = observer_validate(server, a, b, listener=True)
    for report in (server, a, b):
        for row in report["cases"]: check_factory(row)
        check_startup(report)
    return dict(result, listener_factory_orchestration_migrated=True, native_named_callback_no_python_closure=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--directory", required=True)
    root = Path(parser.parse_args().directory)
    print(json.dumps(validate(*(json.loads((root/(name+".json")).read_text(encoding="utf-8-sig")) for name in ("server", "A", "B0")))))
