"""Host-readable Blueprint migration model and explicit scope classification."""

from collections import Counter
import hashlib
import re


ENTRY_CLASSES = {"K2Node_FunctionEntry", "K2Node_Event", "K2Node_CustomEvent",
                 "K2Node_ComponentBoundEvent", "K2Node_ActorBoundEvent"}
NON_BUSINESS_NODES = {"EdGraphNode_Comment", "K2Node_Knot", *ENTRY_CLASSES,
                      "K2Node_FunctionResult", "K2Node_Tunnel"}


def retained_reason(blueprint):
    path = blueprint["path"]
    asset_class = blueprint["asset_class"]
    parent = blueprint.get("parent_class") or ""
    if asset_class == "ControlRigBlueprint" or re.search(
            r"AnimInstance|AnimNotify|AnimNotifyState|AnimationModifier|ControlRig", parent):
        return "animation system retained"
    if re.search(r"/Animations?/|/Rig/|/AnimModifiers/|/AnimNotifies/|/AnimationNotifies/", path):
        return "animation system retained"
    if "EditorUtility" in asset_class or re.search(r"/Tools/|/EditorUtilities/|^/LyraExtTool/", path):
        return "editor tooling retained"
    if re.search(r"^/ShooterTests/|/Tests/|/Testing/|/B_PerfTest|/GCNL?_Test_|/B_ShooterBotSpawner_Perf\.", path):
        return "test tooling retained"
    if blueprint.get("blueprint_type") == 3:
        return "interface declaration retained"
    return None


def entry_name(node, graph):
    properties = node.get("properties", {})
    custom = properties.get("CustomFunctionName")
    if custom and custom != "None":
        return custom
    reference = properties.get("FunctionReference", properties.get("EventReference", {}))
    member = reference.get("MemberName")
    return member if member and member != "None" else graph["name"]


def module_name(path):
    basename = path.rsplit(".", 1)[-1]
    slug = re.sub(r"\W+", "_", basename).lower()
    return slug + "_" + hashlib.sha256(path.encode()).hexdigest()[:10]


def methods(blueprint):
    result = {}
    for graph in blueprint["graphs"]:
        for node in graph["nodes"]:
            if node["class"] in ENTRY_CLASSES:
                name = entry_name(node, graph)
                result[name] = {"entry": node["id"], "graph": graph["id"],
                                "signature": blueprint.get("signatures", {}).get(name)}
    return result


def normalize(blueprint):
    return {
        "path": blueprint["path"], "class": blueprint["generated_class"],
        "parent": blueprint["parent_class"],
        "methods": methods(blueprint),
        "nodes": {node["id"]: node for graph in blueprint["graphs"] for node in graph["nodes"]},
    }


def summarize(audit):
    retained = list(audit.get("retained", []))
    runtime = []
    configuration = []
    for blueprint in audit["blueprints"]:
        reason = retained_reason(blueprint)
        if reason:
            retained.append({"path": blueprint["path"], "reason": reason})
            continue
        business_nodes = [node for graph in blueprint["graphs"] for node in graph["nodes"]
                          if node["class"] not in NON_BUSINESS_NODES]
        if not business_nodes:
            configuration.append(blueprint["path"])
        else:
            runtime.append({"path": blueprint["path"], "module": module_name(blueprint["path"]),
                            "method_count": len(methods(blueprint)), "business_nodes": len(business_nodes),
                            "node_classes": dict(Counter(node["class"] for node in business_nodes))})
    return {"runtime_blueprints": runtime, "configuration_only": configuration, "retained": retained,
            "runtime_blueprint_count": len(runtime), "configuration_only_count": len(configuration),
            "retained_count": len(retained), "migration_complete": False}
