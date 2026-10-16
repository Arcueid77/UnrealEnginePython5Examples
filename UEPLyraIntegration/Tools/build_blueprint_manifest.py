"""Build the complete agreed-scope inventory; no asset-name-prefix guessing."""

import argparse
import json
from pathlib import Path

from blueprint_model import summarize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    if audit.get("status") != "passed" or audit.get("errors"):
        raise RuntimeError("A complete successful graph audit is required")
    report = summarize(audit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "runtime_blueprint_count", "configuration_only_count", "retained_count", "migration_complete")}))


if __name__ == "__main__":
    main()
