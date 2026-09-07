"""Read-only inventory of the Lyra HUD assets used by the 0.8 slice."""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, Object


RESULT_PREFIX = "-UEPLyraHUDAuditResult="

WIDGET_BLUEPRINTS = (
    ("healthbar", "/Game/UI/Hud/W_Healthbar"),
    ("default_hud_layout", "/Game/UI/Hud/W_DefaultHUDLayout"),
    ("shooter_hud_layout", "/ShooterCore/UserInterface/W_ShooterHUDLayout"),
)

DATA_ASSETS = (
    ("shooter_hud_action_set", "/ShooterCore/Experiences/LAS_ShooterGame_StandardHUD"),
)


def command_line_value(prefix):
    for argument in sys.argv:
        if argument.startswith(prefix):
            return argument[len(prefix) :].strip('"')
    return None


def object_name(value):
    if value is None:
        return None
    try:
        return value.get_name()
    except Exception:
        return str(value)


def object_class_name(value):
    try:
        return value.get_class().get_name()
    except Exception:
        return None


def object_path_name(value):
    if value is None:
        return None
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def healthbar_mixin_description(blueprint, cdo, reflected_functions):
    implemented_interfaces = sorted(
        object_name(description.Interface)
        for description in blueprint.ImplementedInterfaces
        if description.Interface is not None
    )
    description = {
        "implemented_interfaces": implemented_interfaces,
        "mixin_set_path": None,
        "mixin_set_class": None,
        "selected_profile": None,
        "default_profile": None,
        "profiles": [],
    }
    if not {
        "GetPythonMixinSet",
        "GetPythonMixinProfile",
    }.issubset(set(reflected_functions)):
        return description

    mixin_set = cdo.GetPythonMixinSet()
    description["selected_profile"] = str(cdo.GetPythonMixinProfile())
    if mixin_set is None:
        return description

    description["mixin_set_path"] = object_path_name(mixin_set)
    description["mixin_set_class"] = object_class_name(mixin_set)
    description["default_profile"] = str(mixin_set.DefaultProfile)
    description["profiles"] = [
        {
            "profile_name": str(profile.ProfileName),
            "python_module": str(profile.PythonModule),
            "python_class": str(profile.PythonClass),
        }
        for profile in mixin_set.Profiles
    ]
    return description


def graph_description(graph, include_pin_defaults=False):
    nodes = []
    for node in graph.Nodes:
        try:
            title = node.node_get_title()
        except Exception:
            title = object_name(node)
        description = {
            "name": object_name(node),
            "class": object_class_name(node),
            "title": title,
        }
        if include_pin_defaults:
            # Read-only, authored defaults used to verify retained visual
            # primitives. Do not compile, alter pins or save these assets.
            description["pins"] = [
                {
                    "name": pin.name,
                    "category": pin.category,
                    "default_value": pin.default_value,
                    "default_object": object_path_name(pin.default_object),
                    "linked_pin_names": [link.name for link in pin.get_linked_to()],
                }
                for pin in node.node_pins()
            ]
        nodes.append(description)
    return {
        "name": graph.get_name(),
        "node_count": len(nodes),
        "nodes": nodes,
    }


def widget_tree_description(blueprint):
    tree = blueprint.WidgetTree
    widgets = []
    for widget in tree.AllWidgets:
        widgets.append(
            {
                "name": object_name(widget),
                "class": object_class_name(widget),
                "properties": sorted(widget.properties()),
            }
        )
    return {
        "widget_count": len(widgets),
        "root_widget": object_name(tree.RootWidget),
        "widgets": widgets,
    }


def blueprint_description(role, path):
    blueprint = ue.load_object(Blueprint, path)
    if blueprint is None or not blueprint.is_valid():
        raise RuntimeError("failed to load " + path)

    generated_class = blueprint.GeneratedClass
    cdo = generated_class.get_cdo()
    graphs = [
        graph_description(graph, include_pin_defaults=role == "healthbar")
        for graph in ue.blueprint_get_all_graphs(blueprint)
    ]
    reflected_functions = sorted(cdo.functions())
    description = {
        "role": role,
        "path": path,
        "asset_class": object_class_name(blueprint),
        "parent_class": object_name(blueprint.ParentClass),
        "generated_class": object_name(generated_class),
        "reflected_properties": sorted(cdo.properties()),
        "reflected_functions": reflected_functions,
        "graphs": graphs,
        "widget_tree": widget_tree_description(blueprint),
    }
    if role == "healthbar":
        description["mixin"] = healthbar_mixin_description(
            blueprint,
            cdo,
            reflected_functions,
        )
    return description


def data_asset_description(role, path):
    asset = ue.load_object(Object, path)
    if asset is None or not asset.is_valid():
        raise RuntimeError("failed to load " + path)
    description = {
        "role": role,
        "path": path,
        "asset_class": object_class_name(asset),
        "properties": sorted(asset.properties()),
    }
    if role == "shooter_hud_action_set":
        actions = []
        for action in asset.Actions:
            entry = {
                "name": object_name(action),
                "class": object_class_name(action),
                "path": action.get_path_name(),
            }
            if "Layout" in action.properties():
                entry["layout_entry_count"] = len(action.Layout)
            if "Widgets" in action.properties():
                entry["widget_entry_count"] = len(action.Widgets)
            actions.append(entry)
        description["game_features_to_enable"] = [
            str(value) for value in asset.GameFeaturesToEnable
        ]
        description["action_count"] = len(actions)
        description["actions"] = actions
    return description


result_value = command_line_value(RESULT_PREFIX)
if not result_value:
    raise RuntimeError(RESULT_PREFIX + "<path> is required")

result_path = Path(result_value)
try:
    report = {
        "schema_version": 1,
        "status": "passed",
        "engine_version": [ue.ENGINE_MAJOR_VERSION, ue.ENGINE_MINOR_VERSION],
        "widget_blueprints": [
            blueprint_description(*entry) for entry in WIDGET_BLUEPRINTS
        ],
        "data_assets": [data_asset_description(*entry) for entry in DATA_ASSETS],
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ue.log("UEP_LYRA_HUD_AUDIT_PASSED")
except Exception:
    details = traceback.format_exc()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(
            {"schema_version": 1, "status": "failed", "error": details},
            indent=2,
        ),
        encoding="utf-8",
    )
    ue.log_error(details)
    ue.log_error("UEP_LYRA_HUD_AUDIT_FAILED")
    raise
