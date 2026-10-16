"""Extend VM transport and configure the example-owned interaction progress UI."""

import hashlib
import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next((arg for arg in sys.argv if Path(arg).name == "generate_ability_progress_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass the generator to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from message_payload_graphs import read_graph, broadcast_graph, connect

HELPER = "/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages"
RESUME = "UEPResumeDurationObservation"
PROXY = "UEPOriginalDurationProxy"


def argument(name):
    prefix = "-" + name + "="
    return next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)


def path(value):
    return None if value is None else value.get_path_name()


def graph_digest(graph):
    # Stable semantic pins/references rather than compiler transient pointers.
    nodes = []
    for node in sorted(graph.Nodes, key=lambda node: node.get_name()):
        reference = None
        try:
            value = node.FunctionReference
            reference = [str(value.MemberName), path(value.MemberParent), bool(value.bSelfContext)]
        except Exception:
            pass
        pins = [{"name": pin.name, "direction": pin.direction, "category": pin.category,
                 "sub_category": pin.sub_category, "object_type": path(pin.sub_category_object),
                 "container": pin.container_type, "reference": pin.is_reference, "const": pin.is_const,
                 "default": pin.default_value, "text": str(pin.default_text_value), "object": path(pin.default_object),
                 "links": sorted((link.owning_node.get_name(), link.name) for link in pin.get_linked_to())}
                for pin in node.node_pins()]
        nodes.append({"name": node.get_name(), "class": node.get_class().get_name(), "function": reference, "pins": pins})
    return hashlib.sha256(json.dumps(nodes, sort_keys=True).encode()).hexdigest()


def extend_adapter():
    helper = ue.load_object(Blueprint, HELPER)
    old_names = {"ReadUI", "ReadVerb", "BroadcastUI", "BroadcastVerb"}
    before = {graph.get_name(): graph_digest(graph) for graph in helper.FunctionGraphs if graph.get_name() in old_names}
    if set(before) != old_names:
        raise RuntimeError("existing typed transport differs")
    names = {graph.get_name() for graph in helper.FunctionGraphs}
    payload = ue.find_struct("LyraInteractionDurationMessage")
    if "ReadDuration" not in names:
        read_graph(helper, "Duration", payload, ue.find_class("AsyncAction_ListenForGameplayMessage"))
    if "BroadcastDuration" not in names:
        broadcast_graph(helper, "Duration", payload, ue.find_class("GameplayMessageSubsystem"))
    ue.compile_blueprint(helper)
    after = {graph.get_name(): graph_digest(graph) for graph in helper.FunctionGraphs if graph.get_name() in old_names}
    if int(helper.Status) == 2 or before != after:
        raise RuntimeError("typed duration extension changed existing transport semantics or failed compilation")
    helper.save_package()
    return helper.GeneratedClass, {"old_graph_digests": before, "old_graphs_unchanged": True,
                                    "functions": [{"name": graph.get_name(), "nodes": len(graph.Nodes)} for graph in helper.FunctionGraphs]}


def expose_proxy(bp):
    variables = {str(variable.VarName) for variable in bp.NewVariables}
    if PROXY in variables:
        return
    ue.blueprint_add_member_variable(bp, PROXY, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("AsyncAction_ListenForGameplayMessage")))
    ue.compile_blueprint(bp)
    graph = bp.UbergraphPages[0]
    actions = [node for node in graph.Nodes if node.get_class().get_name() == "K2Node_AsyncAction_ListenForGameplayMessages"]
    if len(actions) != 1:
        raise RuntimeError("duration widget's original async action differs")
    action = actions[0]
    then = action.node_find_pin("then")
    links = list(then.get_linked_to())
    if len(links) != 1:
        raise RuntimeError("duration widget's async factory continuation differs")
    setter = graph.graph_add_node_variable_set(PROXY)
    for link in links:
        then.break_link_to(link)
    connect(action, "then", setter, "execute")
    setter.node_find_pin("then").connect(links[0])
    connect(action, "AsyncTaskProxy", setter, PROXY)


def generate():
    stage = require_authoring_stage(argument("UEPAbilityProgressStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    source = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    reference = source / "Plugins/GameFeatures/ShooterCore/Content/UserInterface/HUD/W_AbilityProgress.uasset"
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    ue.unregister_all_mixins()
    adapter_class, transport = extend_adapter()
    bp = ue.load_object(Blueprint, "/ShooterCore/UserInterface/HUD/W_AbilityProgress.W_AbilityProgress")
    original_defaults = {name: float(getattr(bp.GeneratedClass.get_cdo(), name)) for name in ("Duration", "StartTime")}
    expose_proxy(bp)
    if RESUME not in {graph.get_name() for graph in bp.FunctionGraphs}:
        ue.blueprint_add_function(bp, RESUME)  # Declaration only; business is Python.
    variables = {str(variable.VarName) for variable in bp.NewVariables}
    if "PythonMessageAdapterClass" not in variables:
        ue.blueprint_add_member_variable(bp, "PythonMessageAdapterClass", EdGraphPinType(PinCategory="class", PinSubCategoryObject=ue.find_class("Object")))
    ue.compile_blueprint(bp)
    ue.unregister_all_mixins()
    name = "DA_W_AbilityProgressMixin"
    mixin = ue.find_asset("/Game/UEPMixins/" + name + "." + name)
    if mixin is None:
        factory = DataAssetFactory()
        factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_hud.ability_progress_mixin", PythonClass=python_class)
                      for profile, python_class in (("Python", "LyraAbilityProgressPythonProfile"), ("BlueprintFallback", "LyraAbilityProgressBlueprintFallbackProfile"))]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(bp)
    cdo = bp.GeneratedClass.get_cdo()
    cdo.PythonMessageAdapterClass = adapter_class
    if int(bp.Status) == 2 or cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
        raise RuntimeError("ability progress Interface/CDO postcondition differs")
    bp.save_package()
    mixin.save_package()
    if hashlib.sha256(reference.read_bytes()).hexdigest() != digest:
        raise RuntimeError("official ability progress changed")
    return {"status": "passed", "asset": bp.get_path_name(), "class_preserved": bp.GeneratedClass.get_name() == "W_AbilityProgress_C",
            "reference_sha256": digest, "original_defaults": original_defaults, "transport": transport,
            "original_proxy_exposed_for_owned_cleanup": True, "resume_declaration_business_logic": False, "runtime_acceptance": False}


result = argument("UEPGenerateAbilityProgressResult")
if result is None:
    raise RuntimeError("UEPGenerateAbilityProgressResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_ABILITY_PROGRESS_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
