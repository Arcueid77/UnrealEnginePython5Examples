"""Compare ORIGINAL BP graph entries with the native effective-profile inventory.

This is static reachability review, not proof that all gameplay paths ran.
It never imports project scripts, compiles/saves assets, or reads private bindings.
"""
import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
from blueprint_model import ENTRY_CLASSES, NON_BUSINESS_NODES, entry_name


class NativeCallInventory:
    """Find source call witnesses; a witness does not prove runtime execution.

    Only the native snapshot's qualified call targets are followed. Unknown
    owners, ambiguous entries and missing profiles cannot borrow another
    class's same-named method. A child definition shadows its parent.
    """

    def __init__(self, coverage):
        self.classes = {}
        for asset in coverage["assets"]:
            name = asset.get("original_class", asset["asset"] + "_C")
            if name in self.classes:
                raise ValueError("Duplicate native class: " + name)
            self.classes[name] = asset

    @staticmethod
    def profile(asset):
        return asset.get("effective_cdo_profile", asset.get("default_profile"))

    def definition(self, context, owner, method):
        asset = self.classes[context]
        ancestry = asset.get("ancestry", [context])
        if owner not in ancestry:
            return None
        bindings = {row["target_class"]: row for row in asset.get("all_ancestor_bindings", [])}
        for name in ancestry[ancestry.index(owner):]:
            current = self.classes.get(name)
            binding = bindings.get(name)
            functions = binding.get("profiles", {}).get(self.profile(asset), []) if binding else []
            if not binding and name == context:
                functions = asset.get("profiles", {}).get(self.profile(asset), {}).get("functions", [])
            if method in functions:
                return dict(kind="python", owner=name, profile=self.profile(asset), method=method)
            entries = [row for row in (current or {}).get("staged_wired_entries", []) if row["entry"] == method]
            if len(entries) == 1:
                return dict(kind="graph", owner=name, entry=entries[0])
            if entries:  # A duplicate definition is ambiguous, not a reason to try a parent.
                return None
        return None

    def routes(self, asset, entry):
        context = asset.get("original_class", asset["asset"] + "_C")
        pending = deque([(context, context, entry, [])])
        seen, witnesses = set(), []
        while pending:
            runtime, owner, method, path = pending.popleft()
            key = (runtime, owner, method)
            if key in seen:
                continue
            seen.add(key)
            definition = self.definition(runtime, owner, method)
            if definition is None:
                continue
            step = dict(owner_class=definition["owner"], method=method)
            chain = path + [step]
            if definition["kind"] == "python":
                witnesses.append(dict(profile=definition["profile"], path=chain))
                continue
            graph = definition["entry"]
            step["graph"] = graph["graph"]
            # Legacy snapshots have names but no qualified targets. Do not guess.
            for call in sorted(graph.get("call_targets", []), key=lambda row: (
                    row.get("method", ""), row.get("owner_class") or "", row.get("default_target_class") or "")):
                target = call.get("default_target_class") or call.get("owner_class")
                ancestry = self.classes[runtime].get("ancestry", [runtime])
                if target is None:
                    target_context, target_owner = runtime, runtime
                elif target in ancestry:
                    target_context, target_owner = runtime, target
                elif target in self.classes:
                    target_context = target_owner = target
                else:
                    continue
                pending.append((target_context, target_owner, call["method"], chain))
        return witnesses


def execution_shape(row):
    current = row["staged_entry"]
    return dict(original_business_nodes=row["reachable_execution_nodes"],
        original_node_classes=sorted(row["node_classes"]),
        staged_execution_nodes=current["reachable_execution_nodes"],
        staged_node_classes=sorted(current["reachable_node_classes"]),
        staged_calls=sorted(current["call_targets"], key=lambda call: (
            call["method"], call.get("owner_class") or "", call.get("default_target_class") or "")))


def apply_source_reviews(rows, reviews):
    """Apply individually documented retained-source dispositions, fail closed.

    These decisions still need their byte-matched historical evidence checked
    by the caller. Shape checks alone do not prove unchanged links or FText.
    """
    indexed = {(row["asset"], row["graph"], row["entry"]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Ambiguous original entry identity")
    seen = set()
    for review in reviews:
        key = (review["asset"], review["graph"], review["entry"])
        if key in seen:
            raise ValueError("Duplicate retained-source review: " + str(key))
        seen.add(key)
        row = indexed.get(key)
        if row is None or row["disposition"] != "unrouted-business-review":
            raise ValueError("Retained-source review no longer matches an unresolved entry: " + str(key))
        if not review.get("reason") or not review.get("historical_evidence_ledger"):
            raise ValueError("Explicit reason and historical evidence required: " + str(key))
        if execution_shape(row) != review["execution_shape"]:
            raise ValueError("Retained native entry body changed; review again: " + str(key))
        row.update(disposition="retained-native-source-review", retained_source_review=review)


def audit(original, coverage, source_reviews=()):
    blueprints = {item["path"]: item for item in original["blueprints"]}
    inventory = NativeCallInventory(coverage)
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
                routes = []
                if disposition == "unrouted-business-review":
                    routes = inventory.routes(asset, name)
                    if routes:
                        disposition = "staged-transitive-script-dispatch-review"
                rows.append(dict(asset=asset["asset"], version=asset["version"], entry=name,
                    graph=graph["name"], entry_class=entry["class"], disposition=disposition,
                    native_router=asset.get("native_router_class"),
                    staged_entry=current,
                    transitive_python_routes=routes,
                    reachable_execution_nodes=len(business),
                    node_titles=[node["title"].replace("\n", " ") for node in business],
                    node_classes=[node["class"] for node in business]))
    apply_source_reviews(rows, source_reviews)
    return dict(schema_version=2, status="review_complete", runtime_acceptance=False, full_acceptance=False,
        original_assets_modified=False, entrypoints=rows, counts=dict(Counter(row["disposition"] for row in rows)),
        limitations=["Original snapshot execution links, not a fresh graph audit or whole-dataflow proof",
                     "Unconnected events and direct parent forwarders are separately visible, not silently counted as migration",
                     "A transitive call witness proves structural reachability only; branch choices, receivers, dataflow and gameplay still require semantic/runtime evidence",
                     "Retained-source shape reviews require separately verified byte-matched historical evidence; they do not replay gameplay or prove full migration",
                     "Internal generated delegate forwarding may be intentionally replaced by an owning Python subscription; review individually"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-audit", required=True)
    parser.add_argument("--native-coverage", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--source-reviews", help="Explicit retained native entry dispositions; no implicit exemptions")
    args = parser.parse_args()
    files = [Path(args.original_audit).resolve(), Path(args.native_coverage).resolve()]
    original, coverage = (json.loads(file.read_text(encoding="utf-8-sig")) for file in files)
    reviews = []
    if args.source_reviews:
        files.append(Path(args.source_reviews).resolve())
        reviews = json.loads(files[-1].read_text(encoding="utf-8-sig"))["entries"]
    report = audit(original, coverage, reviews)
    report["input_hashes"] = {str(file): hashlib.sha256(file.read_bytes()).hexdigest() for file in files}
    Path(args.result).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(status=report["status"], counts=report["counts"], runtime_acceptance=False)))
    for row in report["entrypoints"]:
        if row["disposition"] == "unrouted-business-review":
            print(row["asset"], row["entry"], row["reachable_execution_nodes"], row["node_titles"][:5])
