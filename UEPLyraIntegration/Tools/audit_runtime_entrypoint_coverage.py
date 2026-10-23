"""Compare ORIGINAL BP graph entries with native current default-profile inventory.

This is static reachability review, not proof that all gameplay paths ran.
It never imports project scripts, compiles/saves assets, or reads private bindings.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from blueprint_model import ENTRY_CLASSES, NON_BUSINESS_NODES, entry_name


def audit(original, coverage):
    blueprints = {item["path"]: item for item in original["blueprints"]}
    rows = []
    for asset in coverage["assets"]:
        bp = blueprints[asset["asset"]]
        profile = asset.get("profiles", {}).get(asset.get("effective_cdo_profile", asset.get("default_profile")), {})
        python = set(profile.get("functions", []))
        current_entries = {(row["graph"], row["entry"]): row for row in asset.get("staged_wired_entries", [])}
        for graph in bp["graphs"]:
            nodes = {node["id"]: node for node in graph["nodes"]}
            for entry in graph["nodes"]:
                if entry["class"] not in ENTRY_CLASSES:
                    continue
                name = entry_name(entry, graph)
                current = current_entries.get((graph["name"], name))
                connected = [link["node"] for pin in entry["pins"] if pin["direction"] == 1 and
                             pin["category"] == "exec" for link in pin["links"]]
                seen, pending = set(), list(connected)
                while pending:
                    key = pending.pop()
                    if key in seen or key not in nodes:
                        continue
                    seen.add(key)
                    pending.extend(link["node"] for pin in nodes[key]["pins"] if pin["direction"] == 1 and
                                   pin["category"] == "exec" for link in pin["links"])
                business = [nodes[key] for key in seen if nodes[key]["class"] not in NON_BUSINESS_NODES]
                # Pure functions have no execution pins; their result expression
                # is still business and cannot be called an empty event.
                if entry["class"] == "K2Node_FunctionEntry" and not any(pin["category"] == "exec" for pin in entry["pins"]):
                    business = [node for node in graph["nodes"] if node["class"] not in NON_BUSINESS_NODES]
                only_parent = bool(business) and all(node["class"] == "K2Node_CallParentFunction" for node in business)
                if name in python:
                    disposition = "python-routed"
                elif current is not None and current["calls_python_dispatch"]:
                    disposition = "staged-script-dispatch-forwarder-review"
                elif any(bridge["entry"] == name and bridge["default_profile"] == "Python" and
                         bridge["method"] in bridge["profiles"]["Python"]["functions"]
                         for bridge in asset.get("typed_dispatch_bridges", [])):
                    disposition = "staged-typed-script-dispatch-forwarder-review"
                elif current is not None and not current["reachable_execution_nodes"] and business:
                    disposition = "staged-disconnected-original-body-review"
                elif not business:
                    disposition = "no-connected-execution-business"
                elif only_parent:
                    disposition = "direct-parent-forwarder-review"
                else:
                    disposition = "unrouted-business-review"
                rows.append(dict(asset=asset["asset"], version=asset["version"], entry=name,
                    graph=graph["name"], entry_class=entry["class"], disposition=disposition,
                    native_router=asset.get("native_router_class"),
                    staged_entry=current,
                    reachable_execution_nodes=len(business),
                    node_titles=[node["title"].replace("\n", " ") for node in business],
                    node_classes=[node["class"] for node in business]))
    return dict(schema_version=1, status="review_complete", runtime_acceptance=False, full_acceptance=False,
        original_assets_modified=False, entrypoints=rows, counts=dict(Counter(row["disposition"] for row in rows)),
        limitations=["Original snapshot execution links, not a fresh graph audit or whole-dataflow proof",
                     "Unconnected events and direct parent forwarders are separately visible, not silently counted as migration",
                     "Internal generated delegate forwarding may be intentionally replaced by an owning Python subscription; review individually"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-audit", required=True)
    parser.add_argument("--native-coverage", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    files = [Path(args.original_audit).resolve(), Path(args.native_coverage).resolve()]
    report = audit(*(json.loads(file.read_text(encoding="utf-8-sig")) for file in files))
    report["input_hashes"] = {str(file): hashlib.sha256(file.read_bytes()).hexdigest() for file in files}
    Path(args.result).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(status=report["status"], counts=report["counts"], runtime_acceptance=False)))
    for row in report["entrypoints"]:
        if row["disposition"] == "unrouted-business-review":
            print(row["asset"], row["entry"], row["reachable_execution_nodes"], row["node_titles"][:5])
