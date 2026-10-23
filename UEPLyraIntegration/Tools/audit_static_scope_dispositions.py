"""Document each original configuration/retained asset without changing scope.

This proves the presence and source relationship of the exclusion reasons. It
does not accept migrated gameplay, native parent behavior or the whole version.
"""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from blueprint_model import NON_BUSINESS_NODES, retained_reason, summarize

COUNTS = (246, 182, 63, 11)


def inspect(audit, manifest, initial):
    if audit.get("status") != "passed" or audit.get("errors"):
        raise ValueError("A successful original graph audit is required")
    paths = [bp["path"] for bp in audit["blueprints"]] + [row["path"] for row in audit["retained"]]
    if len(paths) != 491 or len(set(paths)) != 491:
        raise ValueError("Original 491 assets must remain unique and complete")
    if (len(audit["blueprints"]), len(audit["retained"])) != (471, 20):
        raise ValueError("Original non-ABP/retained-ABP split changed")
    counts = tuple(manifest[key] for key in ("runtime_candidates", "configuration_only", "retained", "scope_review_candidates"))
    if counts != COUNTS or manifest.get("migration_complete") is not False:
        raise ValueError("Original migration scope changed or completion was asserted")
    assignments = [(row["path"], row["version"]) for row in manifest["assets"]]
    if assignments != [(row["path"], row["version"]) for row in initial["assets"]]:
        raise ValueError("Original candidate paths/order/versions changed")
    summary = summarize(audit)
    runtime = {row["path"] for row in summary["runtime_blueprints"]}
    if len(assignments) != 246 or len({p for p, _ in assignments}) != 246 or runtime != {p for p, _ in assignments}:
        raise ValueError("Runtime classification differs from the original candidate inventory")
    if (summary["runtime_blueprint_count"], summary["configuration_only_count"], summary["retained_count"]) != COUNTS[:3]:
        raise ValueError("Original graph classification counts changed")
    generated = {bp["generated_class"]: bp for bp in audit["blueprints"]}
    rows = []
    for bp in audit["blueprints"]:
        if bp["path"] in runtime:
            continue
        kinds = Counter(node["class"] for graph in bp["graphs"] for node in graph["nodes"])
        reason = retained_reason(bp)
        row = dict(asset=bp["path"], asset_class=bp["asset_class"], parent_class=bp["parent_class"],
            disposition="retained" if reason else "configuration-only", graph_node_classes=dict(sorted(kinds.items())))
        if reason:
            row["reason"] = reason
        else:
            if set(kinds) - NON_BUSINESS_NODES:
                raise ValueError("Configuration shell contains own runtime business: " + bp["path"])
            parent, seen, inherited = bp["parent_class"], set(), None
            while parent in generated:
                if parent in seen:
                    raise ValueError("Cyclic Blueprint parent chain")
                seen.add(parent)
                ancestor = generated[parent]
                if ancestor["path"] in runtime:
                    inherited = ancestor["path"]
                    break
                parent = ancestor["parent_class"]
            row.update(reason="No independent runtime business in the audited own graphs;retain native/parent behavior,component/default data and layout.",
                independent_business_nodes=0, inherited_runtime_candidate=inherited)
        rows.append(row)
    for retained in audit["retained"]:
        if retained.get("reason") != "ABP retained by user scope":
            raise ValueError("Retained ABP needs its original explicit scope reason")
        rows.append(dict(asset=retained["path"], disposition="retained", reason=retained["reason"]))
    if len(rows) != 245 or any(not row["reason"] for row in rows):
        raise ValueError("Every excluded asset needs its own reason")
    return dict(schema_version=1, status="passed", original_assets=491, original_non_abps=471, retained_abps=20,
        original_scope=list(COUNTS), dispositions=rows,
        disposition_counts=dict(Counter(row["disposition"] for row in rows)),
        retained_reason_counts=dict(Counter(row["reason"] for row in rows if row["disposition"] == "retained")),
        candidate_paths_order_versions_preserved=True, configuration_and_retained_reasons_documented=True,
        game_project_cpp_migration="separate later scope", runtime_acceptance=False, full_acceptance=False,
        limitations=["Own-graph classification comes from the supplied original native audit",
                     "Configuration shells may inherit migrated or native behavior;their exclusion does not remove that behavior from testing",
                     "Documented exclusion reasons do not accept the246 runtime candidates or whole Experiences"])


@lru_cache(maxsize=32)
def content_root(mount, reference):
    if mount == "Game":
        return Path("Content")
    plugins = list((reference / "Plugins").rglob(mount + ".uplugin"))
    if len(plugins) != 1:
        raise ValueError("Unique project content mount required: " + mount)
    return plugins[0].parent.relative_to(reference) / "Content"


def relative_asset(asset, reference):
    mount, tail = asset.split(".", 1)[0][1:].split("/", 1)
    return content_root(mount, reference) / (tail + ".uasset")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def compare_source_copies(report, reference, stage):
    if not (stage / ".uep-lyra-full-stage.json").is_file():
        raise ValueError("Marked disposable stage required")
    marker = json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))
    if Path(marker["source"]).resolve().parent != reference.resolve() or stage.resolve() == reference.resolve():
        raise ValueError("Stage reference relationship differs")
    for row in report["dispositions"]:
        relative = relative_asset(row["asset"], reference)
        original, copied = reference / relative, stage / relative
        digest = sha(original)
        if sha(copied) != digest:
            raise ValueError("Excluded asset differs from reference;review its current graphs: " + row["asset"])
        row.update(reference_relative_file=relative.as_posix(), reference_sha256=digest, stage_sha256=digest)
    report["current_reference_and_stage_excluded_asset_bytes_match"] = len(report["dispositions"])
    report["source_copy_roots"] = dict(reference=str(reference.resolve()), stage=str(stage.resolve()))


def verify_documentation(document, manifest, initial):
    """Rebuild the classification and verify live copies before citing a reason gate."""
    inputs = document.get("input_hashes", [])
    if len(inputs) != 3 or not document.get("source_copy_roots"):
        raise ValueError("Frozen original audit/inventory and source copy roots required")
    for row in inputs:
        path = Path(row["path"])
        if not path.is_file() or sha(path) != row["sha256"]:
            raise ValueError("Static scope input is missing or changed: " + str(path))
    original = json.loads(Path(inputs[0]["path"]).read_text(encoding="utf-8-sig"))
    original_inventory = json.loads(Path(inputs[2]["path"]).read_text(encoding="utf-8-sig"))
    if original_inventory != initial:
        raise ValueError("Static reason report uses a different initial inventory")
    expected = inspect(original, manifest, initial)
    roots = document["source_copy_roots"]
    compare_source_copies(expected, Path(roots["reference"]), Path(roots["stage"]))
    for key, value in expected.items():
        if document.get(key) != value:
            raise ValueError("Static reason report disagrees with verified source: " + key)
    return dict(status="passed", documented_assets=245, configuration_only=182, retained=63,
        current_reference_stage_byte_matches=245, runtime_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for argument in ("original-audit", "manifest", "initial-inventory", "reference-root", "stage-root", "result"):
        parser.add_argument("--" + argument, required=True)
    args = parser.parse_args()
    inputs = [Path(value).resolve() for value in (args.original_audit, args.manifest, args.initial_inventory)]
    report = inspect(*(json.loads(path.read_text(encoding="utf-8-sig")) for path in inputs))
    compare_source_copies(report, Path(args.reference_root).resolve(), Path(args.stage_root).resolve())
    report["input_hashes"] = [dict(path=str(path), sha256=sha(path)) for path in inputs]
    Path(args.result).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in ("dispositions", "input_hashes", "limitations")}))
