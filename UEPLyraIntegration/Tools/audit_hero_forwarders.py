"""Source-only proof that two character shells contain no independent BP policy."""
import argparse
import hashlib
import json
from pathlib import Path

ASSETS = {
    "/Game/Characters/Character_Default.Character_Default": "Content/Characters/Character_Default.uasset",
    "/Game/Characters/Heroes/B_SimpleHeroPawn.B_SimpleHeroPawn": "Content/Characters/Heroes/B_SimpleHeroPawn.uasset",
}
ALLOWED = {"K2Node_FunctionEntry", "K2Node_Event", "K2Node_CallParentFunction", "EdGraphNode_Comment"}


def audit(data, official, stage):
    rows = []
    for path, relative in ASSETS.items():
        values = [row for row in data["blueprints"] if row["path"] == path]
        if len(values) != 1: raise RuntimeError("Expected one original source asset: "+path)
        value = values[0]
        nodes = [node for graph in value["graphs"] for node in graph["nodes"]]
        unexpected = [node["class"] for node in nodes if node["class"] not in ALLOWED]
        if unexpected: raise RuntimeError("Independent business requires review: "+repr(unexpected))
        parents = [node["properties"]["FunctionReference"]["MemberName"] for node in nodes if node["class"] == "K2Node_CallParentFunction"]
        if not parents or set(parents)-{"UserConstructionScript", "ReceiveBeginPlay"}:
            raise RuntimeError("Unexpected parent forwarding contract")
        hashes = {str(root/relative): hashlib.sha256((root/relative).read_bytes()).hexdigest() for root in (official, stage)}
        if len(set(hashes.values())) != 1: raise RuntimeError("Original shell asset changed: "+path)
        rows.append(dict(path=path, parent=value["parent_class"], independent_business_nodes=0,
            parent_forwarders=parents, node_classes=[node["class"] for node in nodes], reference_hashes=hashes,
            disposition="retain_original_empty_events_and_parent_forwarders", runtime_inheritance_acceptance=False))
    return dict(schema_version=1, status="passed", source_review_only=True, runtime_acceptance=False,
        full_acceptance=False, assets=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--audit", required=True)
    parser.add_argument("--official", required=True); parser.add_argument("--stage", required=True); parser.add_argument("--result", required=True)
    args = parser.parse_args()
    result = audit(json.loads(Path(args.audit).read_text(encoding="utf-8-sig")), Path(args.official), Path(args.stage))
    result["source_audit_sha256"] = hashlib.sha256(Path(args.audit).read_bytes()).hexdigest()
    target = Path(args.result); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(dict(status=result["status"], source_review_only=True, retained_shells=len(result["assets"]))))
