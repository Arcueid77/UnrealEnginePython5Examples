"""Read-only compact pin/link view of a previously captured Blueprint audit."""

import argparse
import json
from pathlib import Path


def inspect(audit, asset, graph_name=None, signature=None):
    matches = [bp for bp in audit["blueprints"] if bp["path"] == asset or bp["path"].split(".")[-1] == asset]
    if len(matches) != 1:
        raise ValueError("select exactly one audited Blueprint: " + asset)
    bp = matches[0]
    if signature == "*":
        print(json.dumps(dict(signatures=bp.get("signatures", {}), functions=bp.get("reflected_functions", [])), indent=2, ensure_ascii=False))
        return
    if signature is not None:
        description = bp.get("signatures", {}).get(signature)
        if description is None:
            description = [dict(graph=graph["name"], entry=node["name"], pins=[
                {key: pin.get(key) for key in ("name", "direction", "category", "sub_category_object")}
                for pin in node["pins"] if pin["category"] not in ("exec", "delegate")])
                for graph in bp["graphs"] for node in graph["nodes"]
                if node.get("properties", {}).get("CustomFunctionName") == signature]
        print(json.dumps(description, indent=2, ensure_ascii=False))
        return
    print(bp["path"], "parent=" + str(bp["parent_class"]))
    names = {pin["id"]: pin["name"] for graph in bp["graphs"] for node in graph["nodes"] for pin in node["pins"]}
    for graph in bp["graphs"]:
        if graph_name and graph["name"] != graph_name:
            continue
        for node in graph["nodes"]:
            if node["class"] == "EdGraphNode_Comment":
                continue
            function = node.get("properties", {}).get("FunctionReference", {}).get("MemberName")
            local_scope = node.get("properties", {}).get("VariableReference", {}).get("MemberScope")
            print(graph["name"] + "/" + node["name"] + ": " + node["title"].replace("\n", " "),
                  "native=" + function if function else "", "scope=" + local_scope if local_scope else "")
            for pin in node["pins"]:
                targets = [link["node"].split(".")[-1] + ":" + names.get(link["pin"], link["pin"]) for link in pin["links"]]
                default = pin.get("default_object") or pin.get("default_text_value") or pin.get("default_value", "")
                if targets or default not in ("", "0", "0.0", "0.000000", "None"):
                    print(" ", pin["name"], "out" if pin["direction"] else "in", repr(default), "->", ",".join(targets))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    parser.add_argument("--asset", required=True)
    parser.add_argument("--graph")
    parser.add_argument("--signature")
    args = parser.parse_args()
    inspect(json.loads(Path(args.audit).read_text(encoding="utf-8-sig")), args.asset, args.graph, args.signature)
