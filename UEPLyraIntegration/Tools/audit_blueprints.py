"""Export all project Blueprint graphs with exact links; never compile/save BPs.

Run with UnrealEditor-Cmd <staged project> -run=Py <this file>
-UEPLyraBlueprintAuditResult=<report.json>. ABPs are recorded as retained.
"""

from collections import Counter
import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint


RESULT_PREFIX = "-UEPLyraBlueprintAuditResult="
PROJECT_MOUNTS = (
    "/Game/", "/ShooterCore/", "/ShooterMaps/", "/ShooterExplorer/", "/TopDownArena/",
    "/ShooterTests/", "/GreenRoom/", "/RedRoom/", "/LyraExampleContent/",
    "/LyraExtTool/", "/CommonGame/", "/CommonLoadingScreen/",
    "/CommonStartupLoadingScreen/", "/GameSettings/", "/GameSubtitles/",
    "/CommonUser/", "/UIExtension/", "/PocketWorlds/", "/AsyncMixin/",
    "/GameplayMessageRouter/", "/ModularGameplayActors/",
)
MEMBER_FIELDS = ("FunctionReference", "EventReference", "VariableReference", "DelegateReference")
NODE_FIELDS = (
    "CustomFunctionName", "bIsPureFunc", "bIsInterfaceCall", "bSelfContext",
    "TargetType", "ProxyFactoryFunctionName", "ProxyFactoryClass", "ProxyClass",
    "DelegatePropertyName", "MacroGraphReference", "Enum", "bHasDefaultPin",
    "CaseSensitive", "FunctionName", "BoundGraph", "TimelineName",
)


def object_path(value):
    return None if value is None else value.get_path_name()


def optional_field(value, name):
    try:
        result = getattr(value, name)
        if result is None or isinstance(result, (str, int, float, bool)):
            return result
        try:
            return object_path(result)
        except Exception:
            return str(result)
    except Exception:
        return None


def member_description(value):
    return {name: optional_field(value, name) for name in (
        "MemberName", "MemberParent", "bSelfContext", "MemberScope"
    )}


def pin_description(pin):
    parent = pin.parent_pin
    return {
        "id": pin.id, "name": pin.name, "direction": pin.direction,
        "category": pin.category, "sub_category": pin.sub_category,
        "sub_category_object": object_path(pin.sub_category_object),
        "container_type": pin.container_type,
        "is_reference": pin.is_reference, "is_const": pin.is_const,
        "parent_pin": None if parent is None else parent.id,
        "default_value": pin.default_value,
        "default_text_value": pin.default_text_value,
        "default_object": object_path(pin.default_object),
        "links": [{"node": object_path(link.owning_node), "pin": link.id}
                  for link in pin.get_linked_to()],
    }


def node_description(node):
    result = {
        "id": object_path(node), "name": node.get_name(),
        "class": node.get_class().get_name(), "title": node.node_get_title(),
        "pins": [pin_description(pin) for pin in node.node_pins()],
        "properties": {},
    }
    for name in MEMBER_FIELDS:
        try:
            result["properties"][name] = member_description(getattr(node, name))
        except Exception:
            pass
    for name in NODE_FIELDS:
        value = optional_field(node, name)
        if value is not None:
            result["properties"][name] = value
    if result["class"] == "K2Node_MacroInstance":
        result["properties"]["macro_graph"] = object_path(node.node_get_macro_graph())
    try:
        result["local_variables"] = [{"name": str(variable.VarName),
            "default_value": str(variable.DefaultValue),
            "category": str(variable.VarType.PinCategory),
            "sub_category_object": object_path(variable.VarType.PinSubCategoryObject)}
            for variable in node.LocalVariables]
    except Exception:
        pass
    return result


def blueprint_description(blueprint):
    generated = blueprint.GeneratedClass
    cdo = generated.get_cdo() if generated is not None else None
    graphs = [{"id": object_path(graph), "name": graph.get_name(),
               "nodes": [node_description(node) for node in graph.Nodes]}
              for graph in ue.blueprint_get_all_graphs(blueprint)]
    signatures = {}
    for graph in graphs:
        for node in graph["nodes"]:
            if node["class"] not in ("K2Node_FunctionEntry", "K2Node_Event", "K2Node_CustomEvent", "K2Node_ComponentBoundEvent"):
                continue
            properties = node["properties"]
            name = properties.get("CustomFunctionName")
            if not name or name == "None":
                reference = properties.get("FunctionReference", properties.get("EventReference", {}))
                name = reference.get("MemberName")
            if name and cdo is not None:
                try:
                    signatures[name] = ue.describe_function(generated, name)
                except Exception:
                    pass
    return {
        "path": object_path(blueprint),
        "asset_class": blueprint.get_class().get_name(),
        "parent_class": object_path(blueprint.ParentClass),
        "generated_class": object_path(generated),
        "blueprint_type": optional_field(blueprint, "BlueprintType"),
        "reflected_functions": [] if cdo is None else sorted(cdo.functions()),
        "graphs": graphs,
        "signatures": signatures,
    }


def export():
    ue.wait_for_assets()
    asset_filter = ue.FARFilter()
    asset_filter.class_names = ["/Script/Engine.Blueprint"]
    asset_filter.recursive_classes = True
    assets = ue.get_assets_by_filter(asset_filter, True)
    retained = []
    descriptions = []
    errors = []
    for asset in sorted(assets, key=lambda entry: entry.object_path):
        path = asset.object_path
        if not path.startswith(PROJECT_MOUNTS):
            continue
        if asset.asset_class == "AnimBlueprint":
            retained.append({"path": path, "reason": "ABP retained by user scope"})
            continue
        try:
            blueprint = ue.load_object(Blueprint, path)
            if blueprint is None:
                raise RuntimeError("Blueprint could not be loaded")
            descriptions.append(blueprint_description(blueprint))
            ue.log("UEP_LYRA_BP_AUDITED " + path)
        except Exception:
            errors.append({"path": path, "error": traceback.format_exc()})
    node_classes = Counter(node["class"] for blueprint in descriptions
                           for graph in blueprint["graphs"] for node in graph["nodes"])
    macro_graphs = {}
    pending = [node["properties"].get("macro_graph") for blueprint in descriptions
               for graph in blueprint["graphs"] for node in graph["nodes"]
               if node["class"] == "K2Node_MacroInstance"]
    from unreal_engine.classes import EdGraph
    while pending:
        path = pending.pop()
        if not path or path in macro_graphs:
            continue
        graph = ue.load_object(EdGraph, path)
        description = {"id": path, "name": graph.get_name(),
                       "nodes": [node_description(node) for node in graph.Nodes]}
        macro_graphs[path] = description
        pending.extend(node["properties"].get("macro_graph") for node in description["nodes"]
                       if node["class"] == "K2Node_MacroInstance")
    return {
        "schema_version": 1,
        "status": "passed" if not errors else "failed",
        "scope": {"mounts": list(PROJECT_MOUNTS), "ABP": "retained"},
        "blueprint_count": len(descriptions), "retained_count": len(retained),
        "node_count": sum(node_classes.values()),
        "node_classes": dict(node_classes.most_common()),
        "blueprints": descriptions, "retained": retained, "errors": errors,
        "macro_graphs": macro_graphs,
    }


result_value = next((arg[len(RESULT_PREFIX):].strip('"') for arg in sys.argv
                     if arg.startswith(RESULT_PREFIX)), None)
if not result_value:
    raise RuntimeError(RESULT_PREFIX + "<path> is required")
report = export()
output = Path(result_value)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
ue.log("UEP_LYRA_BLUEPRINT_AUDIT_" + report["status"].upper())
if report["errors"]:
    raise RuntimeError("Blueprint audit failed for {0} assets".format(len(report["errors"])))
